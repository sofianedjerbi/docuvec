"""Main orchestrator for the ETL pipeline"""

from typing import List

from src.core.config import Config
from src.core.logger import setup_logger
from src.models import Source, Chunk
from src.services import (
    SourceLoader,
    ContentFetcher,
    TextChunker,
    EmbeddingsGenerator,
    DataWriter
)
from src.services.pipeline_cache import PipelineCache
from src.utils.validation import ChunkValidator


class ETLOrchestrator:
    """Orchestrates the entire ETL pipeline"""
    
    def __init__(self, config: Config = None):
        """Initialize orchestrator with configuration
        
        Args:
            config: Configuration object (creates default if None)
        """
        self.config = config or Config()
        self.logger = setup_logger("ETLOrchestrator")
        
        # Initialize services
        self.source_loader = SourceLoader(self.config.sources_file)
        self.content_fetcher = ContentFetcher(
            cache_file=self.config.cache_file,
            request_delay=self.config.request_delay,
            max_retries=self.config.max_retries,
            timeout=self.config.timeout,
            enable_ocr=self.config.enable_ocr
        )
        self.text_chunker = TextChunker(
            max_tokens=self.config.max_tokens,
            overlap_tokens=self.config.overlap_tokens,
            min_tokens=self.config.min_tokens
        )
        self.embeddings_generator = EmbeddingsGenerator(
            model=self.config.embed_model,
            batch_size=self.config.embed_batch_size,
            delay=self.config.embedding_delay
        )
        self.data_writer = DataWriter(
            chunks_dir=self.config.chunks_dir,
            embeds_dir=self.config.embeds_dir,
            summary_file=self.config.summary_file
        )
        self.chunk_validator = ChunkValidator(
            min_tokens=self.config.min_tokens,
            max_tokens=self.config.max_tokens
        )
        self.pipeline_cache = PipelineCache(self.config.cache_dir)
    
    def process_source(self, source: Source) -> List[Chunk]:
        """Process a single source through the pipeline
        
        Args:
            source: Source object to process
            
        Returns:
            List of processed chunks
        """
        try:
            # Fetch content
            content = self.content_fetcher.fetch(source)
            if not content:
                self.logger.warning(f"No content fetched for {source.id}")
                return []
            
            # Create chunks
            chunks = self.text_chunker.create_chunks(source, content)
            if not chunks:
                self.logger.warning(f"No chunks created for {source.id}")
                return []
            
            return chunks
            
        except Exception as e:
            self.logger.error(f"Failed to process source {source.id}: {e}")
            return []
    
    def run(self):
        """Run the complete ETL pipeline with smart caching"""
        self.logger.info("="*50)
        self.logger.info("Starting ETL Pipeline")
        self.logger.info(f"Configuration: model={self.config.embed_model}, "
                        f"batch_size={self.config.embed_batch_size}")
        self.logger.info("="*50)
        
        try:
            # Load sources
            sources = self.source_loader.load_sources()
            if not sources:
                self.logger.error("No sources loaded. Exiting.")
                return
            
            # Check for cached results
            settings = {
                'max_tokens': self.config.max_tokens,
                'overlap_tokens': self.config.overlap_tokens,
                'min_tokens': self.config.min_tokens,
                'embed_model': self.config.embed_model,
                'embed_batch': self.config.embed_batch_size,
                'sources_file': str(self.config.sources_file),
            }
            
            cached_chunks = self.pipeline_cache.get_cached_chunks(sources, settings)
            
            if cached_chunks:
                self.logger.info("Using cached chunks - skipping content processing")
                all_chunks = cached_chunks
            else:
                # Process each source
                all_chunks = []
                for i, source in enumerate(sources, 1):
                    self.logger.info(f"\nProcessing source {i}/{len(sources)}: {source.id}")
                    chunks = self.process_source(source)
                    all_chunks.extend(chunks)
                
                if not all_chunks:
                    self.logger.error("No chunks were created from any source. Exiting.")
                    return
                
                self.logger.info(f"\nTotal chunks created: {len(all_chunks)}")
                
                # Validate chunks
                self.logger.info("\nValidating chunks...")
                all_chunks = self.chunk_validator.validate_batch(all_chunks)
                
                if not all_chunks:
                    self.logger.error("No valid chunks after validation. Exiting.")
                    return
                
                # Cache the processed chunks
                self.pipeline_cache.cache_chunks(all_chunks, sources, settings)
            
            # Generate quality report
            quality_report = self.chunk_validator.generate_quality_report(all_chunks)
            self.logger.info(f"Quality report: {quality_report}")
            
            # Check for cached embeddings
            chunk_ids = [chunk.id for chunk in all_chunks]
            cached_embeddings = self.pipeline_cache.get_cached_embeddings(chunk_ids, self.config.embed_model)
            
            # Apply cached embeddings
            chunks_needing_embeddings = []
            for chunk in all_chunks:
                if chunk.id in cached_embeddings:
                    chunk.embedding = cached_embeddings[chunk.id]
                else:
                    chunks_needing_embeddings.append(chunk)
            
            # Generate embeddings for remaining chunks
            if chunks_needing_embeddings:
                self.logger.info(f"\nGenerating embeddings for {len(chunks_needing_embeddings)} new chunks...")
                self.embeddings_generator.add_embeddings(chunks_needing_embeddings)
                
                # Cache new embeddings
                self.pipeline_cache.cache_embeddings(chunks_needing_embeddings, self.config.embed_model)
            else:
                self.logger.info("\nAll embeddings found in cache!")
            
            # Filter chunks with embeddings
            chunks_with_embeddings = [chunk for chunk in all_chunks if chunk.embedding is not None]
            
            # Write output
            self.logger.info("\nWriting output files...")
            self.data_writer.write_chunks(chunks_with_embeddings, self.config.embed_model)
            
            self.logger.info("\n" + "="*50)
            self.logger.info("ETL Pipeline completed successfully!")
            self.logger.info(f"Processed {len(chunks_with_embeddings)} chunks with embeddings")
            if cached_chunks:
                self.logger.info("Used cached chunks - significant time/token savings!")
            if cached_embeddings:
                self.logger.info(f"Used {len(cached_embeddings)} cached embeddings - token savings!")
            self.logger.info("="*50)
            
        except Exception as e:
            self.logger.error(f"ETL pipeline failed: {e}")
            raise