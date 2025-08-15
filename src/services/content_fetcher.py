"""Content fetching service with caching and retry logic"""

import io
import re
import time
import json
import hashlib
import requests
from typing import Optional, Dict, Any
from pathlib import Path

from bs4 import BeautifulSoup
from markdownify import markdownify as md
from pypdf import PdfReader

from src.models import Source
from src.core.logger import setup_logger
from src.services.text_processor import TextProcessor


class ContentFetcher:
    """Service for fetching and processing content from URLs"""
    
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
    
    def _fetch_with_retry(self, url: str) -> requests.Response:
        """Fetch URL with retry logic and exponential backoff"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        for attempt in range(self.max_retries):
            try:
                response = requests.get(url, headers=headers, timeout=self.timeout)
                response.raise_for_status()
                return response
            except requests.RequestException as e:
                if attempt == self.max_retries - 1:
                    raise e
                wait_time = (2 ** attempt) * 0.5
                self.logger.warning(f"Attempt {attempt + 1} failed, retrying in {wait_time}s: {e}")
                time.sleep(wait_time)
    
    def _extract_pdf_text(self, content: bytes) -> str:
        """Extract text from PDF content"""
        try:
            reader = PdfReader(io.BytesIO(content))
            pages = []
            
            for page in reader.pages:
                text = page.extract_text() or ""
                if text.strip():
                    pages.append(text)
            
            full_text = "\n\n".join(pages)  # Better page separation
            return full_text
            
        except Exception as e:
            self.logger.error(f"Failed to extract PDF text: {e}")
            return ""
    
    def _clean_html_content(self, html_content: str) -> str:
        """Clean and convert HTML to markdown"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove unwanted elements
        for element in soup(["script", "style", "nav", "footer", "header", 
                            "aside", "noscript", "iframe", "form"]):
            element.decompose()
        
        # Remove table of contents if detected
        for toc in soup.find_all(["div", "nav"], class_=re.compile(r"toc|table-of-contents", re.I)):
            toc.decompose()
        
        # Convert to markdown
        markdown = md(str(soup), heading_style="ATX")
        
        # Clean up excessive whitespace
        lines = [line.strip() for line in markdown.split('\n') if line.strip()]
        return '\n'.join(lines)
    
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
            response = self._fetch_with_retry(source.url)
            content_type = response.headers.get('content-type', '').lower()
            
            # Determine content type and process accordingly
            if ("cms.rt.microsoft.com/cms/api/am/binary" in source.url or 
                'application/pdf' in content_type or 
                source.url.endswith('.pdf')):
                # Extract PDF text
                raw_text = self._extract_pdf_text(response.content)
                if not raw_text.strip():
                    self.logger.warning(f"No text extracted from PDF: {source.id}")
                    return None
                # Process PDF text with text processor
                content, metadata = self.text_processor.process_text(raw_text, "pdf")
            elif 'text/html' in content_type:
                # Clean HTML and convert to markdown
                raw_text = self._clean_html_content(response.text)
                # Process HTML text with text processor
                content, metadata = self.text_processor.process_text(raw_text, "html")
            else:
                # Plain text
                raw_text = response.text
                content, metadata = self.text_processor.process_text(raw_text, "general")
            
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
                'content_type': content_type,
                'metadata': metadata
            }
            self._save_cache()
            
            # Rate limiting
            time.sleep(self.request_delay)
            
            return content
            
        except Exception as e:
            self.logger.error(f"Failed to fetch content for {source.id}: {e}")
            return None