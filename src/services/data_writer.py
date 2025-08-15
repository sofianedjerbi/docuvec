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
        
        # Create organized subdirectories for each provider
        for provider in ['aws', 'azure', 'gcp']:
            # Certification directories
            (self.chunks_dir / provider / 'cert').mkdir(parents=True, exist_ok=True)
            (self.embeds_dir / provider / 'cert').mkdir(parents=True, exist_ok=True)
            
            # Service directories  
            (self.chunks_dir / provider / 'service').mkdir(parents=True, exist_ok=True)
            (self.embeds_dir / provider / 'service').mkdir(parents=True, exist_ok=True)
    
    def _write_jsonl(self, path: Path, records: List[Dict[str, Any]]):
        """Write records to JSONL format"""
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with path.open("w", encoding="utf-8") as f:
            for record in records:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
    
    def _classify_chunk(self, chunk: Chunk) -> Tuple[str, str]:
        """Get chunk type and identifier from explicit metadata
        
        Returns:
            Tuple of (type, identifier) where:
            - type is 'cert' or 'service' from metadata
            - identifier is the resource name
        """
        # Get explicit type from chunk metadata
        resource_type = chunk.resource_type  # 'cert' or 'service'
        
        if resource_type == 'cert':
            # Use certification code as identifier
            identifier = chunk.certification.lower() if chunk.certification else 'unknown'
        elif resource_type == 'service':
            # Use first service name as identifier
            if chunk.service and len(chunk.service) > 0 and chunk.service[0]:
                identifier = chunk.service[0].lower().replace(' ', '-')
            else:
                identifier = 'general'
        else:
            # Fallback if type not specified
            self.logger.warning(f"Unknown resource type '{resource_type}' for chunk {chunk.id}")
            identifier = 'unknown'
        
        return resource_type, identifier
    
    def _organize_chunks_by_type(self, chunks: List[Chunk]) -> Dict[str, Dict[str, List[Chunk]]]:
        """Organize chunks by provider and type (cert/service)
        
        Returns:
            Nested dict: {provider: {type_identifier: [chunks]}}
        """
        organized = defaultdict(lambda: defaultdict(list))
        
        for chunk in chunks:
            provider = chunk.provider.lower()
            resource_type, identifier = self._classify_chunk(chunk)
            
            # Create key based on explicit type
            if resource_type == 'service':
                key = f"service_{identifier}"  # e.g., 'service_ec2'
            else:
                key = identifier  # e.g., 'clf-c02' for cert
            
            organized[provider][key].append(chunk)
        
        return dict(organized)
    
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
        
        # Process each provider
        for provider, type_groups in organized.items():
            provider_dir = provider.lower()
            
            # Process each type group (cert or service)
            for key, type_chunks in type_groups.items():
                chunk_records = []
                embed_records = []
                
                for chunk in type_chunks:
                    # Chunk record (text and metadata)
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
                        "section_type": chunk.section_type
                    }
                    chunk_records.append(chunk_record)
                    
                    # Embedding record (vector only)
                    if chunk.embedding:
                        embed_record = {
                            "id": chunk.id,
                            "embedding": chunk.embedding
                        }
                        embed_records.append(embed_record)
                
                # Determine output path and filename
                if key.startswith('service_'):
                    # Service resource: aws/service/ec2.jsonl
                    service_name = key.replace('service_', '')
                    filename = f"{service_name}.jsonl"
                    subdir = 'service'
                else:
                    # Certification resource: aws/cert/clf-c02.jsonl
                    filename = f"{key}.jsonl"
                    subdir = 'cert'
                
                # Write chunk file
                chunks_file = self.chunks_dir / provider_dir / subdir / filename
                self._write_jsonl(chunks_file, chunk_records)
                files_written['chunks'].append(str(chunks_file))
                self.logger.info(f"Wrote {len(chunk_records)} chunks to {chunks_file}")
                
                # Write embeddings file
                if embed_records:
                    embeds_file = self.embeds_dir / provider_dir / subdir / filename
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
        for provider, type_groups in organized.items():
            summary['organization'][provider] = {
                'certifications': [],
                'services': [],
                'total_chunks': 0
            }
            
            for key, type_chunks in type_groups.items():
                chunk_count = len(type_chunks)
                summary['organization'][provider]['total_chunks'] += chunk_count
                
                if key.startswith('service_'):
                    service_name = key.replace('service_', '')
                    summary['organization'][provider]['services'].append({
                        'name': service_name,
                        'chunks': chunk_count,
                        'file': f"{provider}/service/{service_name}.jsonl"
                    })
                else:
                    summary['organization'][provider]['certifications'].append({
                        'code': key,
                        'chunks': chunk_count,
                        'file': f"{provider}/cert/{key}.jsonl"
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