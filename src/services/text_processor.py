"""Text processing and cleaning service"""

import re
import hashlib
import unicodedata
from typing import List, Tuple, Set

from src.core.logger import setup_logger


class TextProcessor:
    """Service for cleaning and normalizing text before chunking"""
    
    # Common headers/footers to remove (AWS-focused patterns)
    HEADER_FOOTER_PATTERNS = [
        r"^Operational Excellence Pillar AWS Well-Architected Framework$",
        r"^AWS Well-Architected Framework$",
        r"^AWS Certified.*Exam Guide$",
        r"^Page \d+ of \d+$",
        r"^OPS\d{2}-BP\d{2}.*$",  # AWS section labels
        r"^Copyright.*Amazon.*\d{4}",
        r"^©.*Amazon Web Services.*",
        r"^AWS.*\| \d+ \|.*$",  # AWS page numbers
        r"^\d{1,4}$",  # Lone page numbers
        r"^Table of Contents$",
        r"^Contents$",
    ]
    
    # Low-signal section headers
    LOW_SIGNAL_HEADINGS = [
        r"^Related (documents?|videos?|examples?|services?|resources?):?$",
        r"^Resources?$",
        r"^References?$",
        r"^Additional Resources?$",
        r"^Learn More$",
        r"^See Also$",
        r"^External Links?$",
        r"^Further Reading$",
    ]
    
    def __init__(self):
        self.logger = setup_logger(self.__class__.__name__)
        self.seen_hashes: Set[str] = set()
    
    def normalize_text(self, text: str) -> str:
        """Normalize unicode and whitespace
        
        Args:
            text: Raw text to normalize
            
        Returns:
            Normalized text
        """
        # Normalize unicode to NFC
        text = unicodedata.normalize("NFC", text)
        
        # Fix common ligatures
        text = text.replace("ﬁ", "fi").replace("ﬀ", "ff").replace("ﬂ", "fl")
        text = text.replace("ﬃ", "ffi").replace("ﬄ", "ffl")
        
        # Normalize quotes and dashes
        text = text.replace(""", '"').replace(""", '"')
        text = text.replace("'", "'").replace("'", "'")
        text = text.replace("–", "-").replace("—", "-")
        
        # Collapse multiple spaces/tabs to single space
        text = re.sub(r"[ \t]+", " ", text)
        
        # Normalize line breaks
        text = re.sub(r"\s*\n\s*", "\n", text)
        
        # Remove excessive blank lines
        text = re.sub(r"\n{3,}", "\n\n", text)
        
        return text.strip()
    
    def strip_headers_footers(self, text: str) -> str:
        """Remove repetitive headers and footers
        
        Args:
            text: Text to clean
            
        Returns:
            Text without headers/footers
        """
        lines = text.splitlines()
        keep = []
        
        for line in lines:
            line_stripped = line.strip()
            
            # Check against header/footer patterns
            if any(re.match(pattern, line_stripped, re.IGNORECASE) 
                   for pattern in self.HEADER_FOOTER_PATTERNS):
                continue
            
            # Skip lone numbers (likely page numbers)
            if re.fullmatch(r"\d{1,4}", line_stripped):
                continue
            
            # Skip empty lines at document boundaries
            if not line_stripped and (len(keep) == 0 or len(keep) > 100):
                continue
            
            keep.append(line)
        
        return "\n".join(keep)
    
    def normalize_bullets(self, text: str) -> str:
        """Clean and normalize bullet points and lists
        
        Args:
            text: Text with potential bullet points
            
        Returns:
            Text with normalized bullets
        """
        # Convert various bullet symbols to standard dash
        text = re.sub(r"[•·◦▪▫■□◆◇※→➤➢]\s*", "- ", text)
        
        # Ensure bullet items are on separate lines
        text = re.sub(r"(?<!\n)\s*-\s*", "\n- ", text)
        
        # Fix numbered lists
        text = re.sub(r"(?<!\n)(\d+\.)\s+", r"\n\1 ", text)
        
        # Clean up list formatting
        text = re.sub(r"\n{2,}(?=[-\d])", "\n", text)
        
        return text
    
    def detect_low_signal_section(self, text: str) -> Tuple[str, bool]:
        """Detect and optionally tag low-signal sections
        
        Args:
            text: Text to analyze
            
        Returns:
            Tuple of (text, is_low_signal)
        """
        # Check if text contains low-signal headings
        is_low_signal = any(
            re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
            for pattern in self.LOW_SIGNAL_HEADINGS
        )
        
        # Additional heuristics for low-signal content
        if not is_low_signal:
            # Check for excessive URLs (likely a references section)
            url_count = len(re.findall(r"https?://", text))
            text_length = len(text)
            if text_length > 0 and url_count > 5 and url_count * 50 > text_length:
                is_low_signal = True
            
            # Check for table of contents patterns
            if re.search(r"(\.\s*){3,}\d+", text):  # ... page patterns
                is_low_signal = True
        
        return text, is_low_signal
    
    def clean_special_sections(self, text: str) -> str:
        """Clean special sections like code blocks and tables
        
        Args:
            text: Text to clean
            
        Returns:
            Cleaned text
        """
        # Preserve code blocks but clean formatting
        text = re.sub(r"```(\w+)?\n", "\n[CODE]\n", text)
        text = re.sub(r"```\n?", "\n[/CODE]\n", text)
        
        # Clean table formatting (simple approach)
        text = re.sub(r"\|{2,}", "|", text)  # Collapse multiple pipes
        text = re.sub(r"^\||\|$", "", text, flags=re.MULTILINE)  # Remove leading/trailing pipes
        
        # Remove horizontal rules
        text = re.sub(r"^[-=_*]{3,}$", "", text, flags=re.MULTILINE)
        
        return text
    
    def polish_sentence_boundaries(self, text: str) -> str:
        """Polish text to improve sentence boundaries
        
        Args:
            text: Text to polish
            
        Returns:
            Polished text
        """
        # Ensure space after periods (except decimals and abbreviations)
        text = re.sub(r"\.(?=[A-Z])", ". ", text)
        
        # Fix common abbreviations
        text = re.sub(r"\be\.g\.\s*", "e.g., ", text)
        text = re.sub(r"\bi\.e\.\s*", "i.e., ", text)
        
        # Ensure proper spacing around punctuation
        text = re.sub(r"\s+([,;:])", r"\1", text)
        text = re.sub(r"([,;:])\s*", r"\1 ", text)
        
        # Clean up whitespace again
        text = re.sub(r"\s+", " ", text).strip()
        
        return text
    
    def calculate_hash(self, text: str) -> str:
        """Calculate hash for deduplication
        
        Args:
            text: Text to hash
            
        Returns:
            SHA1 hash of the text
        """
        return hashlib.sha1(text.encode("utf-8")).hexdigest()
    
    def is_duplicate(self, text: str) -> bool:
        """Check if text is a duplicate
        
        Args:
            text: Text to check
            
        Returns:
            True if duplicate, False otherwise
        """
        text_hash = self.calculate_hash(text)
        if text_hash in self.seen_hashes:
            return True
        self.seen_hashes.add(text_hash)
        return False
    
    def process_text(self, text: str, content_type: str = "general") -> Tuple[str, dict]:
        """Complete text processing pipeline
        
        Args:
            text: Raw text to process
            content_type: Type of content (pdf, html, general)
            
        Returns:
            Tuple of (processed_text, metadata)
        """
        if not text:
            return "", {"is_valid": False}
        
        # Step 1: Normalize unicode and whitespace
        text = self.normalize_text(text)
        
        # Step 2: Strip headers/footers (especially for PDFs)
        if content_type == "pdf":
            text = self.strip_headers_footers(text)
        
        # Step 3: Normalize bullets and lists
        text = self.normalize_bullets(text)
        
        # Step 4: Clean special sections
        text = self.clean_special_sections(text)
        
        # Step 5: Detect low-signal sections
        text, is_low_signal = self.detect_low_signal_section(text)
        
        # Step 6: Polish sentence boundaries
        text = self.polish_sentence_boundaries(text)
        
        # Step 7: Final normalization
        text = self.normalize_text(text)
        
        # Create metadata
        metadata = {
            "is_valid": len(text.strip()) > 100,  # Minimum content threshold
            "is_low_signal": is_low_signal,
            "content_type": content_type,
            "text_length": len(text),
            "line_count": len(text.splitlines())
        }
        
        # Log sample for validation
        if text:
            sample = text[:120].replace("\n", " ")
            self.logger.debug(f"Processed text sample: {sample}...")
        
        return text, metadata
    
    def deduplicate_chunks(self, chunks: List[str]) -> List[str]:
        """Remove duplicate chunks
        
        Args:
            chunks: List of text chunks
            
        Returns:
            Deduplicated list of chunks
        """
        unique_chunks = []
        seen_hashes = set()
        
        for chunk in chunks:
            chunk_hash = self.calculate_hash(chunk)
            if chunk_hash not in seen_hashes:
                seen_hashes.add(chunk_hash)
                unique_chunks.append(chunk)
            else:
                self.logger.debug(f"Skipping duplicate chunk: {chunk[:50]}...")
        
        if len(chunks) != len(unique_chunks):
            self.logger.info(f"Removed {len(chunks) - len(unique_chunks)} duplicate chunks")
        
        return unique_chunks