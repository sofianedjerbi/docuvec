"""Chunk data model"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Chunk:
    """Data class for document chunk with embedding"""
    id: str
    text: str
    source_url: str
    page_title: str
    service: List[str]
    domain_exam: str
    certification: str
    provider: str
    resource_type: str  # 'cert' or 'service' - explicit from sources.yaml
    chunk_index: int
    total_chunks: int
    embedding: Optional[List[float]] = field(default=None)
    is_low_signal: bool = field(default=False)
    section_type: str = field(default="content")  # content, references, toc, etc.