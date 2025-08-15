"""Source loader service"""

import yaml
from typing import List
from pathlib import Path

from src.models import Source
from src.core.logger import setup_logger


class SourceLoader:
    """Service for loading sources from YAML"""
    
    def __init__(self, sources_file: str):
        self.sources_file = Path(sources_file)
        self.logger = setup_logger(self.__class__.__name__)
    
    def load_sources(self) -> List[Source]:
        """Load sources from YAML file
        
        Returns:
            List of Source objects
        """
        self.logger.info(f"Loading sources from {self.sources_file}")
        
        if not self.sources_file.exists():
            raise FileNotFoundError(f"Sources file not found: {self.sources_file}")
        
        try:
            with open(self.sources_file, 'r') as f:
                data = yaml.safe_load(f)
            
            sources = []
            for item in data:
                if isinstance(item, dict) and 'id' in item:
                    sources.append(Source(
                        id=item['id'],
                        url=item['url'],
                        title=item['title'],
                        tags=item.get('tags', {})
                    ))
            
            self.logger.info(f"Loaded {len(sources)} sources")
            return sources
            
        except Exception as e:
            self.logger.error(f"Failed to load sources: {e}")
            raise