"""Utilities for enriching chunks with metadata and quality signals"""

import hashlib
import re
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from urllib.parse import urlparse, urlunparse
import json

try:
    import simhash as sh
except ImportError:
    sh = None

try:
    import langdetect
except ImportError:
    langdetect = None


class ChunkEnricher:
    """Enriches chunks with production-ready metadata"""
    
    # Patterns for detecting content features
    CODE_PATTERNS = [
        r'```[\s\S]*?```',           # Markdown code blocks
        r'<code>[\s\S]*?</code>',    # HTML code tags
        r'^\s{4,}.*$',               # Indented code (markdown)
        r'<pre>[\s\S]*?</pre>',      # Pre-formatted text
    ]
    
    TABLE_PATTERNS = [
        r'<table[\s\S]*?</table>',   # HTML tables
        r'\|.*\|.*\|',               # Markdown tables
    ]
    
    LIST_PATTERNS = [
        r'^[\s]*[-*+]\s+',           # Markdown lists
        r'^[\s]*\d+\.\s+',           # Numbered lists
        r'<[uo]l>[\s\S]*?</[uo]l>',  # HTML lists
    ]
    
    # Low signal categories
    LOW_SIGNAL_CATEGORIES = {
        'navigation': ['nav', 'menu', 'breadcrumb', 'sidebar'],
        'legal': ['terms', 'privacy', 'copyright', 'disclaimer', 'cookie'],
        'advertisement': ['ad', 'sponsor', 'promoted', 'advertisement'],
        'social': ['share', 'follow', 'subscribe', 'comment'],
        'footer': ['footer', 'copyright', 'all rights reserved'],
    }
    
    # Retrieval weight adjustments
    WEIGHT_ADJUSTMENTS = {
        'title': 1.3,        # Boost titles
        'introduction': 1.2, # Boost intro sections
        'faq': 1.2,         # Boost FAQs
        'summary': 1.1,     # Boost summaries
        'example': 1.1,     # Boost examples
        'footer': 0.5,      # Downweight footers
        'navigation': 0.3,  # Downweight nav
        'legal': 0.4,       # Downweight legal
        'reference': 0.7,   # Downweight pure references
    }
    
    @staticmethod
    def generate_doc_id(url: str) -> str:
        """Generate stable document ID from canonical URL"""
        canonical = ChunkEnricher.canonicalize_url(url)
        return hashlib.sha256(canonical.encode()).hexdigest()[:16]
    
    @staticmethod
    def canonicalize_url(url: str) -> str:
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
    
    @staticmethod
    def parse_url_components(url: str) -> Tuple[str, str, str]:
        """Extract domain and path from URL"""
        parsed = urlparse(url)
        domain = parsed.netloc
        path = parsed.path or '/'
        canonical = ChunkEnricher.canonicalize_url(url)
        return canonical, domain, path
    
    @staticmethod
    def compute_content_hash(text: str) -> str:
        """Compute SHA1 hash of content"""
        return hashlib.sha1(text.encode('utf-8')).hexdigest()
    
    @staticmethod
    def compute_simhash(text: str) -> str:
        """Compute simhash for near-duplicate detection"""
        if sh:
            try:
                return str(sh.Simhash(text).value)
            except:
                return ""
        return ""
    
    @staticmethod
    def detect_language(text: str, html_lang: Optional[str] = None) -> str:
        """Detect language with HTML lang attribute fallback"""
        # Use HTML lang attribute if available
        if html_lang:
            # Clean up lang attribute (e.g., "en-US" -> "en")
            lang = html_lang.split('-')[0].lower()
            if len(lang) == 2:  # Valid ISO 639-1 code
                return lang
        
        # Fallback to language detection
        if langdetect and text:
            try:
                return langdetect.detect(text[:500])  # Use first 500 chars
            except:
                pass
        
        return "en"  # Default to English
    
    @staticmethod
    def extract_dates_from_metadata(metadata: Dict) -> Tuple[Optional[datetime], Optional[datetime]]:
        """Extract published and modified dates from metadata"""
        published = None
        modified = None
        
        # Common date field names
        date_fields = {
            'published': ['datePublished', 'published_time', 'article:published_time', 
                         'publish_date', 'date', 'created'],
            'modified': ['dateModified', 'modified_time', 'article:modified_time',
                        'updated', 'lastmod', 'last_modified']
        }
        
        for field_type, field_names in date_fields.items():
            for field in field_names:
                if field in metadata and metadata[field]:
                    try:
                        # Parse ISO format or common date strings
                        date_str = metadata[field]
                        if isinstance(date_str, str):
                            # Try ISO format first
                            try:
                                parsed_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                            except:
                                # Try other common formats
                                from dateutil import parser
                                parsed_date = parser.parse(date_str)
                            
                            if field_type == 'published' and not published:
                                published = parsed_date
                            elif field_type == 'modified' and not modified:
                                modified = parsed_date
                    except:
                        continue
        
        return published, modified
    
    @staticmethod
    def detect_content_features(text: str) -> Dict[str, any]:
        """Detect code, tables, lists, and other features"""
        features = {
            'has_code': False,
            'has_table': False,
            'has_list': False,
            'headings': [],
            'links_out': 0,
        }
        
        # Check for code
        for pattern in ChunkEnricher.CODE_PATTERNS:
            if re.search(pattern, text, re.MULTILINE):
                features['has_code'] = True
                break
        
        # Check for tables
        for pattern in ChunkEnricher.TABLE_PATTERNS:
            if re.search(pattern, text, re.MULTILINE | re.IGNORECASE):
                features['has_table'] = True
                break
        
        # Check for lists
        for pattern in ChunkEnricher.LIST_PATTERNS:
            if re.search(pattern, text, re.MULTILINE):
                features['has_list'] = True
                break
        
        # Extract headings (Markdown style)
        heading_pattern = r'^#{1,6}\s+(.+)$'
        headings = re.findall(heading_pattern, text, re.MULTILINE)
        features['headings'] = headings[:10]  # Limit to first 10
        
        # Count outbound links
        link_patterns = [
            r'https?://[^\s<>"{}|\\^`\[\]]+',  # URLs
            r'\[([^\]]+)\]\(([^)]+)\)',        # Markdown links
            r'<a[^>]+href=["\']([^"\']+)',     # HTML links
        ]
        links = []
        for pattern in link_patterns:
            links.extend(re.findall(pattern, text))
        features['links_out'] = min(len(links), 50)  # Cap at 50
        
        return features
    
    @staticmethod
    def calculate_retrieval_weight(text: str, title: str, section_type: str) -> float:
        """Calculate retrieval weight based on content signals"""
        weight = 1.0
        text_lower = text.lower()
        title_lower = title.lower()
        
        # Check for weight adjustments
        for keyword, adjustment in ChunkEnricher.WEIGHT_ADJUSTMENTS.items():
            if keyword in title_lower or f"\n{keyword}\n" in text_lower:
                weight *= adjustment
                break  # Apply only the first matching adjustment
        
        # Additional signals
        if len(text) < 100:  # Very short chunks
            weight *= 0.7
        
        if section_type == 'structured':  # Well-structured content
            weight *= 1.1
        
        # Clamp weight to reasonable range
        return max(0.1, min(1.5, weight))
    
    @staticmethod
    def detect_low_signal_reason(text: str, is_low_signal: bool) -> str:
        """Determine why content is low signal"""
        if not is_low_signal:
            return ""
        
        text_lower = text.lower()
        
        # Check categories
        for category, keywords in ChunkEnricher.LOW_SIGNAL_CATEGORIES.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return category
        
        # Other checks
        if len(text) < 50:
            return "too_short"
        
        if text.count('\n') > len(text) / 20:  # Too many line breaks
            return "fragmented"
        
        if re.search(r'^[\s\d\W]+$', text):  # Only numbers/symbols
            return "non_text"
        
        return "generic_low_quality"
    
    @staticmethod
    def extract_robots_meta(html_content: str) -> Tuple[bool, bool]:
        """Extract noindex and nofollow from robots meta tags"""
        noindex = False
        nofollow = False
        
        # Check meta robots tag
        robots_pattern = r'<meta\s+name=["\']robots["\']\s+content=["\']([^"\']+)'
        matches = re.findall(robots_pattern, html_content, re.IGNORECASE)
        
        for content in matches:
            content_lower = content.lower()
            if 'noindex' in content_lower:
                noindex = True
            if 'nofollow' in content_lower:
                nofollow = True
        
        return noindex, nofollow
    
    @staticmethod
    def calculate_source_confidence(domain: str, text: str) -> float:
        """Calculate source confidence based on domain and content signals"""
        confidence = 1.0
        
        # Known low-quality domains (you'd expand this list)
        low_quality_domains = ['spam', 'ads', 'click', 'track']
        for lq in low_quality_domains:
            if lq in domain.lower():
                confidence *= 0.5
        
        # Check for spammy content signals
        spam_signals = ['click here', 'buy now', 'limited offer', 'act now']
        spam_count = sum(1 for signal in spam_signals if signal in text.lower())
        if spam_count > 2:
            confidence *= 0.7
        
        # User-generated content signals
        ugc_signals = ['posted by', 'commented', 'reply', 'anonymous']
        ugc_count = sum(1 for signal in ugc_signals if signal in text.lower())
        if ugc_count > 3:
            confidence *= 0.8
        
        return max(0.1, min(1.0, confidence))