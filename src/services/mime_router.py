"""MIME type detection and routing for content extraction"""

import io
import mimetypes
from typing import Optional, Tuple, Dict, Any
from pathlib import Path
import requests

from src.core.logger import setup_logger


class MimeRouter:
    """Routes content to appropriate extraction pipeline based on MIME type"""
    
    # MIME type mappings for content extraction
    MIME_MAPPINGS = {
        # HTML/Web content
        'text/html': 'html',
        'application/xhtml+xml': 'html',
        'text/xml': 'html',
        'application/xml': 'html',
        
        # PDF documents
        'application/pdf': 'pdf',
        'application/x-pdf': 'pdf',
        
        # Microsoft Office formats
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
        'application/msword': 'doc',
        'application/vnd.openxmlformats-officedocument.presentationml.presentation': 'pptx',
        'application/vnd.ms-powerpoint': 'ppt',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'xlsx',
        'application/vnd.ms-excel': 'xls',
        
        # Text formats
        'text/plain': 'text',
        'text/markdown': 'markdown',
        'text/x-markdown': 'markdown',
        'application/json': 'json',
        'text/csv': 'csv',
        
        # Images (for OCR)
        'image/jpeg': 'image',
        'image/jpg': 'image',
        'image/png': 'image',
        'image/tiff': 'image',
        'image/bmp': 'image',
        'image/gif': 'image',
        'image/webp': 'image',
    }
    
    # File extension fallbacks
    EXTENSION_MAPPINGS = {
        '.html': 'html',
        '.htm': 'html',
        '.pdf': 'pdf',
        '.docx': 'docx',
        '.doc': 'doc',
        '.pptx': 'pptx',
        '.ppt': 'ppt',
        '.xlsx': 'xlsx',
        '.xls': 'xls',
        '.txt': 'text',
        '.md': 'markdown',
        '.json': 'json',
        '.csv': 'csv',
        '.jpg': 'image',
        '.jpeg': 'image',
        '.png': 'image',
        '.tiff': 'image',
        '.tif': 'image',
        '.bmp': 'image',
        '.gif': 'image',
        '.webp': 'image',
    }
    
    def __init__(self, enable_ocr: bool = False):
        """
        Initialize MIME router
        
        Args:
            enable_ocr: Whether to enable OCR for images and scanned PDFs
        """
        self.enable_ocr = enable_ocr
        self.logger = setup_logger(self.__class__.__name__)
    
    def detect_mime_type(self, url: str, headers: Optional[Dict[str, str]] = None) -> Tuple[str, str]:
        """
        Detect MIME type from URL and optional headers
        
        Args:
            url: URL to analyze
            headers: Optional HTTP headers containing Content-Type
            
        Returns:
            Tuple of (mime_type, content_type)
        """
        mime_type = None
        
        # First, try to get from provided headers
        if headers and 'content-type' in headers:
            content_type_header = headers['content-type'].lower()
            # Extract MIME type (before any semicolon)
            mime_type = content_type_header.split(';')[0].strip()
            
        # If not found, try HEAD request
        if not mime_type:
            try:
                response = requests.head(url, timeout=5, allow_redirects=True, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                })
                content_type_header = response.headers.get('content-type', '').lower()
                if content_type_header:
                    mime_type = content_type_header.split(';')[0].strip()
            except Exception as e:
                self.logger.debug(f"Could not fetch headers for {url}: {e}")
        
        # Fallback to URL extension
        if not mime_type:
            # Use mimetypes library first
            guessed_type, _ = mimetypes.guess_type(url)
            if guessed_type:
                mime_type = guessed_type.lower()
            else:
                # Manual extension check
                path = Path(url.lower())
                ext = path.suffix
                if ext in self.EXTENSION_MAPPINGS:
                    # Synthesize a MIME type
                    if self.EXTENSION_MAPPINGS[ext] == 'pdf':
                        mime_type = 'application/pdf'
                    elif self.EXTENSION_MAPPINGS[ext] == 'html':
                        mime_type = 'text/html'
                    elif self.EXTENSION_MAPPINGS[ext] == 'docx':
                        mime_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                    else:
                        mime_type = 'application/octet-stream'
        
        # Map MIME type to content type
        content_type = self.MIME_MAPPINGS.get(mime_type, 'unknown')
        
        # Special URL patterns (fallback)
        if content_type == 'unknown':
            # Check for PDF patterns in URL
            if any(pattern in url.lower() for pattern in ['/pdf/', 'format=pdf', '.pdf']):
                content_type = 'pdf'
                mime_type = 'application/pdf'
        
        self.logger.debug(f"Detected MIME type for {url}: {mime_type} -> {content_type}")
        return mime_type, content_type
    
    def get_extraction_method(self, content_type: str) -> str:
        """
        Get the appropriate extraction method for a content type
        
        Args:
            content_type: Detected content type
            
        Returns:
            Extraction method name
        """
        extraction_methods = {
            'html': 'extract_html',
            'pdf': 'extract_pdf',
            'docx': 'extract_docx',
            'doc': 'extract_doc',
            'pptx': 'extract_pptx',
            'ppt': 'extract_ppt',
            'xlsx': 'extract_xlsx',
            'xls': 'extract_xls',
            'text': 'extract_text',
            'markdown': 'extract_markdown',
            'json': 'extract_json',
            'csv': 'extract_csv',
            'image': 'extract_image_ocr' if self.enable_ocr else 'skip_image',
            'unknown': 'extract_fallback'
        }
        
        return extraction_methods.get(content_type, 'extract_fallback')
    
    def should_process(self, content_type: str) -> bool:
        """
        Check if content type should be processed
        
        Args:
            content_type: Content type to check
            
        Returns:
            True if should be processed
        """
        # Skip images if OCR is disabled
        if content_type == 'image' and not self.enable_ocr:
            return False
        
        # Skip unknown types
        if content_type == 'unknown':
            return False
        
        return True
    
    def get_required_libraries(self, content_type: str) -> Dict[str, str]:
        """
        Get required libraries for processing a content type
        
        Args:
            content_type: Content type to check
            
        Returns:
            Dict of library name to pip package
        """
        libraries = {
            'pdf': {'pypdf': 'pypdf', 'pdfplumber': 'pdfplumber'},
            'docx': {'python-docx': 'python-docx', 'mammoth': 'mammoth'},
            'doc': {'python-docx': 'python-docx', 'mammoth': 'mammoth'},
            'pptx': {'python-pptx': 'python-pptx'},
            'ppt': {'python-pptx': 'python-pptx'},
            'xlsx': {'openpyxl': 'openpyxl', 'pandas': 'pandas'},
            'xls': {'xlrd': 'xlrd', 'pandas': 'pandas'},
            'csv': {'pandas': 'pandas'},
            'image': {'pytesseract': 'pytesseract', 'Pillow': 'Pillow'} if self.enable_ocr else {},
        }
        
        return libraries.get(content_type, {})