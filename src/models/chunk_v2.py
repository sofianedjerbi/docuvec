"""Enhanced chunk data model v2 with auditability and compliance fields"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict
from datetime import datetime


@dataclass
class ChunkV2:
    """Production-ready chunk with comprehensive metadata, auditability, and compliance"""
    
    # === CORE FIELDS ===
    id: str                          # Unique chunk identifier
    doc_id: str                      # Stable document ID (canonical URL hash)
    text: str                        # Chunk text content
    embedding: Optional[List[float]] = field(default=None)
    
    # === VERSIONING & AUDITABILITY ===
    schema_version: str = "2.0.0"   # Schema version for migrations
    pipeline_version: str = ""      # ETL pipeline version/hash
    embedding_model: str = ""        # Model used (e.g., "text-embedding-3-small")
    embedding_dim: int = 1536        # Embedding dimensions
    tokenizer: str = "cl100k_base"   # Tokenizer used
    
    # === URL COMPONENTS ===
    source_url: str = ""             # Original URL
    canonical_url: str = ""          # Normalized canonical URL
    domain: str = ""                 # Domain (e.g., "docs.example.com")
    path: str = ""                   # URL path (e.g., "/api/auth")
    anchor_url: str = ""             # Full URL with fragment for precise linking
    
    # === SOURCE METADATA ===
    source_type: str = "crawl"       # "crawl" | "upload" | "api" | "file"
    license: str = ""                # Content license (e.g., "MIT", "CC-BY-4.0")
    attribution_required: bool = False  # Whether attribution is required
    
    # === CONTENT METADATA ===
    page_title: str = ""             # Full hierarchical title string
    title_hierarchy: List[str] = field(default_factory=list)  # ["Page", "Section", "Subsection"]
    lang: str = "en"                 # ISO language code
    content_type: str = "html"       # "html" | "pdf" | "docx" | "markdown" | "txt"
    
    # === POSITION & NAVIGATION ===
    page_num: Optional[int] = None   # Page number (for PDFs)
    anchor_id: str = ""              # HTML anchor/fragment ID
    chunk_index: int = 0             # Position in document
    total_chunks: int = 0            # Total chunks from document
    chunk_char_start: Optional[int] = None  # Character offset start
    chunk_char_end: Optional[int] = None    # Character offset end
    
    # === CONTENT METRICS ===
    tokens: int = 0                  # Token count
    word_count: int = 0              # Word count (cheap, useful for snippets)
    
    # === TIMESTAMPS ===
    published_at: Optional[datetime] = None
    modified_at: Optional[datetime] = None
    crawl_ts: datetime = field(default_factory=datetime.now)
    
    # === CONTENT HASHING ===
    content_sha1: str = ""           # SHA1 of cleaned text
    original_sha1: str = ""          # SHA1 of raw content (before cleaning)
    simhash: str = ""                # Simhash for near-duplicate detection
    
    # === PRIVACY & COMPLIANCE ===
    pii_flags: Dict[str, bool] = field(default_factory=lambda: {
        "email": False,
        "phone": False,
        "ssn": False,
        "credit_card": False,
        "ip_address": False,
        "person_name": False,
        "address": False,
        "id_number": False,
    })
    noindex: bool = False            # Respect robots meta
    nofollow: bool = False           # Respect link following rules
    
    # === QUALITY & RELEVANCE ===
    is_low_signal: bool = False
    low_signal_reason: str = ""
    retrieval_weight: float = 1.0    # 0.0-1.5
    source_confidence: float = 1.0   # 0.0-1.0
    section_type: str = "content"
    
    # === CONTENT FEATURES ===
    headings: List[str] = field(default_factory=list)
    has_code: bool = False
    has_table: bool = False
    has_list: bool = False
    links_out: int = 0
    
    # === LEGACY/DOMAIN FIELDS ===
    service: List[str] = field(default_factory=list)
    domain_exam: str = ""
    certification: str = ""
    provider: str = ""
    resource_type: str = "document"
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            # Core
            "id": self.id,
            "doc_id": self.doc_id,
            "text": self.text,
            "embedding": self.embedding,
            
            # Versioning & Auditability
            "schema_version": self.schema_version,
            "pipeline_version": self.pipeline_version,
            "embedding_model": self.embedding_model,
            "embedding_dim": self.embedding_dim,
            "tokenizer": self.tokenizer,
            
            # URLs
            "source_url": self.source_url,
            "canonical_url": self.canonical_url,
            "domain": self.domain,
            "path": self.path,
            "anchor_url": self.anchor_url,
            
            # Source metadata
            "source_type": self.source_type,
            "license": self.license,
            "attribution_required": self.attribution_required,
            
            # Content metadata
            "page_title": self.page_title,
            "title_hierarchy": self.title_hierarchy,
            "lang": self.lang,
            "content_type": self.content_type,
            
            # Position & Navigation
            "page_num": self.page_num,
            "anchor_id": self.anchor_id,
            "chunk_index": self.chunk_index,
            "total_chunks": self.total_chunks,
            "chunk_char_start": self.chunk_char_start,
            "chunk_char_end": self.chunk_char_end,
            
            # Metrics
            "tokens": self.tokens,
            "word_count": self.word_count,
            
            # Timestamps
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "modified_at": self.modified_at.isoformat() if self.modified_at else None,
            "crawl_ts": self.crawl_ts.isoformat(),
            
            # Hashing
            "content_sha1": self.content_sha1,
            "original_sha1": self.original_sha1,
            "simhash": self.simhash,
            
            # Privacy & Compliance
            "pii_flags": self.pii_flags,
            "noindex": self.noindex,
            "nofollow": self.nofollow,
            
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
            
            # Legacy fields
            "service": self.service,
            "domain_exam": self.domain_exam,
            "certification": self.certification,
            "provider": self.provider,
            "resource_type": self.resource_type,
        }
    
    @classmethod
    def get_schema_version(cls) -> str:
        """Get current schema version"""
        return "2.0.0"
    
    def validate(self) -> List[str]:
        """Validate chunk data and return list of issues"""
        issues = []
        
        if not self.id:
            issues.append("Missing chunk ID")
        if not self.doc_id:
            issues.append("Missing document ID")
        if not self.text:
            issues.append("Missing text content")
        if self.retrieval_weight < 0 or self.retrieval_weight > 1.5:
            issues.append(f"Invalid retrieval_weight: {self.retrieval_weight}")
        if self.source_confidence < 0 or self.source_confidence > 1:
            issues.append(f"Invalid source_confidence: {self.source_confidence}")
        
        return issues