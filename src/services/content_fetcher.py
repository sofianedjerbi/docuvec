"""Content fetching service with trafilatura for intelligent extraction"""

import io
import time
import json
import hashlib
from typing import Optional, Dict, Any
from pathlib import Path

import trafilatura
from pypdf import PdfReader

from src.models import Source
from src.core.logger import setup_logger
from src.services.text_processor import TextProcessor


class ContentFetcher:
    """Service for fetching and intelligently extracting content from URLs"""
    
    def __init__(self, cache_file: Path, request_delay: float = 1.0, 
                 max_retries: int = 4, timeout: int = 30):
        self.cache_file = cache_file
        self.request_delay = request_delay
        self.max_retries = max_retries
        self.timeout = timeout
        self.logger = setup_logger(self.__class__.__name__)
        self.cache = self._load_cache()
        self.text_processor = TextProcessor()
    
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
            # Download PDF content using trafilatura's fetch (handles retries)
            downloaded = trafilatura.fetch_url(url, no_ssl=True, decode=False)
            if not downloaded:
                self.logger.error(f"Failed to download PDF: {url}")
                return None
            
            # Extract text using pypdf
            reader = PdfReader(io.BytesIO(downloaded))
            pages = []
            
            for page in reader.pages:
                text = page.extract_text() or ""
                if text.strip():
                    pages.append(text)
            
            full_text = "\n\n".join(pages)
            return full_text if full_text.strip() else None
            
        except Exception as e:
            self.logger.error(f"Failed to extract PDF text: {e}")
            return None
    
    def _extract_web_content(self, url: str) -> Optional[str]:
        """
        Extract main content from web pages using trafilatura.
        This handles HTML intelligently, removing boilerplate.
        """
        try:
            # Download the page
            downloaded = trafilatura.fetch_url(url, no_ssl=True, decode=True)
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
        """Fetch and process content from source URL"""
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
            # Determine if URL is a PDF
            is_pdf = (
                "cms.rt.microsoft.com/cms/api/am/binary" in source.url or
                source.url.lower().endswith('.pdf') or
                '/pdf/' in source.url.lower() or
                'format=pdf' in source.url.lower()
            )
            
            if is_pdf:
                # Extract PDF text
                self.logger.info(f"Processing as PDF: {source.id}")
                raw_text = self._extract_pdf_text(source.url)
                if not raw_text:
                    self.logger.warning(f"No text extracted from PDF: {source.id}")
                    return None
                # Process PDF text
                content, metadata = self.text_processor.process_text(raw_text, "pdf")
            else:
                # Extract web content using trafilatura
                self.logger.info(f"Processing as web content: {source.id}")
                raw_text = self._extract_web_content(source.url)
                if not raw_text:
                    self.logger.warning(f"No content extracted from web page: {source.id}")
                    return None
                # Process web text
                content, metadata = self.text_processor.process_text(raw_text, "html")
            
            # Check if content is valid
            if not metadata.get("is_valid", False):
                self.logger.warning(f"Content too short or invalid for {source.id}")
                return None
            
            # Log if low-signal content
            if metadata.get("is_low_signal", False):
                self.logger.info(f"Low-signal content detected for {source.id}")
            
            # Cache the processed content
            self.cache[cache_key] = {
                'content': content,
                'timestamp': time.time(),
                'url': source.url,
                'is_pdf': is_pdf,
                'metadata': metadata
            }
            self._save_cache()
            
            # Rate limiting
            time.sleep(self.request_delay)
            
            return content
            
        except Exception as e:
            self.logger.error(f"Failed to fetch content for {source.id}: {e}")
            return None
    
    def clear_cache(self):
        """Clear the content cache"""
        self.cache = {}
        if self.cache_file.exists():
            self.cache_file.unlink()
        self.logger.info("Content cache cleared")