"""Content fetching service with trafilatura for intelligent extraction"""

import io
import time
import json
import hashlib
import requests
from typing import Optional, Dict, Any
from pathlib import Path

import trafilatura
from pypdf import PdfReader

from src.models import Source
from src.core.logger import setup_logger
from src.services.text_processor import TextProcessor
from src.services.mime_router import MimeRouter
from src.services.content_extractors import ContentExtractors


class ContentFetcher:
    """Service for fetching and intelligently extracting content from URLs"""
    
    def __init__(self, cache_file: Path, request_delay: float = 1.0, 
                 max_retries: int = 4, timeout: int = 30, enable_ocr: bool = False):
        self.cache_file = cache_file
        self.request_delay = request_delay
        self.max_retries = max_retries
        self.timeout = timeout
        self.enable_ocr = enable_ocr
        self.logger = setup_logger(self.__class__.__name__)
        self.cache = self._load_cache()
        self.text_processor = TextProcessor()
        self.mime_router = MimeRouter(enable_ocr=enable_ocr)
        self.extractors = ContentExtractors(enable_ocr=enable_ocr)
    
    def _load_cache(self) -> Dict[str, Any]:
        """Load existing cache if available"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.warning(f"Failed to load cache: {e}")
        return {}
    
    def _save_cache(self):
        """Save cache to disk"""
        try:
            self.cache_file.parent.mkdir(exist_ok=True)
            with open(self.cache_file, 'w') as f:
                json.dump(self.cache, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save cache: {e}")
    
    def _get_cache_key(self, url: str) -> str:
        """Generate cache key for URL"""
        return hashlib.md5(url.encode()).hexdigest()
    
    def _extract_pdf_text(self, url: str) -> Optional[str]:
        """Extract text from PDF using direct download"""
        try:
            # Download PDF content using requests for binary data
            import requests
            
            response = requests.get(url, timeout=30, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            response.raise_for_status()
            
            # Extract text using pypdf
            reader = PdfReader(io.BytesIO(response.content))
            pages = []
            
            for page in reader.pages:
                text = page.extract_text() or ""
                if text.strip():
                    pages.append(text)
            
            full_text = "\n\n".join(pages)
            return full_text if full_text.strip() else None
            
        except Exception as e:
            self.logger.error(f"Failed to extract PDF text from {url}: {e}")
            return None
    
    def _extract_web_content(self, url: str) -> Optional[str]:
        """
        Extract main content from web pages using trafilatura.
        This handles HTML intelligently, removing boilerplate.
        """
        try:
            # Download the page
            downloaded = trafilatura.fetch_url(url, no_ssl=True)
            if not downloaded:
                self.logger.warning(f"Failed to download: {url}")
                return None
            
            # Extract main content (plain text for embeddings)
            content = trafilatura.extract(
                downloaded,
                favor_recall=True,          # Better for documentation
                include_comments=False,      # Skip comments sections
                include_tables=True,         # Keep tables (important for docs)
                include_formatting=False,    # Plain text (better for embeddings)
                deduplicate=True,           # Remove duplicate content
                target_language='en'        # Focus on English content
            )
            
            if not content:
                # Fallback to markdown extraction if plain text fails
                self.logger.info(f"Trying markdown extraction for {url}")
                content = trafilatura.extract(
                    downloaded,
                    output_format='markdown',
                    favor_recall=True,
                    include_tables=True
                )
            
            return content
            
        except Exception as e:
            self.logger.error(f"Failed to extract web content: {e}")
            return None
    
    def fetch(self, source: Source) -> Optional[str]:
        """Fetch and process content from source URL using MIME-based routing"""
        cache_key = self._get_cache_key(source.url)
        
        # Check cache first
        if cache_key in self.cache:
            self.logger.info(f"Using cached content for {source.id}")
            return self.cache[cache_key].get('content')
        
        # Skip Google Forms (not text-rich)
        if "docs.google.com/forms" in source.url:
            self.logger.info(f"Skipping Google Forms source: {source.id}")
            return None
        
        self.logger.info(f"Fetching content for {source.id}: {source.url}")
        
        try:
            # Download content with proper headers
            response = requests.get(source.url, timeout=self.timeout, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            response.raise_for_status()
            
            # Detect MIME type
            headers = {k.lower(): v for k, v in response.headers.items()}
            mime_type, content_type = self.mime_router.detect_mime_type(source.url, headers)
            
            self.logger.info(f"Detected content type '{content_type}' (MIME: {mime_type}) for {source.id}")
            
            # Check if we should process this type
            if not self.mime_router.should_process(content_type):
                self.logger.info(f"Skipping content type '{content_type}' for {source.id}")
                return None
            
            # Get extraction method
            extraction_method_name = self.mime_router.get_extraction_method(content_type)
            extraction_method = getattr(self.extractors, extraction_method_name, None)
            
            if not extraction_method:
                self.logger.warning(f"No extraction method for type '{content_type}'")
                return None
            
            # Extract content using appropriate method
            # Pass URL for HTML extraction
            if content_type == 'html':
                raw_text = extraction_method(response.content, source.url)
            else:
                raw_text = extraction_method(response.content)
            
            if not raw_text:
                self.logger.warning(f"No content extracted from {content_type}: {source.id}")
                return None
            
            # Process extracted text
            # Map content types to processing types
            processing_type_map = {
                'pdf': 'pdf',
                'html': 'html',
                'docx': 'document',
                'doc': 'document',
                'pptx': 'document',
                'ppt': 'document',
                'xlsx': 'spreadsheet',
                'xls': 'spreadsheet',
                'csv': 'spreadsheet',
                'json': 'data',
                'markdown': 'markdown',
                'text': 'general',
                'image': 'ocr',
            }
            
            processing_type = processing_type_map.get(content_type, 'general')
            content, metadata = self.text_processor.process_text(raw_text, processing_type)
            
            # Check if content is valid
            if not metadata.get("is_valid", False):
                self.logger.warning(f"Content too short or invalid for {source.id}")
                return None
            
            # Log if low-signal content
            if metadata.get("is_low_signal", False):
                self.logger.info(f"Low-signal content detected for {source.id}")
            
            # Cache the processed content
            # Include extractor metadata if available
            extractor_metadata = {}
            if hasattr(self.extractors, 'last_metadata'):
                extractor_metadata = self.extractors.last_metadata
            
            self.cache[cache_key] = {
                'content': content,
                'timestamp': time.time(),
                'url': source.url,
                'mime_type': mime_type,
                'content_type': content_type,
                'metadata': metadata,
                'extractor_metadata': extractor_metadata
            }
            self._save_cache()
            
            # Rate limiting
            time.sleep(self.request_delay)
            
            return content
            
        except requests.RequestException as e:
            self.logger.error(f"Failed to download content for {source.id}: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Failed to process content for {source.id}: {e}")
            return None
    
    def clear_cache(self):
        """Clear the content cache"""
        self.cache = {}
        if self.cache_file.exists():
            self.cache_file.unlink()
        self.logger.info("Content cache cleared")