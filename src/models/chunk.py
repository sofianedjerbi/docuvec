"""Enhanced chunk data model with production-ready fields"""

from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime


@dataclass
class Chunk:
    """Enhanced data class for document chunk with comprehensive metadata"""
    
    # Required fields
    id: str                          # Unique chunk identifier
    doc_id: str                      # Stable document ID (canonical URL hash)
    text: str                        # Chunk text content
    source_url: str                  # Original URL
    canonical_url: str               # Normalized canonical URL
    domain: str                      # Domain (e.g., "docs.example.com")
    path: str                        # URL path (e.g., "/api/auth")
    page_title: str                  # Full hierarchical title string
    title_hierarchy: List[str]      # ["Page Title", "Section", "Subsection"]
    lang: str                        # ISO language code (e.g., "en", "fr")
    content_type: str                # "html" | "pdf" | "docx" | "markdown" | "txt"
    chunk_index: int                 # Position in document
    total_chunks: int                # Total chunks from document
    
    # Timestamps
    published_at: Optional[datetime] = None  # Document publish date
    modified_at: Optional[datetime] = None   # Document last modified
    crawl_ts: datetime = field(default_factory=datetime.now)  # When we crawled
    
    # Content hashing
    content_sha1: str = ""           # SHA1 hash of text for exact duplicate detection
    simhash: str = ""                # Simhash for near-duplicate detection
    
    # Optional fields
    embedding: Optional[List[float]] = field(default=None)  # Vector embedding
    chunk_char_start: Optional[int] = None  # Character offset start
    chunk_char_end: Optional[int] = None    # Character offset end
    tokens: int = 0                  # Token count for this chunk
    
    # Quality and relevance
    is_low_signal: bool = False     # Low-quality content flag
    low_signal_reason: str = ""     # Why it's low signal
    retrieval_weight: float = 1.0   # Weight for retrieval (0.0-1.5)
    source_confidence: float = 1.0  # Source reliability (0.0-1.0)
    section_type: str = "content"   # "content" | "structured" | "simple"
    
    # Content features
    headings: List[str] = field(default_factory=list)  # All headings in chunk
    has_code: bool = False           # Contains code blocks
    has_table: bool = False          # Contains tables
    has_list: bool = False           # Contains lists
    links_out: int = 0               # Number of outbound links
    
    # Compliance
    noindex: bool = False            # Respect robots meta
    nofollow: bool = False           # Respect link following rules
    
    # Legacy/optional fields (for backward compatibility)
    service: List[str] = field(default_factory=list)
    domain_exam: str = ""
    certification: str = ""
    provider: str = ""               # Category/provider
    resource_type: str = "document"  # "document" | "service"
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            # Core
            "id": self.id,
            "doc_id": self.doc_id,
            "text": self.text,
            "embedding": self.embedding,
            
            # URLs
            "source_url": self.source_url,
            "canonical_url": self.canonical_url,
            "domain": self.domain,
            "path": self.path,
            
            # Content metadata
            "page_title": self.page_title,
            "title_hierarchy": self.title_hierarchy,
            "lang": self.lang,
            "content_type": self.content_type,
            
            # Timestamps (ISO format)
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "modified_at": self.modified_at.isoformat() if self.modified_at else None,
            "crawl_ts": self.crawl_ts.isoformat(),
            
            # Hashing
            "content_sha1": self.content_sha1,
            "simhash": self.simhash,
            
            # Chunk metadata
            "chunk_index": self.chunk_index,
            "total_chunks": self.total_chunks,
            "chunk_char_start": self.chunk_char_start,
            "chunk_char_end": self.chunk_char_end,
            "tokens": self.tokens,
            
            # Quality
            "is_low_signal": self.is_low_signal,
            "low_signal_reason": self.low_signal_reason,
            "retrieval_weight": self.retrieval_weight,
            "source_confidence": self.source_confidence,
            "section_type": self.section_type,
            
            # Features
            "headings": self.headings,
            "has_code": self.has_code,
            "has_table": self.has_table,
            "has_list": self.has_list,
            "links_out": self.links_out,
            
            # Compliance
            "noindex": self.noindex,
            "nofollow": self.nofollow,
            
            # Legacy fields
            "service": self.service,
            "domain_exam": self.domain_exam,
            "certification": self.certification,
            "provider": self.provider,
            "resource_type": self.resource_type,
        }