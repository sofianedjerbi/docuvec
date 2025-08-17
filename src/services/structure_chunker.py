"""Structure-aware text chunking with semantic boundaries and quality gates"""

import re
import hashlib
from typing import List, Tuple, Dict, Any, Optional
from dataclasses import dataclass, field
import tiktoken

from src.core.logger import setup_logger


@dataclass
class DocumentSection:
    """Represents a section of a document with hierarchy"""
    content: str
    level: int  # 0=title, 1=h1, 2=h2, 3=h3, 4=paragraph
    heading: str = ""
    parent_headings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StructuredChunk:
    """A chunk with hierarchical context and quality metrics"""
    text: str
    chunk_id: str
    hierarchical_title: str  # "Page Title > Section > Subsection"
    headings: List[str]
    chunk_index: int
    total_chunks: int
    token_count: int
    quality_score: float
    is_low_signal: bool
    metadata: Dict[str, Any] = field(default_factory=dict)


class StructureChunker:
    """Advanced chunking with structure awareness and quality gates"""
    
    # Heading patterns for markdown-style content
    HEADING_PATTERNS = [
        (r'^#{1}\s+(.+)$', 1),  # # H1
        (r'^#{2}\s+(.+)$', 2),  # ## H2
        (r'^#{3}\s+(.+)$', 3),  # ### H3
        (r'^#{4,6}\s+(.+)$', 4),  # #### H4+ (treat as paragraph level)
    ]
    
    # Low-signal patterns
    LOW_SIGNAL_PATTERNS = [
        r'^\s*\[.*\]\(.*\)\s*$',  # Link-only line
        r'^\s*\d+\.\s*$',  # Number-only line
        r'^\s*[•·▪▫◦‣⁃]\s*$',  # Bullet-only line
        r'^\s*(Advertisement|Sponsored|Ad)\s*$',
        r'^\s*(Read more|Continue reading|Click here)\s*$',
        r'^\s*Page \d+ of \d+\s*$',
        r'^\s*Copyright ©.*\s*$',
        r'^\s*All rights reserved\s*$',
    ]
    
    def __init__(self, 
                 max_tokens: int = 700,
                 overlap_tokens: int = 80,
                 min_tokens: int = 40,
                 model: str = "cl100k_base"):
        """
        Initialize structure-aware chunker
        
        Args:
            max_tokens: Maximum tokens per chunk
            overlap_tokens: Token overlap between chunks
            min_tokens: Minimum tokens for valid chunk
            model: Tokenizer model name
        """
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens
        self.min_tokens = min_tokens
        self.tokenizer = tiktoken.get_encoding(model)
        self.logger = setup_logger(self.__class__.__name__)
    
    def parse_structure(self, text: str, page_title: str = "") -> List[DocumentSection]:
        """
        Parse document structure into hierarchical sections
        
        Args:
            text: Document text
            page_title: Overall page/document title
            
        Returns:
            List of DocumentSection objects with hierarchy
        """
        sections = []
        current_headings = {1: "", 2: "", 3: ""}  # Track heading hierarchy
        
        # Add page title as root section
        if page_title:
            sections.append(DocumentSection(
                content="",
                level=0,
                heading=page_title,
                parent_headings=[],
                metadata={"is_title": True}
            ))
        
        # Split into lines for processing
        lines = text.split('\n')
        current_paragraph = []
        
        for line in lines:
            line = line.strip()
            
            # Skip empty lines
            if not line:
                # Flush current paragraph if exists
                if current_paragraph:
                    content = '\n'.join(current_paragraph)
                    sections.append(DocumentSection(
                        content=content,
                        level=4,  # Paragraph level
                        heading="",
                        parent_headings=self._get_current_headings(current_headings),
                        metadata={"is_paragraph": True}
                    ))
                    current_paragraph = []
                continue
            
            # Check for heading
            is_heading = False
            for pattern, level in self.HEADING_PATTERNS:
                match = re.match(pattern, line, re.MULTILINE)
                if match:
                    # Flush current paragraph
                    if current_paragraph:
                        content = '\n'.join(current_paragraph)
                        sections.append(DocumentSection(
                            content=content,
                            level=4,
                            heading="",
                            parent_headings=self._get_current_headings(current_headings),
                            metadata={"is_paragraph": True}
                        ))
                        current_paragraph = []
                    
                    # Add heading section
                    heading_text = match.group(1).strip()
                    current_headings[level] = heading_text
                    
                    # Clear lower-level headings
                    for l in range(level + 1, 4):
                        current_headings[l] = ""
                    
                    sections.append(DocumentSection(
                        content="",
                        level=level,
                        heading=heading_text,
                        parent_headings=self._get_current_headings(current_headings, level - 1),
                        metadata={"is_heading": True, "level": level}
                    ))
                    
                    is_heading = True
                    break
            
            # If not a heading, add to current paragraph
            if not is_heading:
                current_paragraph.append(line)
        
        # Flush final paragraph
        if current_paragraph:
            content = '\n'.join(current_paragraph)
            sections.append(DocumentSection(
                content=content,
                level=4,
                heading="",
                parent_headings=self._get_current_headings(current_headings),
                metadata={"is_paragraph": True}
            ))
        
        return sections
    
    def _get_current_headings(self, headings: Dict[int, str], max_level: int = 3) -> List[str]:
        """Get current heading hierarchy up to specified level"""
        result = []
        for level in range(1, min(max_level + 1, 4)):
            if headings.get(level):
                result.append(headings[level])
        return result
    
    def create_semantic_chunks(self, 
                              sections: List[DocumentSection], 
                              page_title: str = "",
                              page_language: str = "en") -> List[StructuredChunk]:
        """
        Create semantic chunks from document sections
        
        Args:
            sections: Parsed document sections
            page_title: Overall page title
            page_language: Expected language of page
            
        Returns:
            List of StructuredChunk objects
        """
        chunks = []
        current_chunk_sections = []
        current_token_count = 0
        current_headings = []
        
        for section in sections:
            # Skip empty sections
            if not section.content and not section.heading:
                continue
            
            # Calculate tokens for this section
            section_text = section.heading + "\n" + section.content if section.heading else section.content
            section_tokens = len(self.tokenizer.encode(section_text))
            
            # Update headings for hierarchical title
            if section.level <= 3 and section.heading:
                # Update heading hierarchy
                current_headings = section.parent_headings + [section.heading]
            
            # Check if adding this section would exceed max tokens
            if current_token_count + section_tokens > self.max_tokens and current_chunk_sections:
                # Create chunk from current sections
                chunk = self._create_chunk_from_sections(
                    current_chunk_sections,
                    page_title,
                    current_headings,
                    len(chunks),
                    page_language
                )
                if chunk and not chunk.is_low_signal:
                    chunks.append(chunk)
                
                # Start new chunk with overlap
                current_chunk_sections = self._get_overlap_sections(current_chunk_sections)
                current_token_count = sum(
                    len(self.tokenizer.encode(s.heading + "\n" + s.content if s.heading else s.content))
                    for s in current_chunk_sections
                )
            
            # Add section to current chunk
            current_chunk_sections.append(section)
            current_token_count += section_tokens
        
        # Create final chunk
        if current_chunk_sections:
            chunk = self._create_chunk_from_sections(
                current_chunk_sections,
                page_title,
                current_headings,
                len(chunks),
                page_language
            )
            if chunk and not chunk.is_low_signal:
                chunks.append(chunk)
        
        # Update total chunks count
        for i, chunk in enumerate(chunks):
            chunk.total_chunks = len(chunks)
        
        return chunks
    
    def _create_chunk_from_sections(self,
                                   sections: List[DocumentSection],
                                   page_title: str,
                                   headings: List[str],
                                   chunk_index: int,
                                   page_language: str) -> Optional[StructuredChunk]:
        """Create a chunk from sections with quality assessment"""
        if not sections:
            return None
        
        # Combine section texts
        chunk_lines = []
        for section in sections:
            if section.heading and section.level <= 3:
                # Add heading with markdown formatting
                prefix = "#" * section.level
                chunk_lines.append(f"{prefix} {section.heading}")
            if section.content:
                chunk_lines.append(section.content)
        
        chunk_text = '\n\n'.join(chunk_lines).strip()
        
        if not chunk_text:
            return None
        
        # Calculate tokens
        tokens = self.tokenizer.encode(chunk_text)
        token_count = len(tokens)
        
        # Build hierarchical title
        title_parts = []
        if page_title:
            title_parts.append(page_title)
        title_parts.extend(headings[:3])  # Max 3 levels
        hierarchical_title = " > ".join(title_parts)
        
        # Calculate quality score and check if low-signal
        quality_score, is_low_signal = self._assess_chunk_quality(
            chunk_text, 
            token_count,
            page_language
        )
        
        # Generate chunk ID
        chunk_id = self._generate_chunk_id(chunk_text, chunk_index)
        
        return StructuredChunk(
            text=chunk_text,
            chunk_id=chunk_id,
            hierarchical_title=hierarchical_title,
            headings=headings,
            chunk_index=chunk_index,
            total_chunks=0,  # Will be updated later
            token_count=token_count,
            quality_score=quality_score,
            is_low_signal=is_low_signal,
            metadata={
                "sections_count": len(sections),
                "has_headings": any(s.level <= 3 for s in sections),
                "language": page_language
            }
        )
    
    def _get_overlap_sections(self, sections: List[DocumentSection]) -> List[DocumentSection]:
        """Get sections for overlap in next chunk"""
        if not sections:
            return []
        
        # Calculate how many tokens to keep for overlap
        overlap_sections = []
        overlap_tokens = 0
        
        # Start from the end and work backwards
        for section in reversed(sections):
            section_text = section.heading + "\n" + section.content if section.heading else section.content
            section_tokens = len(self.tokenizer.encode(section_text))
            
            if overlap_tokens + section_tokens <= self.overlap_tokens:
                overlap_sections.insert(0, section)
                overlap_tokens += section_tokens
            else:
                break
        
        return overlap_sections
    
    def _assess_chunk_quality(self, text: str, token_count: int, page_language: str) -> Tuple[float, bool]:
        """
        Assess chunk quality and determine if it's low-signal
        
        Returns:
            Tuple of (quality_score, is_low_signal)
        """
        quality_score = 1.0
        is_low_signal = False
        
        # Check minimum token count
        if token_count < self.min_tokens:
            quality_score *= 0.3
            is_low_signal = True
            return quality_score, is_low_signal
        
        # Check for low-signal patterns
        lines = text.split('\n')
        low_signal_lines = 0
        total_lines = len(lines)
        
        for line in lines:
            for pattern in self.LOW_SIGNAL_PATTERNS:
                if re.match(pattern, line.strip(), re.IGNORECASE):
                    low_signal_lines += 1
                    break
        
        if total_lines > 0:
            low_signal_ratio = low_signal_lines / total_lines
            if low_signal_ratio > 0.5:
                quality_score *= 0.4
                is_low_signal = True
        
        # Check for high punctuation/digit ratio (likely code or data)
        text_chars = len(text)
        if text_chars > 0:
            punct_count = sum(1 for c in text if c in '.,;:!?()[]{}/<>@#$%^&*+=|\\`~"\'')
            digit_count = sum(1 for c in text if c.isdigit())
            
            punct_ratio = punct_count / text_chars
            digit_ratio = digit_count / text_chars
            
            if punct_ratio > 0.3:  # More than 30% punctuation
                quality_score *= 0.6
                if punct_ratio > 0.5:
                    is_low_signal = True
            
            if digit_ratio > 0.3:  # More than 30% digits
                quality_score *= 0.6
                if digit_ratio > 0.5:
                    is_low_signal = True
        
        # Check for link-only content
        link_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
        links = re.findall(link_pattern, text)
        if links:
            # Remove links to check remaining content
            text_without_links = re.sub(link_pattern, '', text).strip()
            if len(text_without_links) < 50:  # Almost only links
                quality_score *= 0.3
                is_low_signal = True
        
        # Language detection (if langdetect is available)
        try:
            import langdetect
            detected_lang = langdetect.detect(text[:500] if len(text) > 500 else text)
            
            # Check language mismatch
            if page_language and detected_lang != page_language[:2]:
                quality_score *= 0.7
                # Don't mark as low-signal, just reduce quality
        except:
            pass  # langdetect not available or detection failed
        
        return quality_score, is_low_signal
    
    def _generate_chunk_id(self, text: str, index: int) -> str:
        """Generate stable chunk ID from content"""
        # Use first 100 chars + index for ID
        content_sample = text[:100] + str(index)
        return hashlib.md5(content_sample.encode()).hexdigest()[:16]
    
    def chunk_text(self, 
                   text: str, 
                   page_title: str = "",
                   page_language: str = "en",
                   metadata: Dict[str, Any] = None) -> List[StructuredChunk]:
        """
        Main entry point for structure-aware chunking
        
        Args:
            text: Document text to chunk
            page_title: Title of the page/document
            page_language: Expected language (ISO code)
            metadata: Additional metadata to include
            
        Returns:
            List of StructuredChunk objects
        """
        if not text or not text.strip():
            return []
        
        # Parse document structure
        sections = self.parse_structure(text, page_title)
        
        # Create semantic chunks
        chunks = self.create_semantic_chunks(sections, page_title, page_language)
        
        # Add metadata to all chunks
        if metadata:
            for chunk in chunks:
                chunk.metadata.update(metadata)
        
        # Log chunking results
        self.logger.info(f"Created {len(chunks)} structure-aware chunks")
        if chunks:
            low_signal_count = sum(1 for c in chunks if c.is_low_signal)
            avg_tokens = sum(c.token_count for c in chunks) / len(chunks)
            self.logger.info(f"  Average tokens: {avg_tokens:.1f}, Low-signal: {low_signal_count}/{len(chunks)}")
        
        return chunks