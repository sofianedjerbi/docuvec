"""Pipeline cache service for settings-aware caching"""

import json
import hashlib
import time
from typing import Dict, Any, List, Optional
from pathlib import Path

from src.models import Source, Chunk
from src.core.logger import setup_logger


class PipelineCache:
    """Service for caching pipeline results based on settings"""
    
    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(exist_ok=True)
        self.logger = setup_logger(self.__class__.__name__)
        
        # Cache file paths
        self.settings_cache_file = self.cache_dir / "settings_cache.json"
        self.chunks_cache_file = self.cache_dir / "chunks_cache.json"
        self.embeddings_cache_file = self.cache_dir / "embeddings_cache.json"
        
        # Load existing caches
        self.settings_cache = self._load_json_cache(self.settings_cache_file)
        self.chunks_cache = self._load_json_cache(self.chunks_cache_file)
        self.embeddings_cache = self._load_json_cache(self.embeddings_cache_file)
    
    def _load_json_cache(self, file_path: Path) -> Dict[str, Any]:
        """Load JSON cache file"""
        if file_path.exists():
            try:
                with open(file_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.warning(f"Failed to load cache {file_path}: {e}")
        return {}
    
    def _save_json_cache(self, cache: Dict[str, Any], file_path: Path):
        """Save JSON cache file"""
        try:
            with open(file_path, 'w') as f:
                json.dump(cache, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save cache {file_path}: {e}")
    
    def _generate_settings_hash(self, settings: Dict[str, Any]) -> str:
        """Generate hash for pipeline settings"""
        # Include relevant settings that affect output
        relevant_settings = {
            'max_tokens': settings.get('max_tokens', 700),
            'overlap_tokens': settings.get('overlap_tokens', 80),
            'min_tokens': settings.get('min_tokens', 40),
            'embed_model': settings.get('embed_model', 'text-embedding-3-small'),
            'embed_batch': settings.get('embed_batch', 64),
            'sources_file': settings.get('sources_file', 'sources.yaml'),
        }
        
        # Create deterministic hash
        settings_str = json.dumps(relevant_settings, sort_keys=True)
        return hashlib.sha256(settings_str.encode()).hexdigest()[:16]
    
    def _generate_source_hash(self, source: Source) -> str:
        """Generate hash for source including relevant metadata"""
        source_data = {
            'id': source.id,
            'url': source.url,
            'title': source.title,
            'tags': source.tags
        }
        source_str = json.dumps(source_data, sort_keys=True)
        return hashlib.sha256(source_str.encode()).hexdigest()[:16]
    
    def get_cached_chunks(self, sources: List[Source], settings: Dict[str, Any]) -> Optional[List[Chunk]]:
        """Get cached chunks if settings and sources haven't changed"""
        settings_hash = self._generate_settings_hash(settings)
        
        # Check if we have a cached result for these settings
        if settings_hash not in self.settings_cache:
            self.logger.info("No cache found for current settings")
            return None
        
        cached_entry = self.settings_cache[settings_hash]
        
        # Check if sources have changed
        current_sources_hash = self._generate_sources_hash(sources)
        if cached_entry.get('sources_hash') != current_sources_hash:
            self.logger.info("Sources have changed, cache invalid")
            return None
        
        # Check cache age (24 hours max)
        cache_age = time.time() - cached_entry.get('timestamp', 0)
        if cache_age > 86400:  # 24 hours
            self.logger.info("Cache too old, invalidating")
            return None
        
        # Load cached chunks
        chunks_key = cached_entry.get('chunks_key')
        if chunks_key not in self.chunks_cache:
            self.logger.warning("Chunks cache missing, rebuilding")
            return None
        
        self.logger.info(f"Loading {len(self.chunks_cache[chunks_key])} cached chunks")
        return self._deserialize_chunks(self.chunks_cache[chunks_key])
    
    def _generate_sources_hash(self, sources: List[Source]) -> str:
        """Generate hash for all sources"""
        sources_data = []
        for source in sources:
            sources_data.append({
                'id': source.id,
                'url': source.url,
                'title': source.title,
                'tags': source.tags
            })
        
        sources_str = json.dumps(sources_data, sort_keys=True)
        return hashlib.sha256(sources_str.encode()).hexdigest()[:16]
    
    def cache_chunks(self, chunks: List[Chunk], sources: List[Source], settings: Dict[str, Any]):
        """Cache processed chunks"""
        if not chunks:
            return
        
        settings_hash = self._generate_settings_hash(settings)
        sources_hash = self._generate_sources_hash(sources)
        chunks_key = f"{settings_hash}_{sources_hash}"
        
        # Serialize chunks (without embeddings to save space)
        serialized_chunks = self._serialize_chunks(chunks, include_embeddings=False)
        
        # Cache chunks
        self.chunks_cache[chunks_key] = serialized_chunks
        
        # Cache settings mapping
        self.settings_cache[settings_hash] = {
            'chunks_key': chunks_key,
            'sources_hash': sources_hash,
            'timestamp': time.time(),
            'total_chunks': len(chunks),
            'settings': self._generate_settings_hash(settings)
        }
        
        # Save caches
        self._save_json_cache(self.chunks_cache, self.chunks_cache_file)
        self._save_json_cache(self.settings_cache, self.settings_cache_file)
        
        self.logger.info(f"Cached {len(chunks)} chunks for settings hash {settings_hash}")
    
    def get_cached_embeddings(self, chunk_ids: List[str], embed_model: str) -> Dict[str, List[float]]:
        """Get cached embeddings for chunk IDs"""
        embeddings_key = f"{embed_model}"
        
        if embeddings_key not in self.embeddings_cache:
            return {}
        
        cached_embeddings = self.embeddings_cache[embeddings_key]
        result = {}
        
        for chunk_id in chunk_ids:
            if chunk_id in cached_embeddings:
                result[chunk_id] = cached_embeddings[chunk_id]
        
        if result:
            self.logger.info(f"Found {len(result)} cached embeddings for {embed_model}")
        
        return result
    
    def cache_embeddings(self, chunks: List[Chunk], embed_model: str):
        """Cache embeddings for chunks"""
        if not chunks:
            return
        
        embeddings_key = f"{embed_model}"
        
        if embeddings_key not in self.embeddings_cache:
            self.embeddings_cache[embeddings_key] = {}
        
        cached_count = 0
        for chunk in chunks:
            if chunk.embedding:
                self.embeddings_cache[embeddings_key][chunk.id] = chunk.embedding
                cached_count += 1
        
        # Save embeddings cache
        self._save_json_cache(self.embeddings_cache, self.embeddings_cache_file)
        
        self.logger.info(f"Cached {cached_count} embeddings for model {embed_model}")
    
    def _serialize_chunks(self, chunks: List[Chunk], include_embeddings: bool = True) -> List[Dict[str, Any]]:
        """Serialize chunks to JSON-compatible format"""
        serialized = []
        
        for chunk in chunks:
            chunk_data = {
                'id': chunk.id,
                'text': chunk.text,
                'source_url': chunk.source_url,
                'page_title': chunk.page_title,
                'service': chunk.service,
                'domain_exam': chunk.domain_exam,
                'certification': chunk.certification,
                'provider': chunk.provider,
                'resource_type': chunk.resource_type,
                'chunk_index': chunk.chunk_index,
                'total_chunks': chunk.total_chunks,
                'is_low_signal': chunk.is_low_signal,
                'section_type': chunk.section_type
            }
            
            if include_embeddings and chunk.embedding:
                chunk_data['embedding'] = chunk.embedding
            
            serialized.append(chunk_data)
        
        return serialized
    
    def _deserialize_chunks(self, serialized_chunks: List[Dict[str, Any]]) -> List[Chunk]:
        """Deserialize chunks from JSON format"""
        chunks = []
        
        for chunk_data in serialized_chunks:
            chunk = Chunk(
                id=chunk_data['id'],
                text=chunk_data['text'],
                source_url=chunk_data['source_url'],
                page_title=chunk_data['page_title'],
                service=chunk_data['service'],
                domain_exam=chunk_data['domain_exam'],
                certification=chunk_data['certification'],
                provider=chunk_data['provider'],
                resource_type=chunk_data['resource_type'],
                chunk_index=chunk_data['chunk_index'],
                total_chunks=chunk_data['total_chunks'],
                embedding=chunk_data.get('embedding'),
                is_low_signal=chunk_data.get('is_low_signal', False),
                section_type=chunk_data.get('section_type', 'content')
            )
            chunks.append(chunk)
        
        return chunks
    
    def invalidate_cache(self, reason: str = "Manual invalidation"):
        """Invalidate all caches"""
        self.settings_cache.clear()
        self.chunks_cache.clear()
        self.embeddings_cache.clear()
        
        # Save empty caches
        self._save_json_cache(self.settings_cache, self.settings_cache_file)
        self._save_json_cache(self.chunks_cache, self.chunks_cache_file)
        self._save_json_cache(self.embeddings_cache, self.embeddings_cache_file)
        
        self.logger.info(f"Cache invalidated: {reason}")
    
    def cleanup_old_cache(self, max_age_hours: int = 168):  # 7 days
        """Remove old cache entries"""
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        
        # Clean settings cache
        keys_to_remove = []
        for key, entry in self.settings_cache.items():
            if current_time - entry.get('timestamp', 0) > max_age_seconds:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self.settings_cache[key]
        
        if keys_to_remove:
            self.logger.info(f"Cleaned up {len(keys_to_remove)} old cache entries")
            self._save_json_cache(self.settings_cache, self.settings_cache_file)