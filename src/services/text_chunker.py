"""Text chunking service using token-based splitting"""

import hashlib
from typing import List, Optional, Dict, Any

import tiktoken

from src.models import Source, Chunk
from src.core.logger import setup_logger
from src.services.text_processor import TextProcessor
from src.services.structure_chunker import StructureChunker, StructuredChunk


class TextChunker:
    """Service for chunking text into token-based segments"""
    
    def __init__(self, max_tokens: int = 700, overlap_tokens: int = 80, min_tokens: int = 40):
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens
        self.min_tokens = min_tokens
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
        self.logger = setup_logger(self.__class__.__name__)
        self.text_processor = TextProcessor()
        self.structure_chunker = StructureChunker(
            max_tokens=max_tokens,
            overlap_tokens=overlap_tokens,
            min_tokens=min_tokens
        )
    
    def _generate_chunk_id(self, source_id: str, chunk_index: int, chunk_text: str) -> str:
        """Generate stable chunk ID with content hash"""
        content_hash = hashlib.sha1(chunk_text.encode()).hexdigest()[:16]
        return f"{source_id}#{chunk_index:05d}-{content_hash}"
    
    def chunk_text(self, text: str) -> List[str]:
        """Split text into chunks by tokens with overlap"""
        if not text:
            return []
        
        # Encode text to tokens
        tokens = self.tokenizer.encode(text)
        
        if len(tokens) <= self.max_tokens:
            # Check minimum token threshold
            if len(tokens) < self.min_tokens:
                return []
            return [text]
        
        chunks = []
        i = 0
        
        while i < len(tokens):
            # Get chunk of tokens
            end_idx = min(i + self.max_tokens, len(tokens))
            chunk_tokens = tokens[i:end_idx]
            
            # Skip chunks that are too small
            if len(chunk_tokens) < self.min_tokens:
                i += (self.max_tokens - self.overlap_tokens)
                continue
            
            # Decode back to text
            chunk_text = self.tokenizer.decode(chunk_tokens)
            chunks.append(chunk_text)
            
            # Move forward with overlap
            if end_idx >= len(tokens):
                break
            i += (self.max_tokens - self.overlap_tokens)
        
        return chunks
    
    def create_chunks(self, source: Source, content: str, use_structure: bool = True) -> List[Chunk]:
        """
        Create chunk objects from source and content
        
        Args:
            source: Source object with metadata
            content: Text content to chunk
            use_structure: Whether to use structure-aware chunking
        """
        if not content:
            return []
        
        chunks = []
        tags = source.tags
        
        # Extract metadata
        service = tags.get('service', [])
        if isinstance(service, str):
            service = [service]
        
        domain_exam = tags.get('domain_exam', '')
        certification = tags.get('certification', '')
        provider = tags.get('provider', '')  # No default provider
        resource_type = tags.get('type', 'document')  # Generic default
        language = tags.get('language', 'en')
        
        if use_structure:
            # Try structure-aware chunking first
            try:
                structured_chunks = self.structure_chunker.chunk_text(
                    content,
                    page_title=source.title,
                    page_language=language,
                    metadata={
                        'source_id': source.id,
                        'url': source.url
                    }
                )
                
                # Convert structured chunks to Chunk objects
                for i, s_chunk in enumerate(structured_chunks):
                    # Skip low-signal chunks if configured
                    if s_chunk.is_low_signal:
                        self.logger.debug(f"Skipping low-signal chunk {i} from {source.id}")
                        continue
                    
                    chunk = Chunk(
                        id=s_chunk.chunk_id,
                        text=s_chunk.text,
                        source_url=source.url,
                        page_title=s_chunk.hierarchical_title,  # Use hierarchical title
                        service=service,
                        domain_exam=domain_exam,
                        certification=certification,
                        provider=provider,
                        resource_type=resource_type,
                        chunk_index=s_chunk.chunk_index,
                        total_chunks=s_chunk.total_chunks,
                        is_low_signal=s_chunk.is_low_signal,
                        section_type="structured"  # Mark as structure-aware
                    )
                    chunks.append(chunk)
                
                if chunks:
                    self.logger.info(f"Created {len(chunks)} structure-aware chunks for {source.id}")
                    return chunks
                
            except Exception as e:
                self.logger.warning(f"Structure chunking failed for {source.id}, falling back: {e}")
        
        # Fallback to simple token-based chunking
        text_chunks = self.chunk_text(content)
        
        if not text_chunks:
            self.logger.warning(f"No valid chunks created for {source.id}")
            return []
        
        # Deduplicate chunks
        text_chunks = self.text_processor.deduplicate_chunks(text_chunks)
        
        # Create chunk objects
        for i, chunk_text in enumerate(text_chunks):
            chunk_id = self._generate_chunk_id(source.id, i, chunk_text)
            
            chunk = Chunk(
                id=chunk_id,
                text=chunk_text,
                source_url=source.url,
                page_title=source.title,
                service=service,
                domain_exam=domain_exam,
                certification=certification,
                provider=provider,
                resource_type=resource_type,
                chunk_index=i,
                total_chunks=len(text_chunks),
                section_type="simple"  # Mark as simple chunking
            )
            
            chunks.append(chunk)
        
        self.logger.info(f"Created {len(chunks)} simple chunks for {source.id}")
        return chunks