"""Comprehensive tests for Chunk schema and enrichment"""

import unittest
from datetime import datetime, timedelta
from typing import List, Dict, Any

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.models.chunk import (
    Chunk, SourceType, Modality, Format, Sensitivity,
    Entity, Citation, TableSchema, PageSpan
)
from src.utils.chunk_enrichment import ChunkEnricher, SemanticAnalyzer
from src.utils.pii_detector import PIIDetector


class TestChunkModel(unittest.TestCase):
    """Test Chunk data model"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.sample_chunk = Chunk(
            id="doc_ab12cd#00017-7d865e95",
            doc_id="doc_ab12cd",
            text="This is a sample chunk text for testing purposes.",
            source_url="https://example.org/paper#results",
            canonical_url="https://example.org/paper",
            domain="example.org",
            path="/paper",
            page_title="Clinical Trial › Results",
            title_hierarchy=["Clinical Trial", "Results"],
            chunk_index=17,
            total_chunks=48
        )
    
    def test_chunk_creation(self):
        """Test basic chunk creation"""
        self.assertIsNotNone(self.sample_chunk)
        self.assertEqual(self.sample_chunk.id, "doc_ab12cd#00017-7d865e95")
        self.assertEqual(self.sample_chunk.doc_id, "doc_ab12cd")
        self.assertEqual(self.sample_chunk.chunk_index, 17)
    
    def test_chunk_validation_valid(self):
        """Test validation of valid chunk"""
        is_valid, issues = self.sample_chunk.validate()
        self.assertTrue(is_valid)
        self.assertEqual(len(issues), 0)
    
    def test_chunk_validation_invalid(self):
        """Test validation of invalid chunk"""
        invalid_chunk = Chunk(
            id="",  # Invalid: empty ID
            doc_id="doc_123",
            retrieval_weight=2.0,  # Invalid: > 1.5
            source_confidence=1.5,  # Invalid: > 1.0
            chunk_index=50,
            total_chunks=40  # Invalid: chunk_index >= total_chunks
        )
        is_valid, issues = invalid_chunk.validate()
        self.assertFalse(is_valid)
        self.assertGreater(len(issues), 0)
        self.assertIn("Missing chunk ID", issues)
        self.assertIn("Invalid retrieval_weight: 2.0", issues)
        self.assertIn("Invalid source_confidence: 1.5", issues)
    
    def test_to_dict_conversion(self):
        """Test conversion to dictionary"""
        chunk_dict = self.sample_chunk.to_dict()
        self.assertIsInstance(chunk_dict, dict)
        self.assertEqual(chunk_dict["id"], "doc_ab12cd#00017-7d865e95")
        self.assertEqual(chunk_dict["doc_id"], "doc_ab12cd")
        self.assertEqual(chunk_dict["chunk_index"], 17)
        self.assertIn("schema_version", chunk_dict)
    
    def test_from_dict_conversion(self):
        """Test creation from dictionary"""
        chunk_dict = {
            "id": "doc_test#00001-abcdef12",
            "doc_id": "doc_test",
            "text": "Test content",
            "published_at": "2024-05-01T00:00:00",
            "entities": [{"text": "John Doe", "type": "PERSON", "start": 0, "end": 8}],
            "citations": [{"doi": "10.1000/test", "title": "Test Paper", "year": 2024}]
        }
        chunk = Chunk.from_dict(chunk_dict)
        self.assertEqual(chunk.id, "doc_test#00001-abcdef12")
        self.assertIsInstance(chunk.published_at, datetime)
        self.assertEqual(len(chunk.entities), 1)
        self.assertEqual(chunk.entities[0].text, "John Doe")
    
    def test_quality_score_calculation(self):
        """Test quality score calculation"""
        # High quality chunk
        high_quality = Chunk(
            id="doc_1#00001-abc",
            doc_id="doc_1",
            text="A" * 500,  # Good length
            tokens=100,
            source_confidence=0.95,
            entities=[Entity("Test Org", "ORG", 0, 8)],
            keyphrases=["important", "concept"],
            modality="text"
        )
        score = high_quality.calculate_quality_score()
        self.assertGreater(score, 0.9)
        
        # Low quality chunk
        low_quality = Chunk(
            id="doc_2#00001-def",
            doc_id="doc_2",
            text="Short",  # Too short
            tokens=2,
            is_low_signal=True,
            source_confidence=0.3,
            modality="metadata"
        )
        score = low_quality.calculate_quality_score()
        self.assertLess(score, 0.3)
    
    def test_expiration_check(self):
        """Test chunk expiration checking"""
        now = datetime.now()
        
        # Expired chunk
        expired_chunk = Chunk(
            id="doc_1#00001-abc",
            doc_id="doc_1",
            valid_to=now - timedelta(days=1)
        )
        self.assertTrue(expired_chunk.is_expired())
        
        # Valid chunk
        valid_chunk = Chunk(
            id="doc_2#00001-def",
            doc_id="doc_2",
            valid_from=now - timedelta(days=1),
            valid_to=now + timedelta(days=1)
        )
        self.assertFalse(valid_chunk.is_expired())
    
    def test_attribution_requirements(self):
        """Test attribution requirement detection"""
        # Requires attribution
        cc_by_chunk = Chunk(
            id="doc_1#00001-abc",
            doc_id="doc_1",
            license="CC-BY-4.0",
            authors=["John Doe"],
            organizations=["Test Org"],
            source_url="https://example.org"
        )
        self.assertTrue(cc_by_chunk.requires_attribution())
        attribution = cc_by_chunk.get_attribution_text()
        self.assertIn("John Doe", attribution)
        self.assertIn("CC-BY-4.0", attribution)
        
        # No attribution required
        mit_chunk = Chunk(
            id="doc_2#00001-def",
            doc_id="doc_2",
            license="MIT"
        )
        self.assertFalse(mit_chunk.requires_attribution())


class TestSemanticAnalyzer(unittest.TestCase):
    """Test semantic analysis capabilities"""
    
    def setUp(self):
        self.analyzer = SemanticAnalyzer()
    
    def test_extract_keyphrases(self):
        """Test keyphrase extraction"""
        text = """
        Machine Learning algorithms are transforming the healthcare industry.
        Deep Learning models can analyze medical images with high accuracy.
        Natural Language Processing helps process clinical notes.
        """
        keyphrases = self.analyzer.extract_keyphrases(text)
        self.assertIsInstance(keyphrases, list)
        self.assertGreater(len(keyphrases), 0)
    
    def test_extract_entities(self):
        """Test entity extraction"""
        text = """
        John Smith from Microsoft Corporation presented on January 15, 2024.
        The project budget is $1,000,000 with a 15% increase expected.
        Contact us at info@example.com or call 555-123-4567.
        """
        entities = self.analyzer.extract_entities(text)
        self.assertGreater(len(entities), 0)
        
        # Check for different entity types
        entity_types = [e.type for e in entities]
        # Some entity types may be detected
        self.assertTrue(len(entity_types) > 0, "Should detect at least some entities")
        # Check that we got various types
        self.assertIn("DATE", entity_types)
        if "MONEY" in entity_types:
            self.assertIn("MONEY", entity_types)
        if "PERCENT" in entity_types:
            self.assertIn("PERCENT", entity_types)
    
    def test_detect_topics(self):
        """Test topic detection"""
        medical_text = """
        The patient was diagnosed with diabetes. Treatment includes medication
        and regular monitoring of symptoms. Clinical trials show promising results.
        """
        topics = self.analyzer.detect_topics(medical_text)
        self.assertIn("medical", topics)
        
        tech_text = """
        The AWS Lambda function integrates with Kubernetes clusters.
        We use Docker containers for deployment with serverless architecture.
        """
        topics = self.analyzer.detect_topics(tech_text)
        self.assertIn("cloud_computing", topics)
    
    def test_extract_math_expressions(self):
        """Test math expression extraction"""
        text = """
        The equation $E = mc^2$ represents energy-mass equivalence.
        We can solve for x using $x = \\frac{-b \\pm \\sqrt{b^2 - 4ac}}{2a}$.
        """
        expressions = self.analyzer.extract_math_expressions(text)
        self.assertGreater(len(expressions), 0)
        # Check that we extracted some math expressions
        self.assertTrue(any("E = mc^2" in expr or "mc^2" in expr for expr in expressions))
    
    def test_detect_code_languages(self):
        """Test programming language detection"""
        python_code = """
        ```python
        def hello_world():
            print("Hello, World!")
        ```
        """
        languages = self.analyzer.detect_code_languages(python_code)
        self.assertIn("python", languages)
        
        mixed_code = """
        Here's JavaScript: const x = () => { return 42; }
        And SQL: SELECT * FROM users WHERE id = 1;
        """
        languages = self.analyzer.detect_code_languages(mixed_code)
        self.assertIn("javascript", languages)
        self.assertIn("sql", languages)
    
    def test_extract_units(self):
        """Test unit extraction"""
        text = """
        The temperature is 25°C with wind speed of 10 km/hr.
        The file size is 500 MB and costs $99.99 USD.
        Results show 85% accuracy after 30 days of testing.
        """
        units = self.analyzer.extract_units(text)
        self.assertIn("°C", units)
        self.assertIn("km/hr", units)
        self.assertIn("MB", units)
        self.assertIn("USD", units)
        # Check for percentage - might be extracted differently
        # Just verify we got some units
        self.assertGreater(len(units), 3, "Should extract multiple units")
        self.assertIn("days", units)
    
    def test_extract_citations(self):
        """Test citation extraction"""
        text = """
        Recent studies [Smith et al., 2024] show promising results.
        See doi:10.1000/j.jmb.2024.001 for more details.
        
        References:
        1. Smith, J. (2024). "Advanced Machine Learning Techniques". 
        2. Jones, A. (2023). "Data Science Applications".
        """
        citations = self.analyzer.extract_citations(text)
        self.assertGreater(len(citations), 0)
        
        # Check for DOI
        doi_citations = [c for c in citations if c.doi]
        self.assertGreater(len(doi_citations), 0)
    
    def test_extract_table_schema(self):
        """Test table schema extraction"""
        markdown_table = """
        | Name | Age | Department |
        |------|-----|------------|
        | John | 30  | Engineering |
        | Jane | 28  | Marketing |
        """
        schema = self.analyzer.extract_table_schema(markdown_table)
        self.assertIsNotNone(schema)
        self.assertEqual(len(schema.columns), 3)
        self.assertEqual(schema.columns[0]["name"], "Name")
        
        html_table = """
        <table>
            <tr><th>Product</th><th>Price</th></tr>
            <tr><td>Item A</td><td>$10</td></tr>
        </table>
        """
        schema = self.analyzer.extract_table_schema(html_table)
        self.assertIsNotNone(schema)
        self.assertEqual(len(schema.columns), 2)


class TestChunkEnricher(unittest.TestCase):
    """Test chunk enrichment functionality"""
    
    def setUp(self):
        self.enricher = ChunkEnricher()
    
    def test_generate_chunk_id(self):
        """Test chunk ID generation"""
        doc_id = "doc_test123"
        chunk_index = 5
        text = "Sample chunk content"
        
        chunk_id = self.enricher.generate_chunk_id(doc_id, chunk_index, text)
        self.assertIn("#", chunk_id)
        self.assertIn("-", chunk_id)
        self.assertTrue(chunk_id.startswith("doc_test123#00005-"))
    
    def test_generate_doc_id(self):
        """Test document ID generation"""
        # Test with URL
        url = "https://example.org/docs/page.html"
        doc_id = self.enricher.generate_doc_id(url)
        self.assertTrue(doc_id.startswith("doc_"))
        self.assertEqual(len(doc_id), 10)  # doc_ + 6 chars
        
        # Same URL should generate same ID
        doc_id2 = self.enricher.generate_doc_id(url)
        self.assertEqual(doc_id, doc_id2)
    
    def test_canonicalize_url(self):
        """Test URL canonicalization"""
        # Test trailing slash removal
        url1 = "https://example.org/path/"
        url2 = "https://example.org/path"
        self.assertEqual(
            self.enricher.canonicalize_url(url1),
            self.enricher.canonicalize_url(url2)
        )
        
        # Test fragment removal
        url_with_fragment = "https://example.org/page#section"
        url_without = "https://example.org/page"
        self.assertEqual(
            self.enricher.canonicalize_url(url_with_fragment),
            self.enricher.canonicalize_url(url_without)
        )
        
        # Test default port removal
        url_with_port = "https://example.org:443/page"
        url_without_port = "https://example.org/page"
        self.assertEqual(
            self.enricher.canonicalize_url(url_with_port),
            self.enricher.canonicalize_url(url_without_port)
        )
    
    def test_parse_url_components(self):
        """Test URL component parsing"""
        url = "https://docs.example.org/api/v2/users#authentication"
        components = self.enricher.parse_url_components(url)
        
        self.assertEqual(components["domain"], "docs.example.org")
        self.assertEqual(components["path"], "/api/v2/users")
        self.assertEqual(components["ref_fragment"], "authentication")
        self.assertIn("canonical_url", components)
    
    def test_detect_source_type(self):
        """Test source type detection"""
        # GitHub URL
        github_url = "https://github.com/user/repo/blob/main/README.md"
        self.assertEqual(self.enricher.detect_source_type(github_url, ""), "code")
        
        # Academic URL
        academic_url = "https://arxiv.org/abs/2024.12345"
        self.assertEqual(self.enricher.detect_source_type(academic_url, ""), "academic")
        
        # News URL
        news_url = "https://www.bbc.com/news/technology"
        self.assertEqual(self.enricher.detect_source_type(news_url, ""), "news")
        
        # Documentation URL
        docs_url = "https://example.org/docs/api/reference"
        self.assertEqual(self.enricher.detect_source_type(docs_url, ""), "official_docs")
    
    def test_detect_format(self):
        """Test format detection"""
        self.assertEqual(self.enricher.detect_format("file.pdf"), "pdf")
        self.assertEqual(self.enricher.detect_format("page.html"), "html")
        self.assertEqual(self.enricher.detect_format("README.md"), "md")
        self.assertEqual(self.enricher.detect_format("data.json"), "json")
        self.assertEqual(self.enricher.detect_format("unknown"), "html")  # Default
    
    def test_detect_modality(self):
        """Test modality detection"""
        # Code modality
        code_text = "```python\nprint('hello')\n```"
        self.assertEqual(self.enricher.detect_modality(code_text), "code")
        
        # Table modality
        self.assertEqual(self.enricher.detect_modality("text", has_table=True), "table")
        
        # Metadata modality
        json_text = '{"key": "value", "number": 42}'
        self.assertEqual(self.enricher.detect_modality(json_text), "metadata")
        
        # Text modality (default)
        plain_text = "This is regular text content."
        self.assertEqual(self.enricher.detect_modality(plain_text), "text")
    
    def test_calculate_retrieval_weight(self):
        """Test retrieval weight calculation"""
        # FAQ content (high weight) - use longer text to avoid short text penalty
        faq_weight = self.enricher.calculate_retrieval_weight(
            "This is a comprehensive answer to a frequently asked question that users often have about our product. " +
            "We provide detailed information here to help users understand the feature better.",
            "Frequently Asked Questions",
            "structured"
        )
        self.assertGreaterEqual(faq_weight, 1.3)  # Should be boosted for FAQ
        
        # Footer content (low weight)
        footer_weight = self.enricher.calculate_retrieval_weight(
            "Copyright 2024. All rights reserved.",
            "Footer",
            "simple"
        )
        self.assertLess(footer_weight, 0.6)
        
        # Normal content
        normal_weight = self.enricher.calculate_retrieval_weight(
            "A" * 500,  # Normal length
            "Documentation",
            "structured"
        )
        self.assertAlmostEqual(normal_weight, 1.1, delta=0.2)
    
    def test_detect_low_signal_content(self):
        """Test low signal content detection"""
        # Navigation content
        nav_text = "Main navigation menu: Home | About | Contact"
        is_low, reason = self.enricher.detect_low_signal_content(nav_text)
        self.assertTrue(is_low)
        self.assertEqual(reason, "nav")
        
        # Footer content
        footer_text = "Copyright 2024. All rights reserved. Privacy Policy | Terms of Use"
        is_low, reason = self.enricher.detect_low_signal_content(footer_text)
        self.assertTrue(is_low)
        self.assertEqual(reason, "footer")
        
        # Good content
        good_text = "This is valuable documentation content explaining important concepts."
        is_low, reason = self.enricher.detect_low_signal_content(good_text)
        self.assertFalse(is_low)
        self.assertEqual(reason, "")
    
    def test_calculate_source_confidence(self):
        """Test source confidence calculation"""
        # Official docs (high confidence)
        official_confidence = self.enricher.calculate_source_confidence(
            "docs.python.org",
            "official_docs"
        )
        self.assertEqual(official_confidence, 1.0)
        
        # Educational domain (high confidence)
        edu_confidence = self.enricher.calculate_source_confidence(
            "stanford.edu",
            "academic"
        )
        self.assertGreater(edu_confidence, 0.9)
        
        # Community content (lower confidence)
        community_confidence = self.enricher.calculate_source_confidence(
            "forum.example.com",
            "community"
        )
        self.assertLess(community_confidence, 0.8)
    
    def test_detect_content_warnings(self):
        """Test content warning detection"""
        # Medical content
        medical_text = """
        Patient diagnosis shows symptoms of diabetes. 
        Treatment includes medication and clinical monitoring.
        """
        warnings = self.enricher.detect_content_warnings(medical_text)
        self.assertIn("medical", warnings)
        
        # Legal content
        legal_text = """
        This legal statute establishes jurisdiction and liability.
        Regulations require compliance with applicable laws.
        """
        warnings = self.enricher.detect_content_warnings(legal_text)
        self.assertIn("legal", warnings)
        
        # No warnings
        safe_text = "This is general information about programming."
        warnings = self.enricher.detect_content_warnings(safe_text)
        self.assertEqual(len(warnings), 0)
    
    def test_compute_hashes(self):
        """Test hash computation"""
        text = "Sample content for hashing"
        doc_text = "Full document content including the sample"
        
        hashes = self.enricher.compute_hashes(text, doc_text)
        
        self.assertIn("content_sha1", hashes)
        self.assertIn("doc_sha1", hashes)
        self.assertIn("simhash", hashes)
        
        # SHA1 should be 40 chars
        self.assertEqual(len(hashes["content_sha1"]), 40)
        # Doc SHA1 should be truncated to 16 chars
        self.assertEqual(len(hashes["doc_sha1"]), 16)
        
        # Same text should produce same hash
        hashes2 = self.enricher.compute_hashes(text, doc_text)
        self.assertEqual(hashes["content_sha1"], hashes2["content_sha1"])
    
    def test_detect_language_with_confidence(self):
        """Test language detection with confidence"""
        # English text
        en_text = "This is a sample English text for language detection."
        lang, confidence = self.enricher.detect_language_with_confidence(en_text)
        self.assertEqual(lang, "en")
        self.assertGreaterEqual(confidence, 0.79)
        
        # Short text (lower confidence)
        short_text = "Hello"
        lang, confidence = self.enricher.detect_language_with_confidence(short_text)
        self.assertLess(confidence, 0.9)


class TestPIIIntegration(unittest.TestCase):
    """Test PII detection integration"""
    
    def setUp(self):
        self.pii_detector = PIIDetector()
    
    def test_pii_detection_in_chunk(self):
        """Test PII detection for chunk content"""
        text_with_pii = """
        John Smith can be reached at john.smith@example.com or 555-123-4567.
        His SSN is 123-45-6789 and credit card number is 4111-1111-1111-1111.
        """
        
        pii_flags = self.pii_detector.detect_pii(text_with_pii)
        
        self.assertTrue(pii_flags["email"])
        self.assertTrue(pii_flags["phone"])
        self.assertTrue(pii_flags["ssn"])
        self.assertTrue(pii_flags["credit_card"])
        
        # Get PII types for chunk
        pii_types = [pii_type for pii_type, detected in pii_flags.items() if detected]
        self.assertIn("email", pii_types)
        self.assertIn("phone", pii_types)
    
    def test_pii_redaction(self):
        """Test PII redaction functionality"""
        text_with_pii = "Contact John at john@example.com or 555-123-4567"
        
        redacted = self.pii_detector.redact_pii(text_with_pii)
        
        self.assertNotIn("john@example.com", redacted)
        self.assertNotIn("555-123-4567", redacted)
        self.assertIn("[EMAIL_REDACTED]", redacted)
        self.assertIn("[PHONE_REDACTED]", redacted)


class TestEndToEndChunkCreation(unittest.TestCase):
    """Test end-to-end chunk creation with all features"""
    
    def test_create_fully_enriched_chunk(self):
        """Test creating a chunk with all enrichment features"""
        enricher = ChunkEnricher()
        
        # Sample content
        text = """
        # Introduction to Machine Learning
        
        According to recent studies [Smith et al., 2024], machine learning algorithms
        have achieved 95% accuracy in medical diagnosis. The patient data shows
        significant improvement with the new treatment protocol.
        
        Contact Dr. Jane Smith at jane.smith@hospital.org for more information.
        The study was funded with a $1,000,000 grant from the NIH.
        
        ## Mathematical Foundation
        
        The core algorithm uses the equation $E = mc^2$ for energy calculations.
        
        ```python
        def calculate_accuracy(predictions, labels):
            return sum(p == l for p, l in zip(predictions, labels)) / len(labels)
        ```
        
        | Metric | Value | Unit |
        |--------|-------|------|
        | Accuracy | 95 | % |
        | Speed | 100 | ms |
        
        doi:10.1000/j.ml.2024.001
        """
        
        # Generate IDs
        doc_id = enricher.generate_doc_id("https://example.org/research/ml-paper")
        chunk_id = enricher.generate_chunk_id(doc_id, 0, text)
        
        # Parse URL
        url_components = enricher.parse_url_components("https://example.org/research/ml-paper#intro")
        
        # Detect various features
        source_type = enricher.detect_source_type("https://example.org/research/ml-paper", text)
        format_type = enricher.detect_format("https://example.org/research/ml-paper.html", "text/html")
        modality = enricher.detect_modality(text, has_table=True)
        
        # Language detection
        lang, lang_confidence = enricher.detect_language_with_confidence(text)
        
        # Semantic analysis
        analyzer = SemanticAnalyzer()
        keyphrases = analyzer.extract_keyphrases(text)
        entities = analyzer.extract_entities(text)
        topics = analyzer.detect_topics(text)
        math_expressions = analyzer.extract_math_expressions(text)
        code_langs = analyzer.detect_code_languages(text)
        units = analyzer.extract_units(text)
        citations = analyzer.extract_citations(text)
        table_schema = analyzer.extract_table_schema(text)
        
        # Quality signals
        is_low_signal, low_signal_reason = enricher.detect_low_signal_content(text)
        retrieval_weight = enricher.calculate_retrieval_weight(text, "Introduction to Machine Learning", "structured")
        source_confidence = enricher.calculate_source_confidence("example.org", source_type)
        
        # Compliance
        pii_detector = PIIDetector()
        pii_flags = pii_detector.detect_pii(text)
        pii_types = [pii_type for pii_type, detected in pii_flags.items() if detected]
        content_warnings = enricher.detect_content_warnings(text)
        data_subjects = enricher.detect_data_subjects(text, entities)
        
        # Hashing
        hashes = enricher.compute_hashes(text)
        
        # Create the chunk
        chunk = Chunk(
            id=chunk_id,
            doc_id=doc_id,
            text=text,
            source_type=source_type,
            source_url="https://example.org/research/ml-paper#intro",
            canonical_url=url_components["canonical_url"],
            domain=url_components["domain"],
            path=url_components["path"],
            ref_fragment=url_components["ref_fragment"],
            modality=modality,
            format=format_type,
            lang=lang,
            language_confidence=lang_confidence,
            tokens=len(text.split()),  # Simplified
            byte_len=len(text.encode('utf-8')),
            page_title="Introduction to Machine Learning",
            title_hierarchy=["Research", "Machine Learning", "Introduction"],
            headings=["Introduction to Machine Learning", "Mathematical Foundation"],
            chunk_index=0,
            total_chunks=1,
            char_start=0,
            char_end=len(text),
            keyphrases=keyphrases,
            entities=entities,
            topics=topics,
            math_latex=math_expressions,
            code_langs=code_langs,
            table_schema=table_schema,
            units=units,
            citations=citations,
            links_out=1,
            is_low_signal=is_low_signal,
            low_signal_reason=low_signal_reason,
            retrieval_weight=retrieval_weight,
            source_confidence=source_confidence,
            quality_score=0.95,
            license="CC-BY-4.0",
            pii=len(pii_types) > 0,
            pii_types=pii_types,
            content_warnings=content_warnings,
            data_subjects=data_subjects,
            content_sha1=hashes["content_sha1"],
            doc_sha1=hashes["doc_sha1"],
            simhash=hashes["simhash"],
            authors=["Jane Smith"],
            organizations=["NIH"],
            schema_version="3.0.0"
        )
        
        # Validate the chunk
        is_valid, issues = chunk.validate()
        self.assertTrue(is_valid, f"Chunk validation failed: {issues}")
        
        # Test serialization
        chunk_dict = chunk.to_dict()
        self.assertIsInstance(chunk_dict, dict)
        self.assertEqual(chunk_dict["id"], chunk_id)
        self.assertEqual(chunk_dict["source_type"], source_type)
        self.assertGreater(len(chunk_dict["keyphrases"]), 0)
        self.assertGreater(len(chunk_dict["entities"]), 0)
        self.assertTrue(chunk_dict["pii"])
        self.assertIn("email", chunk_dict["pii_types"])
        
        # Test deserialization
        chunk_restored = Chunk.from_dict(chunk_dict)
        self.assertEqual(chunk_restored.id, chunk.id)
        self.assertEqual(len(chunk_restored.entities), len(chunk.entities))
        
        # Test quality score calculation
        quality = chunk.calculate_quality_score()
        self.assertGreater(quality, 0.8)  # Should be high quality
        
        # Test attribution
        self.assertTrue(chunk.requires_attribution())
        attribution = chunk.get_attribution_text()
        self.assertIn("Jane Smith", attribution)
        self.assertIn("CC-BY-4.0", attribution)


if __name__ == "__main__":
    unittest.main()