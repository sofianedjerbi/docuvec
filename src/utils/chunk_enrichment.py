"""Advanced chunk enrichment with semantic analysis and comprehensive metadata extraction"""

import hashlib
import re
from typing import List, Dict, Optional, Tuple, Any, Set
from datetime import datetime
from urllib.parse import urlparse, urlunparse
import json
import math
from collections import Counter

# import simhash as sh  # Optional dependency
import langdetect
from dateutil import parser as date_parser

from src.models.chunk import Entity, Citation, TableSchema, PageSpan
from src.utils.pii_detector import PIIDetector


class SemanticAnalyzer:
    """Advanced semantic analysis for chunk enrichment"""
    
    # Common technical terms by domain
    DOMAIN_TERMS = {
        "medical": ["patient", "diagnosis", "treatment", "symptom", "medication", "clinical", "trial", "therapy"],
        "legal": ["plaintiff", "defendant", "jurisdiction", "statute", "regulation", "compliance", "liability"],
        "financial": ["revenue", "profit", "investment", "portfolio", "asset", "liability", "equity", "dividend"],
        "technical": ["algorithm", "database", "api", "framework", "deployment", "architecture", "optimization"],
        "academic": ["hypothesis", "methodology", "analysis", "conclusion", "abstract", "citation", "peer-review"],
    }
    
    # Common units patterns
    UNIT_PATTERNS = [
        r'\b\d+\s*(?:mg|g|kg|ml|l|cm|m|km\/hr|km|mm|°C|°F|K|Hz|kHz|MHz|GHz|MB|GB|TB|ms|s|min|hr|hrs|days?|weeks?|months?|years?)\b',
        r'\b\d+\s*(?:USD|EUR|GBP|JPY|\$|€|£|¥)\b',
        r'\b\d+\s*(?:%|percent|pct)\b',
    ]
    
    # Code language detection patterns
    CODE_LANGUAGE_PATTERNS = {
        "python": [r'def\s+\w+\s*\(', r'import\s+\w+', r'from\s+\w+\s+import', r'if\s+__name__\s*=='],
        "javascript": [r'function\s+\w+\s*\(', r'const\s+\w+\s*=', r'let\s+\w+\s*=', r'=>', r'async\s+function'],
        "java": [r'public\s+class', r'private\s+void', r'public\s+static\s+void\s+main', r'@Override'],
        "sql": [r'SELECT\s+.*\s+FROM', r'INSERT\s+INTO', r'UPDATE\s+.*\s+SET', r'CREATE\s+TABLE'],
        "html": [r'<html>', r'<div\s+.*>', r'<span\s+.*>', r'<body>'],
        "css": [r'\.[\w-]+\s*\{', r'#[\w-]+\s*\{', r'@media\s+', r'color:\s*#?\w+'],
        "cpp": [r'#include\s*<', r'using\s+namespace', r'int\s+main\s*\(', r'std::'],
        "go": [r'func\s+\w+\s*\(', r'package\s+\w+', r'import\s+\(', r'defer\s+'],
        "rust": [r'fn\s+\w+\s*\(', r'impl\s+\w+', r'use\s+\w+', r'pub\s+fn'],
        "yaml": [r'^\s*-\s+\w+:', r'^\s*\w+:\s*$', r'^\s*\w+:\s+[\'"]'],
        "json": [r'^\s*\{', r'^\s*"[\w]+"\s*:', r'^\s*\['],
    }
    
    # Math/equation patterns
    MATH_PATTERNS = [
        r'\$\$?[^$]+\$\$?',  # LaTeX inline/display math
        r'\\begin\{equation\}.*?\\end\{equation\}',  # LaTeX equations
        r'\\begin\{align\}.*?\\end\{align\}',  # LaTeX align
        r'[A-Za-z]+\s*=\s*[^=]+(?:[+\-*/]\s*[^=]+)+',  # Simple equations
    ]
    
    @classmethod
    def extract_keyphrases(cls, text: str, max_phrases: int = 10) -> List[str]:
        """Extract key phrases using simple TF-IDF-like approach"""
        # Simple implementation - in production, use proper NLP library
        text_lower = text.lower()
        
        # Extract noun phrases (simplified)
        noun_phrase_pattern = r'\b(?:[A-Z][a-z]+\s+){1,3}[A-Z][a-z]+\b'
        phrases = re.findall(noun_phrase_pattern, text)
        
        # Also extract technical terms
        tech_terms = []
        words = text_lower.split()
        for i in range(len(words) - 1):
            bigram = f"{words[i]} {words[i+1]}"
            if any(term in bigram for domain_terms in cls.DOMAIN_TERMS.values() for term in domain_terms):
                tech_terms.append(bigram)
        
        # Combine and rank by frequency
        all_phrases = phrases + tech_terms
        phrase_counts = Counter(all_phrases)
        
        # Return top phrases
        return [phrase for phrase, _ in phrase_counts.most_common(max_phrases)]
    
    @classmethod
    def extract_entities(cls, text: str) -> List[Entity]:
        """Extract named entities (simplified implementation)"""
        entities = []
        
        # Pattern-based entity extraction (simplified)
        # In production, use spaCy, NLTK, or transformer models
        
        # Person names (Title Case patterns)
        person_pattern = r'\b([A-Z][a-z]+ (?:[A-Z]\. )?[A-Z][a-z]+)\b'
        for match in re.finditer(person_pattern, text):
            # Filter out common non-names
            name = match.group(1)
            if name not in ["United States", "New York", "Web Services", "Machine Learning"]:
                entities.append(Entity(
                    text=name,
                    type="PERSON",
                    start=match.start(),
                    end=match.end(),
                    confidence=0.7
                ))
        
        # Organizations (words ending in Inc., Corp., LLC, etc.)
        org_pattern = r'\b([\w\s]+(?:Inc|Corp|Corporation|LLC|Ltd|GmbH|AG|SA|Co|Company|Foundation|Institute|University)\.?)\b'
        for match in re.finditer(org_pattern, text):
            entities.append(Entity(
                text=match.group(1),
                type="ORG",
                start=match.start(),
                end=match.end(),
                confidence=0.8
            ))
        
        # Dates
        date_pattern = r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4})\b'
        for match in re.finditer(date_pattern, text, re.IGNORECASE):
            entities.append(Entity(
                text=match.group(1),
                type="DATE",
                start=match.start(),
                end=match.end(),
                confidence=0.9
            ))
        
        # Money amounts
        money_pattern = r'\b(\$[\d,]+(?:\.\d{2})?|[\d,]+\s*(?:USD|EUR|GBP))\b'
        for match in re.finditer(money_pattern, text):
            entities.append(Entity(
                text=match.group(1),
                type="MONEY",
                start=match.start(),
                end=match.end(),
                confidence=0.9
            ))
        
        # Percentages
        percent_pattern = r'\b(\d+(?:\.\d+)?%)\b'
        for match in re.finditer(percent_pattern, text):
            entities.append(Entity(
                text=match.group(1),
                type="PERCENT",
                start=match.start(),
                end=match.end(),
                confidence=0.95
            ))
        
        # Remove duplicates and overlapping entities
        entities = cls._deduplicate_entities(entities)
        
        return entities
    
    @classmethod
    def _deduplicate_entities(cls, entities: List[Entity]) -> List[Entity]:
        """Remove duplicate and overlapping entities"""
        if not entities:
            return []
        
        # Sort by start position
        entities.sort(key=lambda e: (e.start, -e.confidence))
        
        deduplicated = []
        for entity in entities:
            # Check if it overlaps with any existing entity
            overlaps = False
            for existing in deduplicated:
                if (entity.start < existing.end and entity.end > existing.start):
                    overlaps = True
                    break
            
            if not overlaps:
                deduplicated.append(entity)
        
        return deduplicated
    
    @classmethod
    def detect_topics(cls, text: str) -> List[str]:
        """Detect topics/domains based on content"""
        topics = []
        text_lower = text.lower()
        
        # Check for domain-specific terms
        for domain, terms in cls.DOMAIN_TERMS.items():
            term_count = sum(1 for term in terms if term in text_lower)
            if term_count >= 2:  # At least 2 domain terms
                topics.append(domain)
        
        # Additional topic detection based on keywords
        topic_keywords = {
            "cloud_computing": ["aws", "azure", "gcp", "kubernetes", "docker", "serverless"],
            "machine_learning": ["neural", "training", "model", "dataset", "accuracy", "prediction"],
            "security": ["vulnerability", "encryption", "authentication", "firewall", "breach"],
            "database": ["sql", "query", "index", "transaction", "normalization", "schema"],
            "web_development": ["html", "css", "javascript", "react", "api", "frontend", "backend"],
        }
        
        for topic, keywords in topic_keywords.items():
            if sum(1 for kw in keywords if kw in text_lower) >= 2:
                if topic not in topics:
                    topics.append(topic)
        
        return topics[:5]  # Limit to 5 topics
    
    @classmethod
    def extract_math_expressions(cls, text: str) -> List[str]:
        """Extract mathematical expressions and LaTeX"""
        expressions = []
        
        for pattern in cls.MATH_PATTERNS:
            matches = re.findall(pattern, text, re.DOTALL)
            expressions.extend(matches)
        
        # Clean up expressions
        expressions = [expr.strip() for expr in expressions]
        expressions = list(set(expressions))  # Remove duplicates
        
        return expressions[:10]  # Limit to 10 expressions
    
    @classmethod
    def detect_code_languages(cls, text: str) -> List[str]:
        """Detect programming languages in code blocks"""
        detected = []
        
        # Extract code blocks first
        code_blocks = []
        code_blocks.extend(re.findall(r'```[\w]*\n(.*?)```', text, re.DOTALL))
        code_blocks.extend(re.findall(r'<code>(.*?)</code>', text, re.DOTALL))
        code_blocks.extend(re.findall(r'<pre>(.*?)</pre>', text, re.DOTALL))
        
        # If no explicit code blocks, check the whole text
        if not code_blocks:
            code_blocks = [text]
        
        for block in code_blocks:
            for lang, patterns in cls.CODE_LANGUAGE_PATTERNS.items():
                for pattern in patterns:
                    if re.search(pattern, block, re.MULTILINE | re.IGNORECASE):
                        if lang not in detected:
                            detected.append(lang)
                        break
        
        return detected
    
    @classmethod
    def extract_units(cls, text: str) -> List[str]:
        """Extract measurement units from text"""
        units = []
        
        for pattern in cls.UNIT_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                # Extract just the unit part
                unit = re.sub(r'^[\d\s.,]+', '', match).strip()
                if unit and unit not in units:
                    units.append(unit)
        
        return units[:20]  # Limit to 20 unique units
    
    @classmethod
    def extract_citations(cls, text: str) -> List[Citation]:
        """Extract citations and references"""
        citations = []
        
        # DOI pattern
        doi_pattern = r'(?:doi:|https?://doi\.org/)([0-9.]+/[-._;()/:\w]+)'
        for match in re.finditer(doi_pattern, text, re.IGNORECASE):
            citations.append(Citation(doi=match.group(1)))
        
        # Academic citation pattern [Author, Year]
        citation_pattern = r'\[([A-Z][a-z]+(?:\s+et\s+al\.)?),?\s+(\d{4})\]'
        for match in re.finditer(citation_pattern, text):
            citations.append(Citation(
                citation_text=match.group(0),
                authors=[match.group(1)],
                year=int(match.group(2))
            ))
        
        # Reference section parsing (simplified)
        if "References" in text or "Bibliography" in text:
            ref_section = text[text.find("References"):] if "References" in text else text[text.find("Bibliography"):]
            ref_lines = ref_section.split('\n')[:20]  # First 20 references
            
            for line in ref_lines:
                if len(line) > 20 and not line.startswith("References") and not line.startswith("Bibliography"):
                    # Try to extract year
                    year_match = re.search(r'\((\d{4})\)', line)
                    year = int(year_match.group(1)) if year_match else None
                    
                    # Extract title (text in quotes)
                    title_match = re.search(r'"([^"]+)"', line)
                    title = title_match.group(1) if title_match else None
                    
                    if year or title:
                        citations.append(Citation(
                            title=title,
                            year=year,
                            citation_text=line[:200]  # Limit length
                        ))
        
        return citations[:30]  # Limit to 30 citations
    
    @classmethod
    def extract_table_schema(cls, text: str) -> Optional[TableSchema]:
        """Extract table structure if present"""
        # Check for markdown table
        if '|' in text and text.count('|') > 4:
            lines = text.split('\n')
            table_lines = [l for l in lines if '|' in l]
            
            if len(table_lines) >= 2:
                # Extract header
                header_line = table_lines[0]
                headers = [h.strip() for h in header_line.split('|') if h.strip()]
                
                if headers:
                    columns = [{"name": h, "type": "string"} for h in headers]
                    return TableSchema(
                        columns=columns,
                        rows=len(table_lines) - 2,  # Exclude header and separator
                        has_header=True
                    )
        
        # Check for HTML table
        if '<table' in text.lower():
            # Count rows
            row_count = text.lower().count('<tr')
            
            # Extract headers
            header_pattern = r'<th[^>]*>(.*?)</th>'
            headers = re.findall(header_pattern, text, re.IGNORECASE | re.DOTALL)
            
            if headers:
                columns = [{"name": h.strip(), "type": "string"} for h in headers]
                return TableSchema(
                    columns=columns,
                    rows=max(0, row_count - 1),  # Exclude header row
                    has_header=True
                )
        
        return None


class ChunkEnricher:
    """Chunk enricher with comprehensive metadata extraction"""
    
    def __init__(self):
        self.semantic_analyzer = SemanticAnalyzer()
        self.pii_detector = PIIDetector()
    
    def generate_chunk_id(self, doc_id: str, chunk_index: int, text: str) -> str:
        """Generate unique chunk ID following the schema spec"""
        content_hash = hashlib.sha1(text.encode('utf-8')).hexdigest()[:8]
        return f"{doc_id}#{chunk_index:05d}-{content_hash}"
    
    def generate_doc_id(self, source: Any) -> str:
        """Generate stable document ID from source"""
        if hasattr(source, 'url'):
            canonical_url = self.canonicalize_url(source.url)
        elif isinstance(source, str):
            canonical_url = self.canonicalize_url(source)
        else:
            # For files, use content hash
            canonical_url = str(source)
        
        return "doc_" + hashlib.sha256(canonical_url.encode()).hexdigest()[:6]
    
    def canonicalize_url(self, url: str) -> str:
        """Normalize URL to canonical form"""
        parsed = urlparse(url.lower())
        
        # Remove fragment
        parsed = parsed._replace(fragment='')
        
        # Remove trailing slash from path
        path = parsed.path.rstrip('/')
        if not path:
            path = '/'
        parsed = parsed._replace(path=path)
        
        # Sort query parameters
        if parsed.query:
            params = sorted(parsed.query.split('&'))
            parsed = parsed._replace(query='&'.join(params))
        
        # Remove default ports
        netloc = parsed.netloc
        if ':80' in netloc and parsed.scheme == 'http':
            netloc = netloc.replace(':80', '')
        elif ':443' in netloc and parsed.scheme == 'https':
            netloc = netloc.replace(':443', '')
        parsed = parsed._replace(netloc=netloc)
        
        return urlunparse(parsed)
    
    def normalize_domain(self, domain: str) -> str:
        """Normalize domain by removing www prefix"""
        if domain.startswith("www."):
            return domain[4:]
        return domain
    
    def parse_url_components(self, url: str) -> Tuple[str, str, str]:
        """Parse URL into components and return tuple"""
        parsed = urlparse(url)
        canonical = self.canonicalize_url(url)
        normalized_domain = self.normalize_domain(parsed.netloc)
        
        return canonical, normalized_domain, parsed.path or "/"
    
    def detect_source_type(self, url: str, content: str) -> str:
        """Detect source type based on URL and content"""
        url_lower = url.lower()
        content_lower = content.lower()[:1000]  # Check first 1000 chars
        
        # URL-based detection
        if "github.com" in url_lower or "gitlab.com" in url_lower:
            return "code"
        elif any(domain in url_lower for domain in [".edu", "arxiv.org", "scholar.google", "pubmed"]):
            return "academic"
        elif any(domain in url_lower for domain in ["news", "bbc.com", "cnn.com", "reuters.com"]):
            return "news"
        elif "stackoverflow.com" in url_lower or "reddit.com" in url_lower:
            return "community"
        elif any(pattern in url_lower for pattern in ["legal", "law", "regulation", "compliance"]):
            return "legal"
        elif any(pattern in url_lower for pattern in ["/docs/", "/documentation/", "/api/"]):
            return "official_docs"
        
        # Content-based detection
        if "copyright" in content_lower and "terms" in content_lower:
            return "legal"
        elif "abstract" in content_lower and "methodology" in content_lower:
            return "academic"
        elif any(log_pattern in content_lower for log_pattern in ["error", "warning", "debug", "info"]):
            if content.count('\n') > 20:  # Many lines suggest log file
                return "log"
        
        return "official_docs"  # Default
    
    def detect_format(self, url: str, content_type: Optional[str] = None) -> str:
        """Detect content format"""
        url_lower = url.lower()
        
        # Extension-based detection
        extensions = {
            ".pdf": "pdf",
            ".html": "html",
            ".htm": "html",
            ".md": "md",
            ".markdown": "md",
            ".docx": "docx",
            ".txt": "txt",
            ".tex": "latex",
            ".json": "json",
            ".csv": "csv",
            ".parquet": "parquet",
            ".rst": "rst"
        }
        
        for ext, format_type in extensions.items():
            if url_lower.endswith(ext):
                return format_type
        
        # Content-type based detection
        if content_type:
            if "pdf" in content_type:
                return "pdf"
            elif "html" in content_type:
                return "html"
            elif "json" in content_type:
                return "json"
            elif "text/plain" in content_type:
                return "txt"
        
        return "html"  # Default
    
    def detect_modality(self, text: str, has_table: bool = False, has_code: bool = False) -> str:
        """Detect content modality"""
        if has_table:
            return "table"
        elif has_code or len(re.findall(r'```.*?```', text, re.DOTALL)) > 0:
            return "code"
        elif len(self.semantic_analyzer.extract_math_expressions(text)) > 2:
            return "equation"
        elif text.startswith('{') or text.startswith('['):
            try:
                json.loads(text)
                return "metadata"
            except:
                pass
        
        return "text"  # Default
    
    def calculate_retrieval_weight(self, text: str, title: str, section_type: str) -> float:
        """Calculate retrieval weight based on content signals"""
        weight = 1.0
        text_lower = text.lower()
        title_lower = title.lower() if title else ""
        
        # Title/header boost
        if any(keyword in title_lower for keyword in ["overview", "introduction", "summary"]):
            weight *= 1.2
        elif any(keyword in title_lower for keyword in ["faq", "frequently asked", "q&a", "questions"]):
            weight *= 1.3
        elif any(keyword in title_lower for keyword in ["example", "tutorial", "how to"]):
            weight *= 1.15
        
        # Content type adjustments
        if "abstract" in text_lower[:200]:
            weight *= 1.1
        elif any(footer in text_lower for footer in ["copyright", "all rights reserved", "terms of service"]):
            weight *= 0.5
        elif text_lower.startswith("table of contents") or text_lower.startswith("index"):
            weight *= 0.4
        
        # Length adjustments
        if len(text) < 100:
            weight *= 0.7
        elif len(text) > 2000:
            weight *= 1.05
        
        # Structure bonus
        if section_type == "structured":
            weight *= 1.1
        
        return max(0.0, min(1.5, weight))
    
    def detect_low_signal_content(self, text: str) -> Tuple[bool, str]:
        """Detect if content is low signal and why"""
        text_lower = text.lower()
        
        # Navigation elements
        nav_patterns = ["navigation", "menu", "breadcrumb", "skip to content"]
        if any(pattern in text_lower for pattern in nav_patterns):
            return True, "nav"
        
        # Footer content
        footer_patterns = ["copyright", "all rights reserved", "privacy policy", "terms of use"]
        if sum(1 for p in footer_patterns if p in text_lower) >= 2:
            return True, "footer"
        
        # Legal boilerplate
        legal_patterns = ["disclaimer", "limitation of liability", "indemnification", "governing law"]
        if sum(1 for p in legal_patterns if p in text_lower) >= 2:
            return True, "legal"
        
        # Table of contents
        if text_lower.startswith("table of contents") or text_lower.startswith("contents"):
            return True, "toc"
        
        # Ads/promotional
        ad_patterns = ["sponsored", "advertisement", "promoted content", "affiliate"]
        if any(pattern in text_lower for pattern in ad_patterns):
            return True, "ads"
        
        # Too short
        if len(text) < 50:
            return True, "too_short"
        
        # Mostly non-text (numbers, symbols)
        if re.match(r'^[\s\d\W]+$', text):
            return True, "non_text"
        
        return False, ""
    
    def calculate_source_confidence(self, domain: str, source_type: str) -> float:
        """Calculate source confidence score"""
        confidence = 1.0
        
        # Source type adjustments
        source_type_confidence = {
            "official_docs": 1.0,
            "academic": 0.95,
            "legal": 0.95,
            "code": 0.9,
            "dataset": 0.9,
            "news": 0.8,
            "community": 0.7,
            "internal": 1.0,
            "log": 0.6
        }
        confidence *= source_type_confidence.get(source_type, 0.8)
        
        # Domain reputation (simplified - in production use a reputation database)
        trusted_domains = [".gov", ".edu", ".org", "wikipedia.org", "documentation"]
        untrusted_patterns = ["blogspot", "wordpress.com", "medium.com", "forum"]
        
        if any(trusted in domain for trusted in trusted_domains):
            confidence *= 1.1
        elif any(untrusted in domain for untrusted in untrusted_patterns):
            confidence *= 0.8
        
        return max(0.0, min(1.0, confidence))
    
    def detect_content_warnings(self, text: str) -> List[str]:
        """Detect content that needs warnings"""
        warnings = []
        text_lower = text.lower()
        
        # Medical content
        medical_terms = ["diagnosis", "treatment", "medication", "symptom", "patient", "clinical"]
        if sum(1 for term in medical_terms if term in text_lower) >= 3:
            warnings.append("medical")
        
        # Legal content  
        legal_terms = ["legal", "lawsuit", "liability", "jurisdiction", "statute", "regulation"]
        if sum(1 for term in legal_terms if term in text_lower) >= 3:
            warnings.append("legal")
        
        # Financial advice
        financial_terms = ["investment", "portfolio", "trading", "financial advice", "risk"]
        if sum(1 for term in financial_terms if term in text_lower) >= 3:
            warnings.append("financial")
        
        return warnings
    
    def detect_data_subjects(self, text: str, entities: List[Entity]) -> List[str]:
        """Detect data subjects mentioned in content"""
        subjects = []
        text_lower = text.lower()
        
        # Check for common data subject mentions
        if "patient" in text_lower or "medical record" in text_lower:
            subjects.append("patients")
        if "employee" in text_lower or "staff" in text_lower:
            subjects.append("employees")
        if "customer" in text_lower or "client" in text_lower:
            subjects.append("customers")
        if "student" in text_lower or "pupil" in text_lower:
            subjects.append("students")
        if "user" in text_lower and ("personal" in text_lower or "data" in text_lower):
            subjects.append("users")
        
        # Check if many person entities suggest data subjects
        person_entities = [e for e in entities if e.type == "PERSON"]
        if len(person_entities) > 5:
            subjects.append("individuals")
        
        return list(set(subjects))
    
    def compute_hashes(self, text: str, doc_text: Optional[str] = None) -> Dict[str, str]:
        """Compute various hashes for deduplication"""
        hashes = {}
        
        # Content SHA1
        hashes["content_sha1"] = hashlib.sha1(text.encode('utf-8')).hexdigest()
        
        # Document SHA1 (if full doc provided)
        if doc_text:
            hashes["doc_sha1"] = hashlib.sha1(doc_text.encode('utf-8')).hexdigest()[:16]
        else:
            hashes["doc_sha1"] = hashes["content_sha1"][:16]
        
        # Simhash for near-duplicate detection
        try:
            import simhash
            hashes["simhash"] = str(simhash.Simhash(text).value)
        except:
            # Fallback simple hash if simhash not available
            hashes["simhash"] = str(hash(text) & 0xFFFFFFFFFFFFFFFF)
        
        return hashes
    
    def compute_content_hash(self, text: str) -> str:
        """Compute SHA1 hash of content (backward compatibility)"""
        return hashlib.sha1(text.encode('utf-8')).hexdigest()
    
    def compute_simhash(self, text: str) -> str:
        """Compute simhash for near-duplicate detection (backward compatibility)"""
        try:
            import simhash
            return str(simhash.Simhash(text).value)
        except:
            # Fallback simple hash if simhash not available
            return str(hash(text) & 0xFFFFFFFFFFFFFFFF)
    
    def extract_page_spans(self, text: str, metadata: Dict[str, Any]) -> List[PageSpan]:
        """Extract page span information for PDFs"""
        spans = []
        
        # Check if we have page information in metadata
        if "page_numbers" in metadata and isinstance(metadata["page_numbers"], list):
            for page_info in metadata["page_numbers"]:
                if isinstance(page_info, dict):
                    spans.append(PageSpan(
                        page=page_info.get("page", 0),
                        char_start=page_info.get("start", 0),
                        char_end=page_info.get("end", len(text))
                    ))
        
        # If no page info but we know it's a PDF, assume single page
        elif metadata.get("format") == "pdf":
            spans.append(PageSpan(
                page=1,
                char_start=0,
                char_end=len(text)
            ))
        
        return spans
    
    def detect_language(self, text: str, html_lang: Optional[str] = None) -> str:
        """Detect language from text or HTML lang attribute"""
        # Use HTML lang attribute if available and valid
        if html_lang and len(html_lang) >= 2:
            return html_lang[:2].lower()
        
        try:
            # Use langdetect for text analysis
            detected = langdetect.detect(text[:1000])  # Use first 1000 chars
            return detected
        except:
            return "en"  # Default to English
    
    def detect_language_with_confidence(self, text: str) -> Tuple[str, float]:
        """Detect language and confidence score"""
        try:
            # Use langdetect
            lang = langdetect.detect(text[:1000])  # Use first 1000 chars
            
            # Get confidence (simplified - langdetect doesn't directly provide confidence)
            # In production, use langdetect.detect_langs() for probabilities
            confidence = 0.99 if len(text) > 100 else 0.79
            
            return lang, confidence
        except:
            return "en", 0.5  # Default with low confidence
    
    def extract_temporal_info(self, metadata: Dict[str, Any]) -> Dict[str, Optional[datetime]]:
        """Extract temporal information from metadata"""
        temporal = {
            "published_at": None,
            "modified_at": None,
            "valid_from": None,
            "valid_to": None
        }
        
        # Common date field mappings
        date_mappings = {
            "published_at": ["datePublished", "published_time", "publish_date", "created_at"],
            "modified_at": ["dateModified", "modified_time", "updated_at", "lastmod"],
            "valid_from": ["validFrom", "effective_date", "start_date"],
            "valid_to": ["validTo", "expiry_date", "end_date"]
        }
        
        for target_field, source_fields in date_mappings.items():
            for source_field in source_fields:
                if source_field in metadata and metadata[source_field]:
                    try:
                        if isinstance(metadata[source_field], str):
                            temporal[target_field] = date_parser.parse(metadata[source_field])
                        elif isinstance(metadata[source_field], datetime):
                            temporal[target_field] = metadata[source_field]
                        break
                    except:
                        continue
        
        return temporal
    
    def extract_robots_meta(self, html_content: str) -> Tuple[bool, bool]:
        """Extract robots meta directives from HTML"""
        noindex = False
        nofollow = False
        
        # Check meta robots tags
        robots_pattern = r'<meta\s+name=["\']robots["\'][^>]*content=["\']([^"\']*)["\'][^>]*>'
        matches = re.findall(robots_pattern, html_content, re.IGNORECASE)
        
        for content in matches:
            content_lower = content.lower()
            if 'noindex' in content_lower:
                noindex = True
            if 'nofollow' in content_lower:
                nofollow = True
        
        return noindex, nofollow
    
    def extract_dates_from_metadata(self, metadata: Dict[str, Any]) -> Tuple[Optional[datetime], Optional[datetime]]:
        """Extract published and modified dates from metadata"""
        published_at = None
        modified_at = None
        
        # Common date field mappings
        pub_fields = ["datePublished", "published_time", "publish_date", "created_at", "publication_date"]
        mod_fields = ["dateModified", "modified_time", "updated_at", "lastmod", "last_updated"]
        
        for field in pub_fields:
            if field in metadata and metadata[field]:
                try:
                    if isinstance(metadata[field], str):
                        published_at = date_parser.parse(metadata[field])
                    elif isinstance(metadata[field], datetime):
                        published_at = metadata[field]
                    break
                except:
                    continue
        
        for field in mod_fields:
            if field in metadata and metadata[field]:
                try:
                    if isinstance(metadata[field], str):
                        modified_at = date_parser.parse(metadata[field])
                    elif isinstance(metadata[field], datetime):
                        modified_at = metadata[field]
                    break
                except:
                    continue
        
        return published_at, modified_at
    
    def detect_content_features(self, text: str) -> Dict[str, Any]:
        """Detect various content features"""
        features = {
            'headings': [],
            'has_code': False,
            'has_table': False,
            'has_list': False,
            'links_out': 0
        }
        
        # Extract headings
        heading_patterns = [
            r'^#+\s+(.+)$',  # Markdown headings
            r'<h[1-6][^>]*>(.*?)</h[1-6]>',  # HTML headings
        ]
        
        for pattern in heading_patterns:
            matches = re.findall(pattern, text, re.MULTILINE | re.IGNORECASE)
            features['headings'].extend([h.strip() for h in matches])
        
        # Remove duplicates and limit
        features['headings'] = list(set(features['headings']))[:10]
        
        # Detect code blocks
        code_patterns = [
            r'```.*?```',  # Markdown code blocks
            r'<code>.*?</code>',  # HTML code
            r'<pre>.*?</pre>',  # HTML pre
        ]
        
        for pattern in code_patterns:
            if re.search(pattern, text, re.DOTALL):
                features['has_code'] = True
                break
        
        # Detect tables
        table_patterns = [
            r'\|.*\|',  # Markdown tables
            r'<table.*?</table>',  # HTML tables
        ]
        
        for pattern in table_patterns:
            if re.search(pattern, text, re.DOTALL):
                features['has_table'] = True
                break
        
        # Detect lists
        list_patterns = [
            r'^\s*[-*+]\s+',  # Markdown unordered lists
            r'^\s*\d+\.\s+',  # Markdown ordered lists
            r'<[uo]l>.*?</[uo]l>',  # HTML lists
        ]
        
        for pattern in list_patterns:
            if re.search(pattern, text, re.MULTILINE | re.DOTALL):
                features['has_list'] = True
                break
        
        # Count outbound links
        link_pattern = r'https?://[^\s<>"]+|www\.[^\s<>"]+'
        features['links_out'] = len(re.findall(link_pattern, text))
        
        return features
    
    def detect_low_signal_reason(self, text: str, is_low_signal: bool) -> str:
        """Detect reason for low signal content"""
        if not is_low_signal:
            return ""
        
        is_low, reason = self.detect_low_signal_content(text)
        return reason