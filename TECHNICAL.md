# Technical Documentation

## Chunk Schema v2.0.0

Complete schema specification for DocuVec chunks:

```json
{
  // === CORE FIELDS ===
  "id": "doc_id#00001-hash",           // Unique chunk identifier
  "doc_id": "a3f5b2c8",                // Stable document ID from canonical URL
  "text": "The actual chunk content...", // Cleaned, extracted text
  "embedding": [0.123, -0.456, ...],   // Vector embedding (1536D or 3072D)
  
  // === VERSIONING & AUDITABILITY ===
  "schema_version": "2.0.0",           // Schema version for migrations
  "pipeline_version": "abc123def",     // ETL pipeline version hash
  "embedding_model": "text-embedding-3-small",  // Model used for vectors
  "embedding_dim": 1536,                // Embedding dimensions
  "tokenizer": "cl100k_base",          // Tokenizer used for chunking
  
  // === URL & NAVIGATION ===
  "source_url": "https://example.com/docs/api.html#section",
  "canonical_url": "https://example.com/docs/api.html",  // Normalized URL
  "domain": "example.com",             // Domain for filtering
  "path": "/docs/api.html",            // Path for section filtering
  "anchor_url": "https://example.com/docs/api.html#auth",  // Deep link
  "page_num": 42,                      // PDF page number (if applicable)
  "anchor_id": "auth",                 // HTML anchor ID
  
  // === CONTENT METADATA ===
  "page_title": "API Documentation > Security > Authentication",
  "title_hierarchy": ["API Documentation", "Security", "Authentication"],
  "lang": "en",                        // ISO language code
  "content_type": "html",              // html|pdf|docx|markdown|txt
  "source_type": "crawl",              // crawl|upload|api|file
  "word_count": 127,                   // Word count for snippets
  "tokens": 95,                        // Token count for limits
  
  // === TIMESTAMPS & HASHING ===
  "published_at": "2024-01-15T10:00:00Z",  // Document publish date
  "modified_at": "2024-03-20T14:00:00Z",   // Last modification
  "crawl_ts": "2024-03-22T09:15:00Z",      // When DocuVec processed
  "content_sha1": "7d865e959b2466918c9863afca942d0fb89d7c9a",  // Clean text hash
  "original_sha1": "8b2466918c9863afca942d0fb89d7c9a7d865e95", // Raw content hash
  "simhash": "1101011010101010",           // Near-duplicate detection
  
  // === QUALITY & RELEVANCE ===
  "retrieval_weight": 1.2,             // 0.0-1.5 (boost FAQs, downweight footers)
  "source_confidence": 0.95,           // 0.0-1.0 (trust score)
  "is_low_signal": false,              // Low-quality content flag
  "low_signal_reason": "",             // navigation|footer|legal|advertisement
  "section_type": "structured",        // structured|simple|content
  
  // === PRIVACY & COMPLIANCE ===
  "pii_flags": {                       // PII detection results
    "email": false,
    "phone": false,
    "ssn": false,
    "credit_card": false,
    "ip_address": false,
    "person_name": false,
    "address": false,
    "id_number": false
  },
  "license": "MIT",                    // Content license
  "attribution_required": true,        // Attribution needed
  "noindex": false,                    // Respect robots meta
  "nofollow": false,                   // Respect link following
  
  // === CONTENT FEATURES ===
  "has_code": true,                    // Contains code blocks
  "has_table": false,                  // Contains tables
  "has_list": true,                    // Contains lists
  "headings": ["Authentication", "OAuth 2.0"],  // Section headings
  "links_out": 5,                      // Number of external links
  
  // === CHUNK POSITION ===
  "chunk_index": 3,                    // Position in document (0-based)
  "total_chunks": 15,                  // Total chunks from document
  "chunk_char_start": 1250,            // Character offset start
  "chunk_char_end": 2100,              // Character offset end
  
  // === LEGACY/OPTIONAL FIELDS ===
  "service": ["auth"],                 // Service names (for API docs)
  "domain_exam": "",                   // Domain/exam category
  "certification": "",                  // Certification code
  "provider": "technical",             // Category/provider
  "resource_type": "document"          // document|service
}
```

## Architecture Overview

### Core Services

- **ContentFetcher**: Downloads and caches content
- **MimeRouter**: Detects content type and routes to extractors
- **HTMLExtractor**: Tiered HTML extraction (trafilatura → readability → BeautifulSoup)
- **TextProcessor**: Advanced text cleaning and normalization
- **StructureChunker**: Heading-aware intelligent chunking
- **TextChunkerV2**: Enhanced chunking with full metadata
- **EmbeddingService**: Batched OpenAI embeddings generation
- **DataWriter**: JSONL output with organization

### Utilities

- **ChunkEnricher**: Metadata extraction and enrichment
- **PIIDetector**: Privacy compliance and PII detection
- **PipelineVersioning**: Version tracking and auditability
- **PipelineCache**: Multi-level caching system

## Processing Pipeline

1. **Source Loading** - Parse sources.yaml configuration
2. **Content Fetching** - Download with caching and retry logic
3. **MIME Detection** - Route to appropriate extractor
4. **Content Extraction** - Format-specific extraction
5. **Text Processing** - Clean, normalize, deduplicate
6. **Structure Analysis** - Parse headings and hierarchy
7. **Smart Chunking** - Structure-aware splitting
8. **Metadata Enrichment** - Add all production fields
9. **Quality Filtering** - Remove low-signal content
10. **Embedding Generation** - Batched API calls
11. **Data Writing** - Organized JSONL output

## Configuration

### Environment Variables

```bash
# API Configuration
OPENAI_API_KEY=your-key-here

# Embedding Configuration
EMBED_MODEL=text-embedding-3-small
EMBED_BATCH=64
EMBED_DIM=1536

# Chunking Configuration
MAX_TOKENS=700
OVERLAP_TOKENS=80
MIN_TOKENS=40

# Network Configuration
REQUEST_DELAY=1.0
EMBEDDING_DELAY=0.1
MAX_RETRIES=4
TIMEOUT=30

# Optional Features
ENABLE_OCR=false
ENABLE_PII_DETECTION=true
```

### Sources Configuration

```yaml
- id: "unique-doc-id"
  url: "https://example.com/document.pdf"
  title: "Document Title"
  tags:
    type: "document"          # document|service
    category: "technical"     # Any category
    language: "en"           # ISO code
    license: "MIT"           # Optional
    topics: ["api", "auth"]  # Optional
```

## Quality Scoring

### Retrieval Weight Adjustments

- **1.3x**: Titles and headers
- **1.2x**: Introductions, FAQs
- **1.1x**: Summaries, examples
- **1.0x**: Normal content (default)
- **0.7x**: References, appendices
- **0.5x**: Footers, copyright notices
- **0.3x**: Navigation, menus

### Source Confidence Factors

- **1.0**: Official documentation
- **0.9**: Verified sources
- **0.8**: Community content
- **0.7**: User-generated content
- **0.5**: Unverified sources

### Low Signal Detection

Content is flagged as low-signal if:
- Token count < 40
- >50% navigation/footer patterns
- >30% punctuation or digits
- Link-only content
- Repeated boilerplate

## Performance Characteristics

- **Processing Speed**: ~100 pages/minute
- **Token Efficiency**: 700 tokens/chunk with 80 overlap
- **API Calls**: Batched in groups of 64
- **Cache Hit Rate**: Typically >80% on re-runs
- **Memory Usage**: ~1GB for 10,000 chunks
- **Cost**: ~$0.001 per 100 pages

## Integration Examples

### With Pinecone

```python
import pinecone
import json

# Read DocuVec output
with open('data/chunks/technical/documents/api.jsonl') as f:
    chunks = [json.loads(line) for line in f]

# Upsert to Pinecone
vectors = [
    (chunk['id'], chunk['embedding'], {
        'text': chunk['text'],
        'source': chunk['source_url'],
        'confidence': chunk['source_confidence']
    })
    for chunk in chunks
]
index.upsert(vectors)
```

### With pgvector

```sql
-- Create table
CREATE TABLE chunks (
    id TEXT PRIMARY KEY,
    doc_id TEXT,
    text TEXT,
    embedding vector(1536),
    metadata JSONB
);

-- Insert from DocuVec
COPY chunks FROM 'data/chunks/output.jsonl' WITH (FORMAT text);

-- Query with metadata filters
SELECT * FROM chunks
WHERE metadata->>'domain' = 'docs.example.com'
AND metadata->>'retrieval_weight' > 1.0
ORDER BY embedding <-> query_embedding
LIMIT 10;
```

## Extending DocuVec

### Adding New Extractors

Create a new extractor in `src/services/extractors/`:

```python
class CustomExtractor:
    def extract(self, content: bytes) -> str:
        # Your extraction logic
        return extracted_text
```

### Custom Quality Scoring

Modify `ChunkEnricher.calculate_retrieval_weight()`:

```python
def calculate_retrieval_weight(text, title, section_type):
    weight = 1.0
    # Add your custom logic
    if 'important' in title.lower():
        weight *= 1.5
    return weight
```

### PII Detection Extensions

Add patterns to `PIIDetector.PATTERNS`:

```python
PATTERNS = {
    'custom_id': r'[A-Z]{3}\d{6}',  # Your pattern
    # ...
}
```