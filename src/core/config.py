"""Configuration management"""

import os
from pathlib import Path
from dotenv import load_dotenv


class Config:
    """Centralized configuration management"""
    
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        # Paths
        self.sources_file = "sources.yaml"
        self.output_dir = Path("data")
        self.cache_dir = self.output_dir / "cache"
        self.chunks_dir = self.output_dir / "chunks"
        self.embeds_dir = self.output_dir / "embeds"
        
        # Create directories
        self._create_directories()
        
        # OpenAI settings
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        # Embedding settings
        self.embed_model = os.getenv("EMBED_MODEL", "text-embedding-3-small")
        self.embed_batch_size = int(os.getenv("EMBED_BATCH", "64"))
        
        # Chunking settings
        self.max_tokens = int(os.getenv("MAX_TOKENS", "700"))
        self.overlap_tokens = int(os.getenv("OVERLAP_TOKENS", "80"))
        self.min_tokens = int(os.getenv("MIN_TOKENS", "40"))
        
        # Rate limiting
        self.request_delay = float(os.getenv("REQUEST_DELAY", "1.0"))
        self.embedding_delay = float(os.getenv("EMBEDDING_DELAY", "0.1"))
        
        # Network settings
        self.max_retries = int(os.getenv("MAX_RETRIES", "4"))
        self.timeout = int(os.getenv("TIMEOUT", "30"))
        
        # Content extraction settings
        self.enable_ocr = os.getenv("ENABLE_OCR", "false").lower() == "true"
    
    def _create_directories(self):
        """Create necessary directories"""
        for directory in [self.output_dir, self.cache_dir, self.chunks_dir, self.embeds_dir]:
            directory.mkdir(parents=True, exist_ok=True)
    
    @property
    def cache_file(self) -> Path:
        """Get cache file path"""
        return self.cache_dir / "content_cache.json"
    
    @property
    def summary_file(self) -> Path:
        """Get summary file path"""
        return self.output_dir / "summary.json"