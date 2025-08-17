"""Advanced HTML content extraction with tiered fallback and rich metadata"""

import re
import json
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
from urllib.parse import urljoin, urlparse

import trafilatura
from bs4 import BeautifulSoup, Comment

from src.core.logger import setup_logger


class HTMLExtractor:
    """Advanced HTML extraction with tiered fallback and metadata preservation"""
    
    # Boilerplate selectors to remove
    BOILERPLATE_SELECTORS = [
        'nav', 'aside', 'footer', 'header', 'form', 'iframe',
        'script', 'style', 'noscript', 'svg', 'canvas',
        '.nav', '.navigation', '.menu', '.sidebar', '.footer', '.header',
        '.cookie', '.cookies', '.cookie-banner', '.gdpr',
        '.comments', '.comment-section', '#comments', '#disqus_thread',
        '.related', '.related-posts', '.related-articles',
        '.social', '.social-share', '.share-buttons',
        '.ads', '.advertisement', '.ad-container', '.sponsor',
        '.popup', '.modal', '.overlay', '.newsletter',
        '.pagination', '.pager', '.page-numbers',
        '[class*="cookie"]', '[id*="cookie"]',
        '[class*="banner"]', '[id*="banner"]',
        '[aria-hidden="true"]', '[role="complementary"]'
    ]
    
    # Patterns for detecting low-value content
    LOW_VALUE_PATTERNS = [
        r'^\s*Read more\s*$',
        r'^\s*Share this\s*$',
        r'^\s*Comments?\s*$',
        r'^\s*Related (posts?|articles?)\s*$',
        r'^\s*Advertisement\s*$',
        r'^\s*Sponsored\s*$',
        r'^\s*Tags?:\s*$',
        r'^\s*Categories?:\s*$',
        r'^\s*Filed under\s*$',
        r'^\s*Posted (in|on)\s*$',
        r'^\s*Previous\s*$',
        r'^\s*Next\s*$',
        r'^\s*Page \d+\s*$',
        r'^\s*\d+ (comments?|replies)\s*$',
    ]
    
    def __init__(self):
        """Initialize HTML extractor with optional dependencies"""
        self.logger = setup_logger(self.__class__.__name__)
        
        # Lazy load optional libraries
        self._readability = None
        self._langdetect = None
        self._dateutil = None
    
    def extract(self, html: str, url: str = "") -> Tuple[Optional[str], Dict[str, Any]]:
        """
        Extract content and metadata from HTML using tiered approach
        
        Args:
            html: HTML content as string
            url: Original URL for resolving relative links
            
        Returns:
            Tuple of (extracted_text, metadata_dict)
        """
        metadata = {'url': url, 'extraction_method': None}
        
        # Try trafilatura first (best general-purpose)
        text, meta = self._extract_with_trafilatura(html, url)
        if text and len(text.strip()) > 100:
            metadata.update(meta)
            metadata['extraction_method'] = 'trafilatura'
            return text, metadata
        
        # Fallback to readability
        text, meta = self._extract_with_readability(html, url)
        if text and len(text.strip()) > 100:
            metadata.update(meta)
            metadata['extraction_method'] = 'readability'
            return text, metadata
        
        # Final fallback to BeautifulSoup with strict filtering
        text, meta = self._extract_with_beautifulsoup(html, url)
        metadata.update(meta)
        metadata['extraction_method'] = 'beautifulsoup'
        
        return text, metadata
    
    def _extract_with_trafilatura(self, html: str, url: str) -> Tuple[Optional[str], Dict[str, Any]]:
        """Extract using trafilatura with metadata"""
        try:
            # Extract with all metadata
            result = trafilatura.extract(
                html,
                url=url,
                favor_recall=True,
                include_comments=False,
                include_tables=True,
                include_formatting=False,
                deduplicate=True,
                target_language='en',
                include_links=False,
                output_format='txt',
                with_metadata=True
            )
            
            if not result:
                return None, {}
            
            # If metadata is included, parse it
            metadata = {}
            
            # Try to extract metadata separately
            doc = trafilatura.bare_extraction(
                html,
                url=url,
                favor_recall=True,
                include_comments=False,
                with_metadata=True
            )
            
            if doc and isinstance(doc, dict):
                metadata = {
                    'title': doc.get('title'),
                    'author': doc.get('author'),
                    'date_published': doc.get('date'),
                    'description': doc.get('description'),
                    'sitename': doc.get('sitename'),
                    'tags': doc.get('tags', []),
                    'language': doc.get('language'),
                }
                # Get main text
                result = doc.get('text', result)
            
            # Clean up None values
            metadata = {k: v for k, v in metadata.items() if v is not None}
            
            return result, metadata
            
        except Exception as e:
            self.logger.debug(f"Trafilatura extraction failed: {e}")
            return None, {}
    
    def _extract_with_readability(self, html: str, url: str) -> Tuple[Optional[str], Dict[str, Any]]:
        """Extract using readability-lxml"""
        try:
            if self._readability is None:
                from readability import Readability
                self._readability = Readability
            
            doc = self._readability(html, url)
            
            # Get article content
            content = doc.content()
            if not content:
                return None, {}
            
            # Parse with BeautifulSoup to extract text
            soup = BeautifulSoup(content, 'html.parser')
            text = self._extract_text_from_soup(soup)
            
            # Extract metadata
            metadata = {
                'title': doc.title(),
                'short_title': doc.short_title(),
            }
            
            return text, metadata
            
        except ImportError:
            self.logger.debug("readability-lxml not installed, skipping")
            return None, {}
        except Exception as e:
            self.logger.debug(f"Readability extraction failed: {e}")
            return None, {}
    
    def _extract_with_beautifulsoup(self, html: str, url: str) -> Tuple[Optional[str], Dict[str, Any]]:
        """Extract using BeautifulSoup with strict filtering"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract metadata first (before removing elements)
            metadata = self._extract_metadata(soup, url)
            
            # Remove boilerplate elements
            self._remove_boilerplate(soup)
            
            # Extract main content
            text = self._extract_text_from_soup(soup)
            
            return text, metadata
            
        except Exception as e:
            self.logger.error(f"BeautifulSoup extraction failed: {e}")
            return None, {}
    
    def _extract_metadata(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """Extract rich metadata from HTML"""
        metadata = {}
        
        # Basic metadata
        if soup.title:
            metadata['title'] = soup.title.string
        
        # Language detection
        html_tag = soup.find('html')
        if html_tag and html_tag.get('lang'):
            metadata['language'] = html_tag.get('lang')
        elif soup.text:
            # Use langdetect as fallback
            try:
                if self._langdetect is None:
                    import langdetect
                    self._langdetect = langdetect
                
                detected_lang = self._langdetect.detect(soup.text[:1000])
                metadata['language'] = detected_lang
            except:
                pass
        
        # Meta tags
        meta_mappings = {
            'author': ['author', 'article:author', 'twitter:creator'],
            'description': ['description', 'og:description', 'twitter:description'],
            'keywords': ['keywords'],
            'canonical_url': ['canonical', 'og:url', 'twitter:url'],
            'site_name': ['og:site_name', 'twitter:site'],
            'published_time': ['article:published_time', 'datePublished'],
            'modified_time': ['article:modified_time', 'dateModified'],
            'section': ['article:section'],
            'article_tag': ['article:tag'],
        }
        
        for field, names in meta_mappings.items():
            for name in names:
                # Try property attribute
                meta = soup.find('meta', property=name)
                if not meta:
                    # Try name attribute
                    meta = soup.find('meta', attrs={'name': name})
                
                if meta and meta.get('content'):
                    metadata[field] = meta.get('content')
                    break
        
        # Open Graph metadata
        og_metadata = {}
        for meta in soup.find_all('meta', property=re.compile(r'^og:')):
            if meta.get('content'):
                key = meta.get('property').replace('og:', 'og_')
                og_metadata[key] = meta.get('content')
        
        if og_metadata:
            metadata['open_graph'] = og_metadata
        
        # Twitter Card metadata
        twitter_metadata = {}
        for meta in soup.find_all('meta', attrs={'name': re.compile(r'^twitter:')}):
            if meta.get('content'):
                key = meta.get('name').replace('twitter:', 'twitter_')
                twitter_metadata[key] = meta.get('content')
        
        if twitter_metadata:
            metadata['twitter_card'] = twitter_metadata
        
        # Schema.org/Article (JSON-LD)
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string)
                if isinstance(data, dict):
                    if data.get('@type') in ['Article', 'NewsArticle', 'BlogPosting']:
                        metadata['schema_org'] = {
                            'type': data.get('@type'),
                            'headline': data.get('headline'),
                            'author': data.get('author', {}).get('name') if isinstance(data.get('author'), dict) else data.get('author'),
                            'datePublished': data.get('datePublished'),
                            'dateModified': data.get('dateModified'),
                            'publisher': data.get('publisher', {}).get('name') if isinstance(data.get('publisher'), dict) else None,
                        }
                        break
            except:
                continue
        
        # Clean up None values
        metadata = {k: v for k, v in metadata.items() if v is not None}
        
        return metadata
    
    def _remove_boilerplate(self, soup: BeautifulSoup):
        """Remove boilerplate elements from soup"""
        # Remove comments
        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()
        
        # Remove boilerplate elements
        for selector in self.BOILERPLATE_SELECTORS:
            for element in soup.select(selector):
                element.decompose()
        
        # Remove elements with specific text patterns
        for pattern in self.LOW_VALUE_PATTERNS:
            regex = re.compile(pattern, re.IGNORECASE)
            for element in soup.find_all(string=regex):
                if element.parent:
                    element.parent.decompose()
    
    def _extract_text_from_soup(self, soup: BeautifulSoup) -> str:
        """Extract clean text from soup"""
        # Try to find main content areas
        main_content = None
        for selector in ['main', 'article', '[role="main"]', '.content', '#content', '.post', '.entry-content']:
            main_content = soup.select_one(selector)
            if main_content:
                break
        
        # Use main content if found, otherwise use body
        content = main_content or soup.body or soup
        
        # Get text with proper spacing
        lines = []
        for element in content.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'td', 'th', 'blockquote']):
            text = element.get_text(strip=True)
            if text and not self._is_low_value_text(text):
                lines.append(text)
        
        # Join with proper spacing
        text = '\n\n'.join(lines)
        
        # Collapse whitespace
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return text.strip()
    
    def _is_low_value_text(self, text: str) -> bool:
        """Check if text is low-value boilerplate"""
        if len(text) < 20:  # Too short
            for pattern in self.LOW_VALUE_PATTERNS:
                if re.match(pattern, text, re.IGNORECASE):
                    return True
        return False
    
    def post_process(self, text: str) -> str:
        """Post-process extracted text"""
        if not text:
            return ""
        
        # Remove repeated headers/footers
        lines = text.split('\n')
        
        # Find and remove repeated lines (likely headers/footers)
        line_counts = {}
        for line in lines:
            clean_line = line.strip()
            if clean_line and len(clean_line) > 10:
                line_counts[clean_line] = line_counts.get(clean_line, 0) + 1
        
        # Remove lines that appear more than 3 times (likely boilerplate)
        repeated_lines = {line for line, count in line_counts.items() if count > 3}
        
        cleaned_lines = []
        for line in lines:
            if line.strip() not in repeated_lines:
                cleaned_lines.append(line)
        
        text = '\n'.join(cleaned_lines)
        
        # Final whitespace normalization
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return text.strip()