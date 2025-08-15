"""Validation utilities for chunks and text quality"""

import re
import requests
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.models import Chunk, Source
from src.core.logger import setup_logger


class ChunkValidator:
    """Validate and assess chunk quality"""
    
    def __init__(self, min_tokens: int = 40, max_tokens: int = 800):
        self.min_tokens = min_tokens
        self.max_tokens = max_tokens
        self.logger = setup_logger(self.__class__.__name__)
    
    def validate_chunk(self, chunk: Chunk) -> Dict[str, Any]:
        """Validate a single chunk
        
        Args:
            chunk: Chunk to validate
            
        Returns:
            Validation results dictionary
        """
        results = {
            "is_valid": True,
            "issues": [],
            "warnings": []
        }
        
        # Check text exists
        if not chunk.text or not chunk.text.strip():
            results["is_valid"] = False
            results["issues"].append("Empty or whitespace-only text")
            return results
        
        # Check minimum length
        if len(chunk.text) < 50:
            results["is_valid"] = False
            results["issues"].append(f"Text too short: {len(chunk.text)} chars")
        
        # Check for excessive repetition
        lines = chunk.text.splitlines()
        if len(lines) > 5:
            unique_lines = set(lines)
            if len(unique_lines) < len(lines) * 0.5:
                results["warnings"].append("High line repetition detected")
        
        # Check for excessive URLs (likely references)
        url_count = len(re.findall(r"https?://", chunk.text))
        if url_count > 10:
            results["warnings"].append(f"High URL count: {url_count}")
            chunk.is_low_signal = True
            chunk.section_type = "references"
        
        # Check for table of contents patterns
        if re.search(r"(\.\s*){3,}\d+", chunk.text):
            results["warnings"].append("Table of contents pattern detected")
            chunk.section_type = "toc"
        
        # Check for code block dominance
        code_blocks = re.findall(r"\[CODE\].*?\[/CODE\]", chunk.text, re.DOTALL)
        if code_blocks:
            code_length = sum(len(block) for block in code_blocks)
            if code_length > len(chunk.text) * 0.8:
                chunk.section_type = "code"
        
        # Log validation results
        if not results["is_valid"]:
            self.logger.debug(f"Invalid chunk {chunk.id}: {results['issues']}")
        elif results["warnings"]:
            self.logger.debug(f"Chunk {chunk.id} warnings: {results['warnings']}")
        
        return results
    
    def validate_batch(self, chunks: List[Chunk]) -> List[Chunk]:
        """Validate a batch of chunks
        
        Args:
            chunks: List of chunks to validate
            
        Returns:
            List of valid chunks
        """
        valid_chunks = []
        
        for chunk in chunks:
            validation = self.validate_chunk(chunk)
            if validation["is_valid"]:
                valid_chunks.append(chunk)
        
        if len(valid_chunks) != len(chunks):
            self.logger.info(f"Filtered {len(chunks) - len(valid_chunks)} invalid chunks")
        
        # Report statistics
        low_signal_count = sum(1 for c in valid_chunks if c.is_low_signal)
        if low_signal_count > 0:
            percentage = (low_signal_count / len(valid_chunks)) * 100
            self.logger.info(f"Low-signal chunks: {low_signal_count}/{len(valid_chunks)} ({percentage:.1f}%)")
        
        # Report section types
        section_types = {}
        for chunk in valid_chunks:
            section_types[chunk.section_type] = section_types.get(chunk.section_type, 0) + 1
        
        self.logger.info(f"Section type distribution: {section_types}")
        
        return valid_chunks
    
    def generate_quality_report(self, chunks: List[Chunk]) -> Dict[str, Any]:
        """Generate quality report for chunks
        
        Args:
            chunks: List of chunks to analyze
            
        Returns:
            Quality report dictionary
        """
        report = {
            "total_chunks": len(chunks),
            "valid_chunks": 0,
            "invalid_chunks": 0,
            "low_signal_chunks": 0,
            "section_types": {},
            "avg_chunk_length": 0,
            "issues_found": [],
            "warnings_found": []
        }
        
        total_length = 0
        all_issues = set()
        all_warnings = set()
        
        for chunk in chunks:
            validation = self.validate_chunk(chunk)
            
            if validation["is_valid"]:
                report["valid_chunks"] += 1
            else:
                report["invalid_chunks"] += 1
            
            if chunk.is_low_signal:
                report["low_signal_chunks"] += 1
            
            section = chunk.section_type
            report["section_types"][section] = report["section_types"].get(section, 0) + 1
            
            total_length += len(chunk.text)
            all_issues.update(validation["issues"])
            all_warnings.update(validation["warnings"])
        
        if chunks:
            report["avg_chunk_length"] = total_length // len(chunks)
        
        report["issues_found"] = list(all_issues)
        report["warnings_found"] = list(all_warnings)
        
        return report


def verify_source(source: Source, timeout: int = 10) -> Dict[str, Any]:
    """Verify a single source is accessible
    
    Args:
        source: Source to verify
        timeout: Request timeout in seconds
        
    Returns:
        Dictionary with verification results
    """
    logger = setup_logger("SourceVerifier")
    result = {
        "source": source,
        "accessible": False,
        "status_code": None,
        "content_type": None,
        "error": None
    }
    
    try:
        # Make a HEAD request first (faster, less bandwidth)
        response = requests.head(source.url, timeout=timeout, allow_redirects=True)
        
        # For some URLs, HEAD might not work, try GET with stream
        if response.status_code == 405:  # Method not allowed
            response = requests.get(source.url, timeout=timeout, stream=True, allow_redirects=True)
            response.close()  # Close immediately, we just want the headers
        
        result["status_code"] = response.status_code
        result["content_type"] = response.headers.get("Content-Type", "")
        
        # Check if accessible
        if response.status_code == 200:
            result["accessible"] = True
            logger.debug(f"✓ {source.id}: Accessible (Status: {response.status_code})")
        else:
            result["error"] = f"HTTP {response.status_code}"
            logger.warning(f"✗ {source.id}: HTTP {response.status_code}")
            
    except requests.exceptions.Timeout:
        result["error"] = "Timeout"
        logger.warning(f"✗ {source.id}: Timeout after {timeout}s")
        
    except requests.exceptions.SSLError as e:
        result["error"] = f"SSL Error: {str(e)[:100]}"
        logger.warning(f"✗ {source.id}: SSL Error")
        
    except requests.exceptions.ConnectionError as e:
        result["error"] = f"Connection Error: {str(e)[:100]}"
        logger.warning(f"✗ {source.id}: Connection Error")
        
    except Exception as e:
        result["error"] = f"Error: {str(e)[:100]}"
        logger.error(f"✗ {source.id}: Unexpected error: {e}")
    
    return result


def verify_sources(sources: List[Source], max_workers: int = 10) -> List[Dict[str, Any]]:
    """Verify multiple sources in parallel
    
    Args:
        sources: List of sources to verify
        max_workers: Maximum number of parallel workers
        
    Returns:
        List of verification results
    """
    logger = setup_logger("SourceVerifier")
    logger.info(f"Verifying {len(sources)} sources with {max_workers} workers...")
    
    results = []
    
    # Use ThreadPoolExecutor for parallel verification
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_source = {
            executor.submit(verify_source, source): source 
            for source in sources
        }
        
        # Process completed tasks
        for future in as_completed(future_to_source):
            source = future_to_source[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to verify {source.id}: {e}")
                results.append({
                    "source": source,
                    "accessible": False,
                    "status_code": None,
                    "content_type": None,
                    "error": f"Verification failed: {str(e)[:100]}"
                })
    
    # Sort results by source ID for consistent output
    results.sort(key=lambda x: x["source"].id)
    
    # Log summary
    accessible_count = sum(1 for r in results if r["accessible"])
    logger.info(f"Verification complete: {accessible_count}/{len(results)} sources accessible")
    
    return results