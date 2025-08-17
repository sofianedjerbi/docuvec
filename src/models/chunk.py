"""Production-ready chunk schema with comprehensive metadata and compliance"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from enum import Enum


class SourceType(Enum):
    """Source content types"""
    OFFICIAL_DOCS = "official_docs"
    ACADEMIC = "academic"
    NEWS = "news"
    COMMUNITY = "community"
    INTERNAL = "internal"
    DATASET = "dataset"
    LEGAL = "legal"
    CODE = "code"
    LOG = "log"


class Modality(Enum):
    """Content modality types"""
    TEXT = "text"
    TABLE = "table"
    CODE = "code"
    EQUATION = "equation"
    FIGURE = "figure"
    METADATA = "metadata"


class Format(Enum):
    """Content format types"""
    HTML = "html"
    PDF = "pdf"
    MARKDOWN = "md"
    DOCX = "docx"
    TXT = "txt"
    LATEX = "latex"
    JSON = "json"
    CSV = "csv"
    PARQUET = "parquet"
    RST = "rst"
    OTHER = "other"


class Sensitivity(Enum):
    """Data sensitivity levels"""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


@dataclass
class Entity:
    """Named entity structure"""
    text: str
    type: str  # PERSON, ORG, DRUG, LOCATION, DATE, etc.
    start: int
    end: int
    confidence: float = 1.0


@dataclass
class Citation:
    """Citation/reference structure"""
    doi: Optional[str] = None
    title: Optional[str] = None
    authors: List[str] = field(default_factory=list)
    year: Optional[int] = None
    url: Optional[str] = None
    citation_text: Optional[str] = None


@dataclass
class TableSchema:
    """Table structure metadata"""
    columns: List[Dict[str, Any]]  # [{"name": "Age", "type": "numeric", "unit": "years"}]
    rows: int = 0
    has_header: bool = True
    caption: Optional[str] = None


@dataclass
class PageSpan:
    """Page span for PDFs and paginated content"""
    page: int
    char_start: int
    char_end: int


@dataclass
class Chunk:
    """
    Comprehensive chunk schema implementing the complete specification
    with SOLID principles and production-ready features.
    """
    
    # === IDENTITY === (Single Responsibility: Unique identification)
    id: str  # <doc_id>#<chunk_index>-<content_sha1[0:8]>
    doc_id: str  # Stable per source doc (canonical URL or file hash)
    
    # === SOURCE & PROVENANCE === (Single Responsibility: Source tracking)
    source_type: str = "official_docs"  # Use SourceType enum values
    source_url: str = ""
    canonical_url: str = ""
    repository: Optional[str] = None  # github|s3|sharepoint|confluence|gdrive|filesystem
    domain: str = ""
    path: str = "/"
    ref_fragment: Optional[str] = None  # URL fragment/anchor
    
    # === CONTENT === (Single Responsibility: Content storage)
    modality: str = "text"  # Use Modality enum values
    format: str = "html"  # Use Format enum values
    lang: str = "en"
    language_confidence: float = 0.99
    text: str = ""
    tokens: int = 0
    byte_len: int = 0
    
    # === STRUCTURE & POSITION === (Single Responsibility: Document structure)
    page_title: str = ""
    title_hierarchy: List[str] = field(default_factory=list)
    section_id: Optional[str] = None
    parent_section_id: Optional[str] = None
    headings: List[str] = field(default_factory=list)
    chunk_index: int = 0
    total_chunks: int = 0
    char_start: Optional[int] = None
    char_end: Optional[int] = None
    page_spans: List[PageSpan] = field(default_factory=list)
    
    # === SEMANTICS === (Single Responsibility: Semantic analysis)
    keyphrases: List[str] = field(default_factory=list)
    entities: List[Entity] = field(default_factory=list)
    topics: List[str] = field(default_factory=list)
    math_latex: List[str] = field(default_factory=list)
    code_langs: List[str] = field(default_factory=list)
    table_schema: Optional[TableSchema] = None
    units: List[str] = field(default_factory=list)
    citations: List[Citation] = field(default_factory=list)
    links_out: int = 0
    
    # === QUALITY & RETRIEVAL SIGNALS === (Single Responsibility: Quality metrics)
    is_low_signal: bool = False
    low_signal_reason: str = ""  # nav|footer|legal|toc|ads
    retrieval_weight: float = 1.0  # [0.0-1.5]; FAQs ~1.2, boilerplate ~0.5
    source_confidence: float = 1.0  # [0-1]; official=1.0, community~0.7
    ocr_confidence: Optional[float] = None  # PDFs/Scans only
    quality_score: float = 0.92  # Internal heuristic
    
    # === COMPLIANCE, SAFETY & SENSITIVITY === (Single Responsibility: Compliance)
    license: Optional[str] = None  # CC-BY-4.0, MIT, etc.
    robots_noindex: bool = False
    robots_nofollow: bool = False
    sensitivity: str = "public"  # Use Sensitivity enum values
    pii: bool = False
    pii_types: List[str] = field(default_factory=list)  # ["NAME","EMAIL","MRN"]
    content_warnings: List[str] = field(default_factory=list)  # ["medical","legal"]
    data_subjects: List[str] = field(default_factory=list)  # ["patients","employees"]
    consent_basis: Optional[str] = None  # consent|contract|public_interest
    
    # === TEMPORAL === (Single Responsibility: Time tracking)
    published_at: Optional[datetime] = None
    modified_at: Optional[datetime] = None
    crawl_ts: datetime = field(default_factory=datetime.now)
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None
    
    # === HASHING & DEDUP === (Single Responsibility: Deduplication)
    content_sha1: str = ""  # Exact dedupe
    doc_sha1: str = ""
    simhash: str = ""  # Near-duplicate detection
    
    # === ATTRIBUTION === (Single Responsibility: Attribution tracking)
    authors: List[str] = field(default_factory=list)
    organizations: List[str] = field(default_factory=list)
    reviewers: List[str] = field(default_factory=list)
    contact: Optional[str] = None
    
    # === LOCALE & JURISDICTION === (Single Responsibility: Legal context)
    locale: Optional[str] = None  # en_US, fr_FR, etc.
    jurisdiction: List[str] = field(default_factory=list)  # ["US", "EU"]
    
    # === VERSIONING === (Open/Closed Principle: Extensible without modification)
    schema_version: str = "1.0.0"
    
    # === EMBEDDINGS === (Liskov Substitution: Compatible with v2)
    embedding: Optional[List[float]] = None
    embedding_model: Optional[str] = None
    embedding_dim: Optional[int] = None
    
    # === BACKWARD COMPATIBILITY === (Legacy fields)
    category: str = "general"  # Legacy field for compatibility
    subcategory: str = ""  # Legacy field for compatibility
    tags: List[str] = field(default_factory=list)  # Legacy field for compatibility
    metadata: Dict[str, Any] = field(default_factory=dict)  # Legacy field for compatibility
    service: List[str] = field(default_factory=list)  # Legacy field
    domain_exam: str = ""  # Legacy field
    certification: str = ""  # Legacy field
    provider: str = ""  # Legacy field
    resource_type: str = "document"  # Legacy field
    section_type: str = "content"  # Legacy field ("content" | "structured" | "simple")
    
    @property
    def content_type(self) -> str:
        """Backward compatibility property that returns format"""
        return self.format
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = {
            # Identity
            "id": self.id,
            "doc_id": self.doc_id,
            
            # Source & Provenance
            "source_type": self.source_type,
            "source_url": self.source_url,
            "canonical_url": self.canonical_url,
            "repository": self.repository,
            "domain": self.domain,
            "path": self.path,
            "ref_fragment": self.ref_fragment,
            
            # Content
            "modality": self.modality,
            "format": self.format,
            "lang": self.lang,
            "language_confidence": self.language_confidence,
            "text": self.text,
            "tokens": self.tokens,
            "byte_len": self.byte_len,
            
            # Structure & Position
            "page_title": self.page_title,
            "title_hierarchy": self.title_hierarchy,
            "section_id": self.section_id,
            "parent_section_id": self.parent_section_id,
            "headings": self.headings,
            "chunk_index": self.chunk_index,
            "total_chunks": self.total_chunks,
            "char_start": self.char_start,
            "char_end": self.char_end,
            "page_spans": [{"page": ps.page, "char_start": ps.char_start, "char_end": ps.char_end} 
                          for ps in self.page_spans],
            
            # Semantics
            "keyphrases": self.keyphrases,
            "entities": [{"text": e.text, "type": e.type, "start": e.start, "end": e.end} 
                        for e in self.entities],
            "topics": self.topics,
            "math_latex": self.math_latex,
            "code_langs": self.code_langs,
            "table_schema": {"columns": self.table_schema.columns, "rows": self.table_schema.rows} 
                           if self.table_schema else None,
            "units": self.units,
            "citations": [{"doi": c.doi, "title": c.title, "year": c.year} 
                         for c in self.citations],
            "links_out": self.links_out,
            
            # Quality & Retrieval Signals
            "is_low_signal": self.is_low_signal,
            "low_signal_reason": self.low_signal_reason,
            "retrieval_weight": self.retrieval_weight,
            "source_confidence": self.source_confidence,
            "ocr_confidence": self.ocr_confidence,
            "quality_score": self.quality_score,
            
            # Compliance, Safety & Sensitivity
            "license": self.license,
            "robots_noindex": self.robots_noindex,
            "robots_nofollow": self.robots_nofollow,
            "sensitivity": self.sensitivity,
            "pii": self.pii,
            "pii_types": self.pii_types,
            "content_warnings": self.content_warnings,
            "data_subjects": self.data_subjects,
            "consent_basis": self.consent_basis,
            
            # Temporal
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "modified_at": self.modified_at.isoformat() if self.modified_at else None,
            "crawl_ts": self.crawl_ts.isoformat(),
            "valid_from": self.valid_from.isoformat() if self.valid_from else None,
            "valid_to": self.valid_to.isoformat() if self.valid_to else None,
            
            # Hashing & Dedup
            "content_sha1": self.content_sha1,
            "doc_sha1": self.doc_sha1,
            "simhash": self.simhash,
            
            # Attribution
            "authors": self.authors,
            "organizations": self.organizations,
            "reviewers": self.reviewers,
            "contact": self.contact,
            
            # Locale & Jurisdiction
            "locale": self.locale,
            "jurisdiction": self.jurisdiction,
            
            # Versioning
            "schema_version": self.schema_version,
            
            # Backward compatibility fields
            "category": self.category,
            "subcategory": self.subcategory,
            "tags": self.tags,
            "metadata": self.metadata,
            "service": self.service,
            "domain_exam": self.domain_exam,
            "certification": self.certification,
            "provider": self.provider,
            "resource_type": self.resource_type,
            "section_type": self.section_type,
        }
        
        # Add embedding if present
        if self.embedding is not None:
            result["embedding"] = self.embedding
            result["embedding_model"] = self.embedding_model
            result["embedding_dim"] = self.embedding_dim
        
        return result
    
    def validate(self) -> Tuple[bool, List[str]]:
        """
        Validate chunk data completeness and correctness
        
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []
        
        # Required fields validation
        if not self.id:
            issues.append("Missing chunk ID")
        if not self.doc_id:
            issues.append("Missing document ID")
        if not self.text and self.modality == "text":
            issues.append("Missing text content for text modality")
        
        # ID format validation
        if self.id and not ("#" in self.id and "-" in self.id):
            issues.append(f"Invalid ID format: {self.id}")
        
        # Range validations
        if not (0.0 <= self.retrieval_weight <= 1.5):
            issues.append(f"Invalid retrieval_weight: {self.retrieval_weight}")
        if not (0.0 <= self.source_confidence <= 1.0):
            issues.append(f"Invalid source_confidence: {self.source_confidence}")
        if not (0.0 <= self.quality_score <= 1.0):
            issues.append(f"Invalid quality_score: {self.quality_score}")
        if self.language_confidence and not (0.0 <= self.language_confidence <= 1.0):
            issues.append(f"Invalid language_confidence: {self.language_confidence}")
        if self.ocr_confidence is not None and not (0.0 <= self.ocr_confidence <= 1.0):
            issues.append(f"Invalid ocr_confidence: {self.ocr_confidence}")
        
        # Logical validations
        if self.chunk_index >= self.total_chunks and self.total_chunks > 0:
            issues.append(f"chunk_index ({self.chunk_index}) >= total_chunks ({self.total_chunks})")
        if self.char_start is not None and self.char_end is not None:
            if self.char_start >= self.char_end:
                issues.append(f"char_start ({self.char_start}) >= char_end ({self.char_end})")
        
        # Enum validations
        valid_source_types = [st.value for st in SourceType]
        if self.source_type not in valid_source_types:
            issues.append(f"Invalid source_type: {self.source_type}")
        
        valid_modalities = [m.value for m in Modality]
        if self.modality not in valid_modalities:
            issues.append(f"Invalid modality: {self.modality}")
        
        valid_formats = [f.value for f in Format]
        if self.format not in valid_formats:
            issues.append(f"Invalid format: {self.format}")
        
        valid_sensitivities = [s.value for s in Sensitivity]
        if self.sensitivity not in valid_sensitivities:
            issues.append(f"Invalid sensitivity: {self.sensitivity}")
        
        # Hash validations
        if self.content_sha1 and len(self.content_sha1) != 40:
            issues.append(f"Invalid content_sha1 length: {len(self.content_sha1)}")
        
        return len(issues) == 0, issues
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Chunk":
        """Create Chunk instance from dictionary"""
        # Convert datetime strings back to datetime objects
        for field in ["published_at", "modified_at", "crawl_ts", "valid_from", "valid_to"]:
            if field in data and data[field]:
                if isinstance(data[field], str):
                    data[field] = datetime.fromisoformat(data[field])
        
        # Convert entity dicts to Entity objects
        if "entities" in data:
            data["entities"] = [Entity(**e) for e in data["entities"]]
        
        # Convert citation dicts to Citation objects
        if "citations" in data:
            data["citations"] = [Citation(**c) for c in data["citations"]]
        
        # Convert table_schema dict to TableSchema object
        if "table_schema" in data and data["table_schema"]:
            data["table_schema"] = TableSchema(**data["table_schema"])
        
        # Convert page_spans dicts to PageSpan objects
        if "page_spans" in data:
            data["page_spans"] = [PageSpan(**ps) for ps in data["page_spans"]]
        
        return cls(**data)
    
    def calculate_quality_score(self) -> float:
        """
        Calculate overall quality score based on multiple signals
        (Dependency Inversion: Depends on abstractions, not concrete implementations)
        """
        score = 1.0
        
        # Content quality factors
        if self.is_low_signal:
            score *= 0.5
        if len(self.text) < 50:
            score *= 0.7
        if self.tokens < 10:
            score *= 0.6
        
        # Source quality factors
        score *= self.source_confidence
        
        # Modality adjustments
        if self.modality == "metadata":
            score *= 0.8
        elif self.modality in ["table", "code", "equation"]:
            score *= 1.1
        
        # OCR quality (if applicable)
        if self.ocr_confidence is not None:
            score *= self.ocr_confidence
        
        # Semantic richness
        if self.entities:
            score *= 1.05
        if self.keyphrases:
            score *= 1.05
        if self.citations:
            score *= 1.1
        
        # Clamp to valid range
        return max(0.0, min(1.0, score))
    
    def is_expired(self, reference_date: Optional[datetime] = None) -> bool:
        """Check if chunk is expired based on validity dates"""
        if reference_date is None:
            reference_date = datetime.now()
        
        if self.valid_to and reference_date > self.valid_to:
            return True
        if self.valid_from and reference_date < self.valid_from:
            return True
        
        return False
    
    def requires_attribution(self) -> bool:
        """Check if content requires attribution based on license"""
        attribution_licenses = ["CC-BY", "CC-BY-SA", "CC-BY-NC", "CC-BY-NC-SA", "CC-BY-ND"]
        if self.license:
            return any(self.license.startswith(lic) for lic in attribution_licenses)
        return False
    
    def get_attribution_text(self) -> Optional[str]:
        """Generate attribution text if required"""
        if not self.requires_attribution():
            return None
        
        parts = []
        if self.authors:
            parts.append(f"By {', '.join(self.authors)}")
        if self.organizations:
            parts.append(f"({', '.join(self.organizations)})")
        if self.license:
            parts.append(f"Licensed under {self.license}")
        if self.source_url:
            parts.append(f"Source: {self.source_url}")
        
        return " ".join(parts) if parts else None