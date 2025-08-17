"""Enhanced text chunking service with comprehensive metadata extraction"""

import hashlib
from typing import List, Optional, Dict, Any
from datetime import datetime

import tiktoken

from src.models import Source
from src.models.chunk import Chunk
from src.core.logger import setup_logger
from src.services.text_processor import TextProcessor
from src.services.structure_chunker import StructureChunker
from src.utils.chunk_enrichment import ChunkEnricher


class TextChunkerV2:
    """Enhanced service for chunking text with rich metadata"""
    
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
        self.enricher = ChunkEnricher()
    
    def _generate_chunk_id(self, doc_id: str, chunk_index: int, chunk_text: str) -> str:
        """Generate stable chunk ID with document reference"""
        content_hash = hashlib.sha1(chunk_text.encode()).hexdigest()[:8]
        return f"{doc_id}#{chunk_index:05d}-{content_hash}"
    
    def create_chunks(self, source: Source, content: str, 
                     html_content: Optional[str] = None,
                     metadata: Optional[Dict] = None,
                     use_structure: bool = True) -> List[Chunk]:
        """
        Create enhanced chunk objects from source and content
        
        Args:
            source: Source object with metadata
            content: Cleaned text content to chunk
            html_content: Original HTML for metadata extraction
            metadata: Additional metadata from extraction
            use_structure: Whether to use structure-aware chunking
        """
        if not content:
            return []
        
        chunks = []
        tags = source.tags
        metadata = metadata or {}
        
        # Generate document ID and parse URL
        doc_id = self.enricher.generate_doc_id(source.url)
        canonical_url, domain, path = self.enricher.parse_url_components(source.url)
        
        # Detect content type
        content_type = tags.get('content_type', 'html')
        if source.url.endswith('.pdf'):
            content_type = 'pdf'
        elif source.url.endswith('.md'):
            content_type = 'markdown'
        elif source.url.endswith('.docx'):
            content_type = 'docx'
        
        # Extract language
        html_lang = metadata.get('language') or tags.get('language')
        language = self.enricher.detect_language(content, html_lang)
        
        # Extract dates from metadata
        published_at, modified_at = self.enricher.extract_dates_from_metadata(metadata)
        
        # Extract robots meta if HTML available
        noindex, nofollow = False, False
        if html_content:
            noindex, nofollow = self.enricher.extract_robots_meta(html_content)
        
        # Calculate source confidence
        source_confidence = self.enricher.calculate_source_confidence(domain, content)
        
        # Track character offsets
        char_offset = 0
        
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
                
                # Convert structured chunks to enhanced Chunk objects
                for i, s_chunk in enumerate(structured_chunks):
                    # Extract content features
                    features = self.enricher.detect_content_features(s_chunk.text)
                    
                    # Calculate retrieval weight
                    retrieval_weight = self.enricher.calculate_retrieval_weight(
                        s_chunk.text,
                        s_chunk.hierarchical_title,
                        "structured"
                    )
                    
                    # Determine low signal reason
                    low_signal_reason = self.enricher.detect_low_signal_reason(
                        s_chunk.text,
                        s_chunk.is_low_signal
                    )
                    
                    # Calculate character positions
                    chunk_char_start = char_offset
                    chunk_char_end = char_offset + len(s_chunk.text)
                    char_offset = chunk_char_end - self.overlap_tokens * 4  # Approximate char overlap
                    
                    chunk = Chunk(
                        # Core fields
                        id=self._generate_chunk_id(doc_id, i, s_chunk.text),
                        doc_id=doc_id,
                        text=s_chunk.text,
                        
                        # URL components
                        source_url=source.url,
                        canonical_url=canonical_url,
                        domain=domain,
                        path=path,
                        
                        # Content metadata
                        page_title=s_chunk.hierarchical_title,
                        title_hierarchy=s_chunk.headings[:3],  # Limit to 3 levels
                        lang=language,
                        format=content_type,
                        
                        # Timestamps
                        published_at=published_at,
                        modified_at=modified_at,
                        crawl_ts=datetime.now(),
                        
                        # Content hashing
                        content_sha1=self.enricher.compute_content_hash(s_chunk.text),
                        simhash=self.enricher.compute_simhash(s_chunk.text),
                        
                        # Chunk metadata
                        chunk_index=s_chunk.chunk_index,
                        total_chunks=s_chunk.total_chunks,
                        chunk_char_start=chunk_char_start,
                        chunk_char_end=chunk_char_end,
                        tokens=s_chunk.token_count,
                        
                        # Quality and relevance
                        is_low_signal=s_chunk.is_low_signal,
                        low_signal_reason=low_signal_reason,
                        retrieval_weight=retrieval_weight,
                        source_confidence=source_confidence,
                        section_type="structured",
                        
                        # Content features
                        headings=features['headings'],
                        has_code=features['has_code'],
                        has_table=features['has_table'],
                        has_list=features['has_list'],
                        links_out=features['links_out'],
                        
                        # Compliance
                        noindex=noindex,
                        nofollow=nofollow,
                        
                        # Legacy fields
                        service=tags.get('service', []),
                        domain_exam=tags.get('domain_exam', ''),
                        certification=tags.get('certification', ''),
                        provider=tags.get('provider', ''),
                        resource_type=tags.get('type', 'document'),
                    )
                    
                    chunks.append(chunk)
                
                if chunks:
                    self.logger.info(f"Created {len(chunks)} enhanced structure-aware chunks for {source.id}")
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
        
        # Create enhanced chunk objects
        for i, chunk_text in enumerate(text_chunks):
            # Extract content features
            features = self.enricher.detect_content_features(chunk_text)
            
            # Calculate retrieval weight
            retrieval_weight = self.enricher.calculate_retrieval_weight(
                chunk_text,
                source.title,
                "simple"
            )
            
            # Calculate character positions
            chunk_char_start = char_offset
            chunk_char_end = char_offset + len(chunk_text)
            char_offset = chunk_char_end - self.overlap_tokens * 4
            
            # Count tokens
            tokens = len(self.tokenizer.encode(chunk_text))
            
            chunk = Chunk(
                # Core fields
                id=self._generate_chunk_id(doc_id, i, chunk_text),
                doc_id=doc_id,
                text=chunk_text,
                
                # URL components
                source_url=source.url,
                canonical_url=canonical_url,
                domain=domain,
                path=path,
                
                # Content metadata
                page_title=source.title,
                title_hierarchy=[source.title],
                lang=language,
                format=content_type,  # Map old field name to new
                
                # Timestamps
                published_at=published_at,
                modified_at=modified_at,
                crawl_ts=datetime.now(),
                
                # Content hashing
                content_sha1=self.enricher.compute_content_hash(chunk_text),
                simhash=self.enricher.compute_simhash(chunk_text),
                
                # Chunk metadata
                chunk_index=i,
                total_chunks=len(text_chunks),
                chunk_char_start=chunk_char_start,
                chunk_char_end=chunk_char_end,
                tokens=tokens,
                
                # Quality and relevance
                is_low_signal=False,
                low_signal_reason="",
                retrieval_weight=retrieval_weight,
                source_confidence=source_confidence,
                section_type="simple",
                
                # Content features
                headings=features['headings'],
                has_code=features['has_code'],
                has_table=features['has_table'],
                has_list=features['has_list'],
                links_out=features['links_out'],
                
                # Compliance
                noindex=noindex,
                nofollow=nofollow,
                
                # Legacy fields
                service=tags.get('service', []),
                domain_exam=tags.get('domain_exam', ''),
                certification=tags.get('certification', ''),
                provider=tags.get('provider', ''),
                resource_type=tags.get('type', 'document'),
            )
            
            chunks.append(chunk)
        
        self.logger.info(f"Created {len(chunks)} enhanced simple chunks for {source.id}")
        return chunks
    
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