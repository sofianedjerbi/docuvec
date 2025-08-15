"""Text chunking service using token-based splitting"""

import hashlib
from typing import List

import tiktoken

from src.models import Source, Chunk
from src.core.logger import setup_logger
from src.services.text_processor import TextProcessor


class TextChunker:
    """Service for chunking text into token-based segments"""
    
    def __init__(self, max_tokens: int = 700, overlap_tokens: int = 80, min_tokens: int = 40):
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens
        self.min_tokens = min_tokens
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
        self.logger = setup_logger(self.__class__.__name__)
        self.text_processor = TextProcessor()
    
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
    
    def create_chunks(self, source: Source, content: str) -> List[Chunk]:
        """Create chunk objects from source and content"""
        if not content:
            return []
        
        # Split into text chunks
        text_chunks = self.chunk_text(content)
        
        if not text_chunks:
            self.logger.warning(f"No valid chunks created for {source.id}")
            return []
        
        # Deduplicate chunks
        text_chunks = self.text_processor.deduplicate_chunks(text_chunks)
        
        chunks = []
        tags = source.tags
        
        # Extract metadata
        service = tags.get('service', [])
        if isinstance(service, str):
            service = [service]
        
        domain_exam = tags.get('domain_exam', '')
        certification = tags.get('certification', '')
        provider = tags.get('provider', 'AWS')
        resource_type = tags.get('type', 'cert')  # Explicit type from sources.yaml
        
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
                total_chunks=len(text_chunks)
            )
            
            chunks.append(chunk)
        
        self.logger.info(f"Created {len(chunks)} chunks for {source.id}")
        return chunks