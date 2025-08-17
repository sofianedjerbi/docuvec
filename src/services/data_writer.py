"""Data writer service for organized JSONL output"""

import json
import time
from typing import List, Dict, Any, Tuple
from pathlib import Path
from collections import defaultdict

from src.models import Chunk
from src.core.logger import setup_logger


class DataWriter:
    """Service for writing data to organized JSONL format"""
    
    def __init__(self, chunks_dir: Path, embeds_dir: Path, summary_file: Path):
        self.chunks_dir = chunks_dir
        self.embeds_dir = embeds_dir
        self.summary_file = summary_file
        self.logger = setup_logger(self.__class__.__name__)
        
        # Base directories will be created on demand based on actual data
        self.chunks_dir.mkdir(parents=True, exist_ok=True)
        self.embeds_dir.mkdir(parents=True, exist_ok=True)
    
    def _serialize_datetime(self, dt) -> str:
        """Convert datetime object to ISO format string for JSON serialization"""
        if dt is None:
            return None
        if hasattr(dt, 'isoformat'):
            return dt.isoformat()
        # If it's already a string, return as-is
        return dt

    def _write_jsonl(self, path: Path, records: List[Dict[str, Any]]):
        """Write records to JSONL format"""
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with path.open("w", encoding="utf-8") as f:
            for record in records:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
    
    def _build_chunk_record(self, chunk: Chunk) -> dict:
        """Build chunk record with content and metadata (no embeddings)"""
        return {
            # Core identification
            "id": chunk.id,
            "doc_id": chunk.doc_id,
            "text": chunk.text,
            
            # URL and source info
            "source_url": chunk.source_url,
            "canonical_url": chunk.canonical_url,
            "domain": chunk.domain,
            "path": chunk.path,
            
            # Content metadata
            "page_title": chunk.page_title,
            "title_hierarchy": chunk.title_hierarchy,
            "lang": chunk.lang,
            "content_type": chunk.content_type,
            
            # Chunk positioning
            "chunk_index": chunk.chunk_index,
            "total_chunks": chunk.total_chunks,
            "chunk_char_start": getattr(chunk, 'chunk_char_start', None),
            "chunk_char_end": getattr(chunk, 'chunk_char_end', None),
            "tokens": getattr(chunk, 'tokens', 0),
            
            # Content hashing for deduplication
            "content_sha1": getattr(chunk, 'content_sha1', ''),
            "simhash": getattr(chunk, 'simhash', ''),
            
            # Quality and type
            "is_low_signal": chunk.is_low_signal,
            "low_signal_reason": getattr(chunk, 'low_signal_reason', ''),
            "section_type": getattr(chunk, 'section_type', 'content'),
            "retrieval_weight": getattr(chunk, 'retrieval_weight', 1.0),
            "source_confidence": getattr(chunk, 'source_confidence', 1.0),
            
            # Content features for UI/ranking
            "headings": getattr(chunk, 'headings', []),
            "has_code": getattr(chunk, 'has_code', False),
            "has_table": getattr(chunk, 'has_table', False),
            "has_list": getattr(chunk, 'has_list', False),
            "links_out": getattr(chunk, 'links_out', 0),
            
            # Legacy fields for backward compatibility
            "provider": chunk.provider,
            "resource_type": chunk.resource_type,
            "service": getattr(chunk, 'service', []),
            "domain_exam": getattr(chunk, 'domain_exam', ''),
            "certification": getattr(chunk, 'certification', ''),
            
            # Timestamps (convert to ISO format for JSON serialization)
            "crawl_ts": self._serialize_datetime(getattr(chunk, 'crawl_ts', None)),
            "published_at": self._serialize_datetime(getattr(chunk, 'published_at', None)),
            "modified_at": self._serialize_datetime(getattr(chunk, 'modified_at', None)),
        }
    
    def _build_embed_record(self, chunk: Chunk) -> dict:
        """Build embedding record with ID and vector only"""
        return {
            "id": chunk.id,
            "embedding": chunk.embedding
        }

    def _classify_chunk(self, chunk: Chunk) -> Tuple[str, str]:
        """Get chunk type and identifier from explicit metadata
        
        Returns:
            Tuple of (type, identifier) where:
            - type is the resource type from metadata
            - identifier is the source ID (doc_id) to ensure one file per source
        """
        # Get resource type, default to 'document'
        resource_type = chunk.resource_type or 'document'
        
        # Use doc_id as identifier to ensure one file per source
        identifier = chunk.doc_id if chunk.doc_id else 'unknown'
        
        return resource_type, identifier
    
    def _organize_chunks_by_type(self, chunks: List[Chunk]) -> Dict[str, Dict[str, List[Chunk]]]:
        """Organize chunks by category and type
        
        Returns:
            Nested dict: {category: {type_identifier: [chunks]}}
        """
        organized = defaultdict(lambda: defaultdict(list))
        
        for chunk in chunks:
            # Use provider as category, or 'general' if not specified
            category = chunk.provider.lower() if chunk.provider else 'general'
            resource_type, identifier = self._classify_chunk(chunk)
            
            # Use identifier (doc_id) as key for grouping
            key = identifier
            
            organized[category][key].append(chunk)
        
        return dict(organized)
    
    def write_source_chunks(self, source, chunks: List[Chunk]) -> dict:
        """Write chunks from a single source to JSONL file immediately
        
        Args:
            source: Source object for metadata
            chunks: List of chunks from this source
            
        Returns:
            dict with file paths written
        """
        if not chunks:
            return {"chunks_file": None, "embeds_file": None}
        
        # Get provider and resource type from first chunk
        sample_chunk = chunks[0]
        category = sample_chunk.provider.lower() if sample_chunk.provider else 'general'
        resource_type = sample_chunk.resource_type or 'document'
        
        # Use source ID as filename
        filename = f"{source.id}.jsonl"
        
        # Prepare records
        chunk_records = []
        embed_records = []
        
        for chunk in chunks:
            # Build chunk record (content and metadata only)
            chunk_record = self._build_chunk_record(chunk)
            chunk_records.append(chunk_record)
            
            # Build embedding record (ID and vector only)
            if chunk.embedding:
                embed_record = self._build_embed_record(chunk)
                embed_records.append(embed_record)
        
        # Write files
        chunks_file = self.chunks_dir / category / resource_type / filename
        self._write_jsonl(chunks_file, chunk_records)
        
        embeds_file = None
        if embed_records:
            embeds_file = self.embeds_dir / category / resource_type / filename
            self._write_jsonl(embeds_file, embed_records)
        
        self.logger.info(f"✅ Wrote {len(chunk_records)} chunks to {chunks_file}")
        if embeds_file:
            self.logger.info(f"✅ Wrote {len(embed_records)} embeddings to {embeds_file}")
        
        return {
            "chunks_file": str(chunks_file),
            "embeds_file": str(embeds_file) if embeds_file else None,
            "chunk_count": len(chunk_records),
            "embed_count": len(embed_records)
        }

    def write_chunks(self, chunks: List[Chunk], embed_model: str):
        """Write chunks to JSONL files organized by provider/type"""
        if not chunks:
            self.logger.warning("No chunks to write")
            return
        
        self.logger.info(f"Writing {len(chunks)} chunks to organized JSONL format")
        
        # Organize chunks by provider and type
        organized = self._organize_chunks_by_type(chunks)
        
        # Track all written files for summary
        files_written = {
            'chunks': [],
            'embeds': []
        }
        
        # Process each category
        for category, type_groups in organized.items():
            category_dir = category.lower()
            
            # Process each type group (cert or service)
            for key, type_chunks in type_groups.items():
                chunk_records = []
                embed_records = []
                
                for chunk in type_chunks:
                    # Chunk record (text and metadata)
                    # Use to_dict() if available, otherwise fall back to manual mapping
                    if hasattr(chunk, 'to_dict'):
                        chunk_record = chunk.to_dict()
                    else:
                        # Backward compatibility for old Chunk model
                        chunk_record = {
                            "id": chunk.id,
                            "text": chunk.text,
                            "source_url": chunk.source_url,
                            "page_title": chunk.page_title,
                            "service": chunk.service,
                            "domain_exam": chunk.domain_exam,
                            "certification": chunk.certification,
                            "provider": chunk.provider,
                            "resource_type": chunk.resource_type,
                            "chunk_index": chunk.chunk_index,
                            "total_chunks": chunk.total_chunks,
                            "is_low_signal": chunk.is_low_signal,
                            "section_type": getattr(chunk, 'section_type', 'content')
                        }
                    chunk_records.append(chunk_record)
                    
                    # Embedding record (vector only)
                    if chunk.embedding:
                        embed_record = {
                            "id": chunk.id,
                            "embedding": chunk.embedding
                        }
                        embed_records.append(embed_record)
                
                # Use doc_id as filename and resource_type as subdirectory
                filename = f"{key}.jsonl"
                subdir = type_chunks[0].resource_type if type_chunks and type_chunks[0].resource_type else 'document'
                
                # Write chunk file
                chunks_file = self.chunks_dir / category_dir / subdir / filename
                self._write_jsonl(chunks_file, chunk_records)
                files_written['chunks'].append(str(chunks_file))
                self.logger.info(f"Wrote {len(chunk_records)} chunks to {chunks_file}")
                
                # Write embeddings file
                if embed_records:
                    embeds_file = self.embeds_dir / category_dir / subdir / filename
                    self._write_jsonl(embeds_file, embed_records)
                    files_written['embeds'].append(str(embeds_file))
                    self.logger.info(f"Wrote {len(embed_records)} embeddings to {embeds_file}")
        
        # Create enhanced summary
        self._write_enhanced_summary(chunks, organized, embed_model, files_written)
    
    def _write_enhanced_summary(self, chunks: List[Chunk], organized: Dict[str, Dict[str, List[Chunk]]], 
                               embed_model: str, files_written: Dict[str, List[str]]):
        """Write enhanced processing summary with file organization"""
        summary = {
            'total_chunks': len(chunks),
            'embedding_model': embed_model,
            'processing_timestamp': time.time(),
            'organization': {},
            'files_written': files_written,
            'statistics': {
                'certifications': {},
                'services': {},
                'providers': {},
                'section_types': {},
                'low_signal_count': 0
            }
        }
        
        # Build organization summary
        for category, type_groups in organized.items():
            summary['organization'][category] = {
                'documents': [],
                'services': [],
                'total_chunks': 0
            }
            
            for key, type_chunks in type_groups.items():
                chunk_count = len(type_chunks)
                summary['organization'][category]['total_chunks'] += chunk_count
                
                if key.startswith('service_'):
                    service_name = key.replace('service_', '')
                    summary['organization'][category]['services'].append({
                        'name': service_name,
                        'chunks': chunk_count,
                        'file': f"{category}/service/{service_name}.jsonl"
                    })
                else:
                    summary['organization'][category]['documents'].append({
                        'id': key,
                        'chunks': chunk_count,
                        'file': f"{category}/{type_chunks[0].resource_type if type_chunks else 'documents'}/{key}.jsonl"
                    })
        
        # Gather statistics
        for chunk in chunks:
            # Provider stats
            provider = chunk.provider
            summary['statistics']['providers'][provider] = \
                summary['statistics']['providers'].get(provider, 0) + 1
            
            # Certification stats
            cert = chunk.certification
            if cert:
                summary['statistics']['certifications'][cert] = \
                    summary['statistics']['certifications'].get(cert, 0) + 1
            
            # Service stats
            for service in chunk.service:
                if service:
                    summary['statistics']['services'][service] = \
                        summary['statistics']['services'].get(service, 0) + 1
            
            # Section type stats
            section = chunk.section_type
            summary['statistics']['section_types'][section] = \
                summary['statistics']['section_types'].get(section, 0) + 1
            
            # Low signal count
            if chunk.is_low_signal:
                summary['statistics']['low_signal_count'] += 1
        
        # Calculate percentages
        if chunks:
            low_signal_pct = (summary['statistics']['low_signal_count'] / len(chunks)) * 100
            summary['statistics']['low_signal_percentage'] = round(low_signal_pct, 2)
        
        # Write summary
        with open(self.summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        self.logger.info(f"Enhanced summary written to {self.summary_file}")
        self.logger.info(f"Organization: {summary['organization']}")