"""Embeddings generation service using OpenAI API"""

import time
from typing import List, Optional

from openai import OpenAI

from src.models import Chunk
from src.core.logger import setup_logger


class EmbeddingsGenerator:
    """Service for generating embeddings using OpenAI API"""
    
    def __init__(self, model: str = "text-embedding-3-small", 
                 batch_size: int = 64, delay: float = 0.1):
        self.model = model
        self.batch_size = batch_size
        self.delay = delay
        self.client = OpenAI()  # Uses OPENAI_API_KEY from env
        self.logger = setup_logger(self.__class__.__name__)
    
    def _generate_batch(self, texts: List[str]) -> List[Optional[List[float]]]:
        """Generate embeddings for a batch of texts"""
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=texts
            )
            
            # Rate limiting
            time.sleep(self.delay)
            
            return [d.embedding for d in response.data]
            
        except Exception as e:
            self.logger.error(f"Failed to generate batch embeddings: {e}")
            return [None] * len(texts)
    
    def add_embeddings(self, chunks: List[Chunk]) -> List[Chunk]:
        """Add embeddings to chunks using batched API calls"""
        if not chunks:
            return []
        
        self.logger.info(f"Generating embeddings for {len(chunks)} chunks using {self.model}")
        
        # Process in batches
        for i in range(0, len(chunks), self.batch_size):
            batch = chunks[i:i + self.batch_size]
            texts = [chunk.text for chunk in batch]
            
            batch_num = i // self.batch_size + 1
            total_batches = (len(chunks) - 1) // self.batch_size + 1
            self.logger.info(f"Processing batch {batch_num}/{total_batches}")
            
            embeddings = self._generate_batch(texts)
            
            # Assign embeddings to chunks
            for chunk, embedding in zip(batch, embeddings):
                chunk.embedding = embedding
        
        # Filter out chunks without embeddings
        valid_chunks = [chunk for chunk in chunks if chunk.embedding is not None]
        
        self.logger.info(f"Generated embeddings for {len(valid_chunks)}/{len(chunks)} chunks")
        return valid_chunks