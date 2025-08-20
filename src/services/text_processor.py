"""Text processing and cleaning service"""

import re
import hashlib
import unicodedata
from typing import List, Tuple, Set

from src.core.logger import setup_logger


class TextProcessor:
    """Service for cleaning and normalizing text before chunking"""
    
    # Common headers/footers to remove (generic patterns)
    HEADER_FOOTER_PATTERNS = [
        r"^Page \d+ of \d+$",  # Page numbers
        r"^\d{1,4}$",  # Lone page numbers
        r"^Table of Contents$",
        r"^Contents$",
        r"^Copyright.*\d{4}",  # Copyright notices
        r"^©.*\d{4}",  # Copyright symbol
        r"^All [Rr]ights [Rr]eserved",
        r"^Confidential",
        r"^Proprietary",
        r"^Draft",
        r"^Version \d+(?:\.\d+)*\s+[A-Z]{2,5}-[A-Z0-9]+\s+\d+\s*\|\s*PAGE",  # Version headers like "Version 1.0 DEA-C01 1 | PAGE"
    ]
    
    # Content quality thresholds
    MIN_WORD_COUNT = 50  # Documents with fewer words are likely navigation/headers
    MIN_SENTENCE_COUNT = 3  # Real content should have multiple sentences
    MIN_AVG_SENTENCE_LENGTH = 5  # Sentences should have substance
    MAX_URL_DENSITY = 0.15  # If >15% of content is URLs, it's likely just links
    MAX_SPECIAL_CHAR_RATIO = 0.4  # Too many special characters indicate non-prose content
    
    def __init__(self):
        self.logger = setup_logger(self.__class__.__name__)
        self.seen_hashes: Set[str] = set()
    
    def strip_frontmatter_and_meta(self, text: str) -> str:
        """Strip YAML frontmatter, HTML meta tags, and page chrome from text"""
        # Strip YAML frontmatter (---...--- at start of document)
        yaml_pattern = r'^---\s*\n.*?\n---\s*\n'
        text = re.sub(yaml_pattern, '', text, flags=re.DOTALL)
        
        # Also strip the pattern with spaced dashes (- - - ... - - -)
        spaced_yaml_pattern = r'^-\s+-\s+-.*?-\s+-\s+-\s*\n'
        text = re.sub(spaced_yaml_pattern, '', text, flags=re.DOTALL)
        
        # Strip inline metadata patterns like "- - - title: ... - - -"
        inline_meta_pattern = r'-\s+-\s+-\s+(?:title|url|hostname|description|sitename|date):[^-]*-\s+-\s+-'
        text = re.sub(inline_meta_pattern, '', text, flags=re.DOTALL)
        
        # Strip HTML meta tags
        text = re.sub(r'<meta[^>]*>', '', text, flags=re.IGNORECASE)
        text = re.sub(r'<title[^>]*>.*?</title>', '', text, flags=re.IGNORECASE | re.DOTALL)
        
        # Strip common page chrome patterns
        chrome_patterns = [
            r'Skip to (?:main )?content',
            r'Navigation menu',
            r'Main menu',
            r'Breadcrumb(?:s)?',
            r'You are here:',
            r'Home\s*>\s*',
            r'Back to top',
            r'Print this page',
            r'Share this (?:page|article)',
            r'Last updated:?\s*\d+',
            r'Published:?\s*\d+',
            r'Tags?:\s*[\w\s,]+',
            r'Categories?:\s*[\w\s,]+',
        ]
        
        for pattern in chrome_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        # Remove common metadata patterns at the start of text
        meta_patterns = [
            r'^title:\s*.*?\n',
            r'^url:\s*.*?\n', 
            r'^author:\s*.*?\n',
            r'^date:\s*.*?\n',
            r'^tags:\s*.*?\n',
            r'^category:\s*.*?\n',
        ]
        
        for pattern in meta_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.MULTILINE)
        
        # Clean up extra whitespace
        text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)  # Collapse multiple newlines
        text = text.strip()
        
        return text
    
    def preserve_technical_content(self, text: str) -> tuple:
        """Preserve URLs and technical identifiers before processing
        
        Returns:
            Tuple of (processed_text, preserved_items)
        """
        preserved = {}
        counter = 0
        
        # Preserve URLs (http, https, ftp, s3, etc.)
        url_pattern = r'(?:https?|ftp|s3|ssh|git)://[^\s<>"{}|\\^`\[\]]+'
        matches = list(re.finditer(url_pattern, text))
        for match in reversed(matches):  # Process from end to maintain positions
            placeholder = f'__PRESERVED_URL_{counter}__'
            preserved[placeholder] = match.group(0)
            text = text[:match.start()] + placeholder + text[match.end():]
            counter += 1
        
        # Preserve AWS S3 bucket URLs and ARNs
        aws_patterns = [
            r'\b[a-z0-9][a-z0-9\-\.]{1,61}[a-z0-9]\.s3[\.-][a-z0-9\-]+\.amazonaws\.com(?:/[^\s]*)?',
            r'\barn:[a-z0-9\-]+:[a-z0-9\-]+:[a-z0-9\-]*:[0-9]*:[a-zA-Z0-9\-_:/]*',
            r's3://[a-z0-9][a-z0-9\-\.]{1,61}[a-z0-9](?:/[^\s]*)?'
        ]
        
        for pattern in aws_patterns:
            matches = list(re.finditer(pattern, text))
            for match in reversed(matches):
                placeholder = f'__PRESERVED_AWS_{counter}__'
                preserved[placeholder] = match.group(0)
                text = text[:match.start()] + placeholder + text[match.end():]
                counter += 1
        
        # Preserve email addresses
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        matches = list(re.finditer(email_pattern, text))
        for match in reversed(matches):
            placeholder = f'__PRESERVED_EMAIL_{counter}__'
            preserved[placeholder] = match.group(0)
            text = text[:match.start()] + placeholder + text[match.end():]
            counter += 1
        
        # Preserve file paths
        path_patterns = [
            r'(?:/[a-zA-Z0-9_\-\.]+)+/?',  # Unix paths
            r'[A-Z]:\\(?:[a-zA-Z0-9_\-\. ]+\\)*[a-zA-Z0-9_\-\. ]*'  # Windows paths
        ]
        
        for pattern in path_patterns:
            matches = list(re.finditer(pattern, text))
            for match in reversed(matches):
                # Only preserve if it looks like a real path (has at least 2 segments)
                if match.group(0).count('/') >= 2 or match.group(0).count('\\') >= 1:
                    placeholder = f'__PRESERVED_PATH_{counter}__'
                    preserved[placeholder] = match.group(0)
                    text = text[:match.start()] + placeholder + text[match.end():]
                    counter += 1
        
        # Preserve technical identifiers (kebab-case like amzn-s3-bucket)
        # Only preserve if it has 3+ segments to avoid over-matching
        kebab_pattern = r'\b[a-z0-9]+(?:-[a-z0-9]+){2,}\b'
        matches = list(re.finditer(kebab_pattern, text))
        for match in reversed(matches):
            placeholder = f'__PRESERVED_KEBAB_{counter}__'
            preserved[placeholder] = match.group(0)
            text = text[:match.start()] + placeholder + text[match.end():]
            counter += 1
        
        return text, preserved
    
    def restore_technical_content(self, text: str, preserved: dict) -> str:
        """Restore preserved technical content"""
        for placeholder, original in preserved.items():
            text = text.replace(placeholder, original)
        return text
    
    def fix_hyphenation_and_splits(self, text: str) -> str:
        """Fix word splits, hyphenation, and spacing issues from PDFs and scraped content
        
        Args:
            text: Text with potential hyphenation issues
            
        Returns:
            Text with fixed hyphenation and word splits
        """
        # 1. Fix soft hyphens and line-wrap hyphenation
        # Remove soft hyphens (invisible hyphens)
        text = text.replace('\u00AD', '')  # Soft hyphen
        text = text.replace('\u2027', '')  # Hyphenation point
        
        # 2. Fix split words across line ends (word- \nword becomes wordword)
        # For hyphenated words at line end, join them
        # Only join if both parts are lowercase (avoid breaking URLs or identifiers)
        text = re.sub(r'\b([a-z]+)-\s*\n\s*([a-z]+)\b', r'\1\2', text)
        
        # 3. Fix incorrectly spaced hyphenated words ONLY for known compounds
        # Don't apply this broadly - it breaks technical identifiers
        compound_words = [
            ('cross', 'account'), ('multi', 'factor'), ('single', 'sign'),
            ('read', 'only'), ('write', 'only'), ('built', 'in'),
            ('plug', 'in'), ('add', 'on'), ('follow', 'up')
        ]
        for word1, word2 in compound_words:
            text = re.sub(f'\\b{word1}\\s+-\\s+{word2}\\b', f'{word1}-{word2}', text, flags=re.IGNORECASE)
        
        # 4. Fix common word splits from OCR/PDF extraction
        # Fix "youcan" -> "you can", "completelab" -> "complete lab"
        text = re.sub(r'\b(you)(can)\b', r'\1 \2', text, flags=re.IGNORECASE)
        text = re.sub(r'\b(complete)(lab)\b', r'\1 \2', text, flags=re.IGNORECASE)
        text = re.sub(r'\b(can)(not)\b', r'\1 \2', text, flags=re.IGNORECASE)
        
        # Fix incorrectly joined words (common patterns)
        text = re.sub(r'\b([a-z]+)([A-Z][a-z]+)\b', r'\1 \2', text)  # lowerUpper -> lower Upper
        
        # Preserve correctly spelled compound words
        text = re.sub(r'\b(for)\s+(example)\b', r'for example', text, flags=re.IGNORECASE)
        text = re.sub(r'\b(how)\s+(ever)\b', r'however', text, flags=re.IGNORECASE)
        text = re.sub(r'\b(there)\s+(fore)\b', r'therefore', text, flags=re.IGNORECASE)
        text = re.sub(r'\b(with)\s+(out)\b', r'without', text, flags=re.IGNORECASE)
        
        # 5. Normalize bullet points and list markers
        # Convert various bullet characters to standard dash
        bullets = ['•', '●', '○', '◦', '▪', '▫', '■', '□', '▸', '▹', '►', '▻', '‣', '⁃']
        for bullet in bullets:
            text = text.replace(bullet, '-')
        
        # 6. Normalize dashes and punctuation
        # Em dash, en dash, figure dash, horizontal bar -> standard dash
        text = text.replace('—', ' - ')  # Em dash
        text = text.replace('–', ' - ')  # En dash  
        text = text.replace('‒', '-')    # Figure dash
        text = text.replace('―', ' - ')  # Horizontal bar
        text = text.replace('⸺', ' - ')  # Two-em dash
        text = text.replace('⸻', ' - ')  # Three-em dash
        
        # 7. Fix spacing around punctuation (but preserve URLs and technical content)
        # Remove space before punctuation
        text = re.sub(r'\s+([,;!?])', r'\1', text)  # Removed : and . to preserve URLs
        # Add space after punctuation if missing (but not in URLs or numbers)
        # Don't add spaces after colons if followed by // (URLs)
        text = re.sub(r'(:)(?!//)(?=[A-Za-z])', r'\1 ', text)
        # Don't add spaces after periods in domains or decimals
        text = re.sub(r'(\.)(?![a-z]{2,4}\b|\d)(?=[A-Z])', r'\1 ', text)
        # Fix commas and semicolons
        text = re.sub(r'([,;])(?=[A-Za-z])', r'\1 ', text)
        # Preserve decimal points
        text = re.sub(r'(\d+)\.\s+(\d+)', r'\1.\2', text)
        
        # 8. Restore sentence breaks that may have been lost
        # Add space after period if followed by capital letter (fix "end.Next" -> "end. Next")
        text = re.sub(r'([.!?])([A-Z])', r'\1 \2', text)
        
        # 9. Normalize whitespace
        # Collapse multiple spaces (but preserve paragraph breaks)
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r' +\n', '\n', text)  # Remove trailing spaces
        text = re.sub(r'\n +', '\n', text)  # Remove leading spaces after newline
        
        # Ensure sentences are properly separated
        text = re.sub(r'([.!?])\s*\n\s*([a-z])', r'\1 \2', text)  # Join if next line starts with lowercase
        
        # Clean up spacing issues from the fixes above
        text = re.sub(r'\s+', ' ', text.replace('\n\n', '§PARA§')).replace('§PARA§', '\n\n')
        
        return text.strip()
    
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
            
            # For lines that contain header patterns, try to extract just the content part
            content_part = line_stripped
            
            # Check if line starts with a header pattern and try to extract content after it
            for pattern in self.HEADER_FOOTER_PATTERNS:
                match = re.match(pattern, line_stripped, re.IGNORECASE)
                if match:
                    # Remove the matched header from the beginning
                    remaining_text = line_stripped[match.end():].strip()
                    if remaining_text:
                        # If there's content after the header, keep just the content
                        content_part = remaining_text
                        break
                    else:
                        # If it's just the header with no content, skip the line
                        content_part = None
                        break
            
            # Skip if we determined this line is just a header
            if content_part is None:
                continue
            
            # Skip lone numbers (likely page numbers)
            if re.fullmatch(r"\d{1,4}", content_part):
                continue
            
            # Skip empty lines at document boundaries
            if not content_part and (len(keep) == 0 or len(keep) > 100):
                continue
            
            # Add the content (either original line or content after header removal)
            if content_part:
                keep.append(content_part)
        
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
    
    def detect_low_signal_section(self, text: str) -> Tuple[str, bool, str]:
        """Detect low-signal content based on quality metrics
        
        Args:
            text: Text to analyze
            
        Returns:
            Tuple of (text, is_low_signal, reason)
        """
        if not text:
            return text, True, "Empty content"
        
        # Calculate quality metrics
        words = text.split()
        word_count = len(words)
        
        # 1. Check minimum word count
        if word_count < self.MIN_WORD_COUNT:
            return text, True, f"Too short: only {word_count} words (min: {self.MIN_WORD_COUNT})"
        
        # 2. Check sentence structure
        # Simple sentence detection (periods, exclamations, questions)
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        sentence_count = len(sentences)
        
        if sentence_count < self.MIN_SENTENCE_COUNT:
            return text, True, f"Too few sentences: {sentence_count} (min: {self.MIN_SENTENCE_COUNT})"
        
        # 3. Check average sentence length
        avg_sentence_length = word_count / sentence_count if sentence_count > 0 else 0
        if avg_sentence_length < self.MIN_AVG_SENTENCE_LENGTH:
            return text, True, f"Sentences too short: avg {avg_sentence_length:.1f} words"
        
        # 4. Check URL density
        url_count = len(re.findall(r"https?://\S+", text))
        if word_count > 0:
            # Count URL words (approximate)
            url_words = url_count * 3  # URLs are typically ~3 words equivalent
            url_density = url_words / word_count
            if url_density > self.MAX_URL_DENSITY:
                return text, True, f"Too many URLs: {url_density:.1%} of content is links"
        
        # 5. Check for table of contents patterns
        toc_pattern = re.search(r"(\.\s*){3,}\d+", text)  # ... page patterns
        if toc_pattern:
            return text, True, "Table of contents pattern detected"
        
        # 6. Check for navigation/menu patterns (many short lines)
        lines = text.split('\n')
        if len(lines) > 10:
            short_lines = sum(1 for line in lines if len(line.split()) < 3)
            if short_lines / len(lines) > 0.7:
                return text, True, f"Navigation/menu pattern: {short_lines}/{len(lines)} short lines"
        
        # 7. Check special character ratio (but be lenient for technical content)
        non_alpha_ratio = len(re.findall(r'[^a-zA-Z\s]', text)) / len(text) if len(text) > 0 else 0
        if non_alpha_ratio > self.MAX_SPECIAL_CHAR_RATIO:
            # Additional check: if it has code blocks or technical content, allow it
            has_code = bool(re.search(r'```|<code>|function|class|def|import', text, re.IGNORECASE))
            if not has_code:
                return text, True, f"Too many special characters: {non_alpha_ratio:.1%}"
        
        # 8. Check if content is mostly boilerplate (copyright, legal, etc.)
        boilerplate_keywords = ['copyright', 'all rights reserved', 'terms of service', 'privacy policy']
        boilerplate_count = sum(1 for keyword in boilerplate_keywords if keyword in text.lower())
        if boilerplate_count >= 3 and word_count < 200:
            return text, True, "Mostly boilerplate content"
        
        return text, False, ""
    
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
        
        # Step 0: Preserve technical content before any processing
        text, preserved_content = self.preserve_technical_content(text)
        
        # Step 1: Fix hyphenation and word splits (especially from PDFs)
        text = self.fix_hyphenation_and_splits(text)
        
        # Step 2: Normalize unicode and whitespace
        text = self.normalize_text(text)
        
        # Step 3: Strip headers/footers (especially for PDFs)
        if content_type == "pdf":
            text = self.strip_headers_footers(text)
        
        # Step 4: Normalize bullets and lists
        text = self.normalize_bullets(text)
        
        # Step 5: Clean special sections
        text = self.clean_special_sections(text)
        
        # Step 6: Detect low-signal sections
        text, is_low_signal, low_signal_reason = self.detect_low_signal_section(text)
        
        # Step 7: Polish sentence boundaries
        text = self.polish_sentence_boundaries(text)
        
        # Step 8: Final normalization
        text = self.normalize_text(text)
        
        # Step 9: Restore preserved technical content
        text = self.restore_technical_content(text, preserved_content)
        
        # Calculate word count
        word_count = len(text.split()) if text else 0
        
        # Create detailed metadata with improved validation logic
        # For PDFs, be more lenient with minimum content threshold
        min_chars_threshold = 50 if content_type == "pdf" else 100
        word_count_threshold = 20 if content_type == "pdf" else 50
        
        # Consider content valid if it meets either character or word count threshold
        has_sufficient_chars = len(text.strip()) > min_chars_threshold
        has_sufficient_words = word_count > word_count_threshold
        
        metadata = {
            "is_valid": has_sufficient_chars or has_sufficient_words,
            "is_low_signal": is_low_signal,
            "low_signal_reason": low_signal_reason if is_low_signal else "",
            "content_type": content_type,
            "text_length": len(text),
            "word_count": word_count,
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