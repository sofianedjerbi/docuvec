"""Pipeline versioning and configuration tracking"""

import hashlib
import json
from typing import Dict, Any
from pathlib import Path
import importlib.metadata


class PipelineVersioning:
    """Track and manage pipeline versions for auditability"""
    
    SCHEMA_VERSION = "2.0.0"
    
    @staticmethod
    def get_pipeline_version() -> str:
        """
        Generate pipeline version hash from configuration and code
        
        Returns:
            Hash representing current pipeline configuration
        """
        components = {
            'schema_version': PipelineVersioning.SCHEMA_VERSION,
            'tokenizer': 'cl100k_base',
            'text_processor': '2.0',  # Version of text processing logic
            'structure_chunker': '2.0',  # Version of chunking logic
            'html_extractor': '2.0',  # Version of extraction logic
        }
        
        # Try to get package versions
        try:
            components['trafilatura'] = importlib.metadata.version('trafilatura')
        except:
            components['trafilatura'] = 'unknown'
        
        try:
            components['tiktoken'] = importlib.metadata.version('tiktoken')
        except:
            components['tiktoken'] = 'unknown'
        
        # Create stable hash
        version_string = json.dumps(components, sort_keys=True)
        return hashlib.sha256(version_string.encode()).hexdigest()[:12]
    
    @staticmethod
    def get_embedding_config(model: str = "text-embedding-3-small") -> Dict[str, Any]:
        """
        Get embedding model configuration
        
        Args:
            model: Embedding model name
            
        Returns:
            Configuration dictionary
        """
        configs = {
            "text-embedding-3-small": {
                "model": "text-embedding-3-small",
                "dim": 1536,
                "max_tokens": 8191,
                "provider": "openai"
            },
            "text-embedding-3-large": {
                "model": "text-embedding-3-large",
                "dim": 3072,
                "max_tokens": 8191,
                "provider": "openai"
            },
            "text-embedding-ada-002": {
                "model": "text-embedding-ada-002",
                "dim": 1536,
                "max_tokens": 8191,
                "provider": "openai"
            }
        }
        
        return configs.get(model, {
            "model": model,
            "dim": 1536,
            "max_tokens": 8000,
            "provider": "unknown"
        })
    
    @staticmethod
    def get_source_type(url: str, upload_path: Optional[str] = None) -> str:
        """
        Determine source type from URL or path
        
        Args:
            url: Source URL
            upload_path: Optional upload path
            
        Returns:
            Source type: "crawl" | "upload" | "api" | "file"
        """
        if upload_path:
            return "upload"
        
        if url.startswith("file://"):
            return "file"
        
        # Check for API patterns
        api_patterns = ['/api/', '/v1/', '/v2/', '/graphql', '.json', '/rest/']
        if any(pattern in url.lower() for pattern in api_patterns):
            return "api"
        
        return "crawl"
    
    @staticmethod
    def detect_license(text: str, metadata: Dict[str, Any]) -> tuple[str, bool]:
        """
        Detect content license from text or metadata
        
        Args:
            text: Content text
            metadata: Extracted metadata
            
        Returns:
            Tuple of (license, attribution_required)
        """
        # Check metadata first
        license_fields = ['license', 'rights', 'copyright', 'dc.rights']
        for field in license_fields:
            if field in metadata and metadata[field]:
                license_text = str(metadata[field]).lower()
                
                # Common licenses
                if 'creative commons' in license_text or 'cc-by' in license_text:
                    return 'CC-BY-4.0', True
                elif 'cc0' in license_text or 'public domain' in license_text:
                    return 'CC0-1.0', False
                elif 'mit' in license_text:
                    return 'MIT', True
                elif 'apache' in license_text:
                    return 'Apache-2.0', True
                elif 'gpl' in license_text:
                    return 'GPL-3.0', True
        
        # Check text for license indicators
        text_lower = text[:5000].lower() if text else ''  # Check first 5000 chars
        
        if 'creative commons' in text_lower:
            if 'attribution' in text_lower or 'cc-by' in text_lower:
                return 'CC-BY-4.0', True
            elif 'cc0' in text_lower:
                return 'CC0-1.0', False
        
        if 'all rights reserved' in text_lower:
            return 'proprietary', True
        
        if 'public domain' in text_lower:
            return 'public-domain', False
        
        # Default to unknown with attribution for safety
        return '', False
    
    @staticmethod
    def create_anchor_url(canonical_url: str, anchor_id: str = "", 
                         page_num: Optional[int] = None) -> str:
        """
        Create precise anchor URL for deep linking
        
        Args:
            canonical_url: Base canonical URL
            anchor_id: HTML anchor ID
            page_num: PDF page number
            
        Returns:
            Full URL with fragment
        """
        if anchor_id:
            # HTML anchor
            return f"{canonical_url}#{anchor_id}"
        elif page_num is not None:
            # PDF page (common convention)
            return f"{canonical_url}#page={page_num}"
        else:
            return canonical_url
    
    @staticmethod
    def count_words(text: str) -> int:
        """
        Count words in text (cheap operation)
        
        Args:
            text: Text to count words in
            
        Returns:
            Word count
        """
        if not text:
            return 0
        
        # Simple word count by splitting on whitespace
        # More sophisticated would handle punctuation better
        words = text.split()
        return len(words)
    
    @staticmethod
    def compute_original_hash(content: bytes) -> str:
        """
        Compute SHA1 hash of original content before cleaning
        
        Args:
            content: Raw content bytes
            
        Returns:
            SHA1 hash hex string
        """
        return hashlib.sha1(content).hexdigest()
    
    @staticmethod
    def should_recrawl(original_sha1: str, new_content: bytes) -> bool:
        """
        Check if content has changed enough to warrant recrawling
        
        Args:
            original_sha1: Previous content hash
            new_content: New content bytes
            
        Returns:
            True if should recrawl
        """
        new_sha1 = PipelineVersioning.compute_original_hash(new_content)
        return original_sha1 != new_sha1