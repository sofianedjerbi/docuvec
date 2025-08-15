#!/usr/bin/env python3
"""Main entry point for the RAG ETL pipeline"""

import sys
import time
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.core.config import Config
from src.core.orchestrator import ETLOrchestrator
from src.core.logger import setup_logger
from src.services.pipeline_cache import PipelineCache
from src.services.source_loader import SourceLoader
from src.utils.validation import verify_sources


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="RAG ETL Pipeline - Process certification documentation with embeddings"
    )
    parser.add_argument(
        "--sources",
        default="sources.yaml",
        help="Path to sources YAML file (default: sources.yaml)"
    )
    parser.add_argument(
        "--output",
        default="data",
        help="Output directory (default: data)"
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Embedding model (default: from .env or text-embedding-3-small)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=None,
        help="Batch size for embeddings (default: from .env or 64)"
    )
    parser.add_argument(
        "--clear-cache",
        action="store_true",
        help="Clear all caches before processing"
    )
    parser.add_argument(
        "--cache-info",
        action="store_true",
        help="Show cache information and exit"
    )
    parser.add_argument(
        "--verify-sources",
        action="store_true",
        help="Verify all sources are accessible and exit"
    )
    
    args = parser.parse_args()
    
    # Setup logger
    logger = setup_logger("Main")
    
    try:
        # Create config
        config = Config()
        
        # Override with command line args if provided
        if args.sources:
            config.sources_file = args.sources
        if args.output:
            config.output_dir = Path(args.output)
            config._create_directories()
        if args.model:
            config.embed_model = args.model
        if args.batch_size:
            config.embed_batch_size = args.batch_size
        
        # Handle cache operations
        cache = PipelineCache(config.cache_dir)
        
        if args.verify_sources:
            # Verify all sources are accessible
            logger.info("Verifying source accessibility...")
            source_loader = SourceLoader(config.sources_file)
            sources = source_loader.load_sources()
            
            print(f"\n{'='*80}")
            print(f"Verifying {len(sources)} sources from {config.sources_file}")
            print(f"{'='*80}\n")
            
            results = verify_sources(sources)
            
            # Display results
            accessible_count = sum(1 for r in results if r['accessible'])
            failed_count = len(results) - accessible_count
            
            # Group by provider and type
            by_provider = {}
            for result in results:
                provider = result['source'].tags.get('provider', 'Unknown')
                source_type = result['source'].tags.get('type', 'Unknown')
                
                if provider not in by_provider:
                    by_provider[provider] = {'cert': [], 'service': []}
                
                by_provider[provider][source_type].append(result)
            
            # Display results by provider
            for provider in sorted(by_provider.keys()):
                print(f"\n{provider} Sources:")
                print(f"{'-'*40}")
                
                for source_type in ['cert', 'service']:
                    if by_provider[provider][source_type]:
                        print(f"\n  {source_type.upper()} Resources:")
                        for result in by_provider[provider][source_type]:
                            status = "✓" if result['accessible'] else "✗"
                            color = "\033[92m" if result['accessible'] else "\033[91m"
                            reset = "\033[0m"
                            
                            print(f"    {color}{status}{reset} {result['source'].id}")
                            if not result['accessible']:
                                print(f"      Error: {result['error']}")
                                print(f"      URL: {result['source'].url}")
            
            # Summary
            print(f"\n{'='*80}")
            print(f"Summary:")
            print(f"  Total sources: {len(results)}")
            print(f"  ✓ Accessible: {accessible_count}")
            if failed_count > 0:
                print(f"  ✗ Failed: {failed_count}")
            
            success_rate = (accessible_count / len(results) * 100) if results else 0
            print(f"  Success rate: {success_rate:.1f}%")
            print(f"{'='*80}\n")
            
            # Exit with appropriate code
            if failed_count > 0:
                sys.exit(1)
            return
        
        if args.cache_info:
            # Show cache information
            settings_count = len(cache.settings_cache)
            chunks_count = len(cache.chunks_cache)
            embeddings_count = len(cache.embeddings_cache)
            
            print(f"\nCache Information:")
            print(f"  Location: {config.cache_dir}")
            print(f"  Settings entries: {settings_count}")
            print(f"  Chunks entries: {chunks_count}")
            print(f"  Embeddings entries: {embeddings_count}")
            
            if settings_count > 0:
                print(f"\nCached Settings:")
                for settings_hash, entry in cache.settings_cache.items():
                    age_hours = (time.time() - entry.get('timestamp', 0)) / 3600
                    print(f"  {settings_hash}: {entry.get('total_chunks', 0)} chunks, {age_hours:.1f}h old")
            
            return
        
        if args.clear_cache:
            logger.info("Clearing all caches...")
            cache.invalidate_cache("User requested cache clear")
            print("All caches cleared successfully")
        
        # Run pipeline
        logger.info("Initializing ETL pipeline...")
        orchestrator = ETLOrchestrator(config)
        orchestrator.run()
        
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        print(f"\nError: {e}")
        print("Make sure to set OPENAI_API_KEY in your environment or .env file")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Pipeline interrupted by user")
        print("\nPipeline interrupted")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        print(f"\nPipeline failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()