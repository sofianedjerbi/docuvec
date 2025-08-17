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
    
    def process_source_streaming(self, source: Source) -> dict:
        """Process a single source and write results immediately
        
        Args:
            source: Source object to process
            
        Returns:
            dict with processing results and stats
        """
        try:
            # Fetch content
            content = self.content_fetcher.fetch(source)
            if not content:
                self.logger.warning(f"❌ No content fetched for {source.id}")
                self.logger.warning(f"   URL: {source.url}")
                return {"success": False, "chunk_count": 0, "embed_count": 0, "reason": "no_content"}
            
            # Create chunks
            chunks = self.text_chunker.create_chunks(source, content)
            if not chunks:
                self.logger.warning(f"❌ No chunks created for {source.id}")
                return {"success": False, "chunk_count": 0, "embed_count": 0, "reason": "no_chunks"}
            
            # Validate chunks immediately
            original_count = len(chunks)
            chunks = self.chunk_validator.validate_batch(chunks)
            if not chunks:
                self.logger.warning(f"❌ No valid chunks after validation for {source.id}")
                return {"success": False, "chunk_count": 0, "embed_count": 0, "reason": "validation_failed"}
            
            # Generate embeddings immediately
            self.embeddings_generator.add_embeddings(chunks)
            
            # Count chunks with embeddings
            chunks_with_embeddings = [chunk for chunk in chunks if chunk.embedding is not None]
            
            # Write files immediately
            write_result = self.data_writer.write_source_chunks(source, chunks_with_embeddings)
            
            # Free memory
            del chunks, chunks_with_embeddings, content
            
            return {
                "success": True,
                "chunk_count": write_result["chunk_count"],
                "embed_count": write_result["embed_count"],
                "files": write_result,
                "validation_dropped": original_count - write_result["chunk_count"]
            }
            
        except Exception as e:
            self.logger.error(f"❌ Failed to process source {source.id}: {e}")
            self.logger.error(f"   URL: {source.url}")
            import traceback
            self.logger.debug(f"   Stack trace: {traceback.format_exc()}")
            return {"success": False, "chunk_count": 0, "embed_count": 0, "reason": "exception", "error": str(e)}

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
                self.logger.warning(f"❌ No content fetched for {source.id}")
                self.logger.warning(f"   URL: {source.url}")
                self.logger.warning(f"   Check if URL is accessible and contains extractable content")
                return []
            
            # Log content info for debugging
            content_length = len(content)
            self.logger.debug(f"✓ Fetched {content_length:,} characters from {source.id}")
            
            # Create chunks
            chunks = self.text_chunker.create_chunks(source, content)
            if not chunks:
                self.logger.warning(f"❌ No chunks created for {source.id}")
                self.logger.warning(f"   Content length: {content_length:,} characters")
                self.logger.warning(f"   This might indicate content is too short, low-quality, or processing failed")
                return []
            
            self.logger.debug(f"✓ Created {len(chunks)} chunks from {source.id}")
            return chunks
            
        except Exception as e:
            self.logger.error(f"❌ Failed to process source {source.id}: {e}")
            self.logger.error(f"   URL: {source.url}")
            self.logger.error(f"   Error type: {type(e).__name__}")
            import traceback
            self.logger.debug(f"   Stack trace: {traceback.format_exc()}")
            return []
    
    def run_streaming(self):
        """Run the ETL pipeline with streaming writes (memory efficient)"""
        self.logger.info("="*50)
        self.logger.info("Starting Streaming ETL Pipeline")
        self.logger.info(f"Configuration: model={self.config.embed_model}, "
                        f"batch_size={self.config.embed_batch_size}")
        self.logger.info("="*50)
        
        try:
            # Load sources
            sources = self.source_loader.load_sources()
            if not sources:
                self.logger.error("No sources loaded. Exiting.")
                return
            
            # Initialize stats
            stats = {
                "total_sources": len(sources),
                "successful_sources": 0,
                "failed_sources": 0,
                "total_chunks": 0,
                "total_embeddings": 0,
                "files_written": [],
                "failed_reasons": {}
            }
            
            # Process each source with immediate writes
            for i, source in enumerate(sources, 1):
                self.logger.info(f"\n🔄 Processing source {i}/{len(sources)}: {source.id}")
                
                result = self.process_source_streaming(source)
                
                if result["success"]:
                    stats["successful_sources"] += 1
                    stats["total_chunks"] += result["chunk_count"]
                    stats["total_embeddings"] += result["embed_count"]
                    stats["files_written"].extend([f for f in result["files"].values() if f])
                    
                    self.logger.info(f"✅ {source.id}: {result['chunk_count']} chunks, {result['embed_count']} embeddings")
                    if result.get("validation_dropped", 0) > 0:
                        self.logger.info(f"   ⚠️  Dropped {result['validation_dropped']} invalid chunks")
                else:
                    stats["failed_sources"] += 1
                    reason = result.get("reason", "unknown")
                    stats["failed_reasons"][reason] = stats["failed_reasons"].get(reason, 0) + 1
                    
                    self.logger.warning(f"❌ {source.id}: {reason}")
            
            # Final summary
            self.logger.info("\n" + "="*50)
            self.logger.info("🎉 Streaming ETL Pipeline Completed!")
            self.logger.info(f"📊 Final Statistics:")
            self.logger.info(f"   ✅ Successful sources: {stats['successful_sources']}/{stats['total_sources']}")
            self.logger.info(f"   ❌ Failed sources: {stats['failed_sources']}")
            self.logger.info(f"   📝 Total chunks written: {stats['total_chunks']:,}")
            self.logger.info(f"   🔗 Total embeddings: {stats['total_embeddings']:,}")
            self.logger.info(f"   📁 Files created: {len(stats['files_written'])}")
            
            if stats["failed_reasons"]:
                self.logger.info(f"   🔍 Failure breakdown:")
                for reason, count in stats["failed_reasons"].items():
                    self.logger.info(f"      {reason}: {count}")
            
            success_rate = (stats['successful_sources'] / stats['total_sources']) * 100
            self.logger.info(f"   📈 Success rate: {success_rate:.1f}%")
            self.logger.info("="*50)
            
            return stats
            
        except Exception as e:
            self.logger.error(f"❌ Streaming ETL pipeline failed: {e}")
            import traceback
            self.logger.error(f"Stack trace: {traceback.format_exc()}")
            raise

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
                failed_sources = []
                empty_sources = []
                
                for i, source in enumerate(sources, 1):
                    self.logger.info(f"\nProcessing source {i}/{len(sources)}: {source.id}")
                    chunks = self.process_source(source)
                    if chunks:
                        all_chunks.extend(chunks)
                    else:
                        # Check if it was a failure or just empty content
                        try:
                            content = self.content_fetcher.fetch(source)
                            if content:
                                empty_sources.append(source.id)
                            else:
                                failed_sources.append(source.id)
                        except:
                            failed_sources.append(source.id)
                
                # Report processing summary
                self.logger.info(f"\n📊 Processing Summary:")
                self.logger.info(f"   ✓ Successful sources: {len(sources) - len(failed_sources) - len(empty_sources)}")
                self.logger.info(f"   ❌ Failed to fetch: {len(failed_sources)}")
                self.logger.info(f"   ⚠️  No chunks created: {len(empty_sources)}")
                
                if failed_sources:
                    self.logger.warning(f"   Failed sources: {', '.join(failed_sources[:5])}")
                    if len(failed_sources) > 5:
                        self.logger.warning(f"   ... and {len(failed_sources) - 5} more")
                
                if empty_sources:
                    self.logger.warning(f"   Empty sources: {', '.join(empty_sources[:5])}")
                    if len(empty_sources) > 5:
                        self.logger.warning(f"   ... and {len(empty_sources) - 5} more")
                
                if not all_chunks:
                    self.logger.error("❌ No chunks were created from any source. Check URLs and content accessibility.")
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