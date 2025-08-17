# Technical Documentation

## Chunk Schema v2.0.0

Complete schema specification for DocuVec chunks:

### Example Chunk
```json
{
  "id": "doc_id#00001-hash",
  "doc_id": "a3f5b2c8",
  "text": "The actual chunk content...",
  "embedding": [0.123, -0.456],
  "schema_version": "2.0.0",
  "pipeline_version": "abc123def",
  "embedding_model": "text-embedding-3-small",
  "embedding_dim": 1536,
  "tokenizer": "cl100k_base",
  "source_url": "https://example.com/docs/api.html#section",
  "canonical_url": "https://example.com/docs/api.html",
  "domain": "example.com",
  "path": "/docs/api.html",
  "anchor_url": "https://example.com/docs/api.html#auth",
  "page_num": 42,
  "anchor_id": "auth",
  "page_title": "API Documentation > Security > Authentication",
  "title_hierarchy": ["API Documentation", "Security", "Authentication"],
  "lang": "en",
  "content_type": "html",
  "source_type": "crawl",
  "word_count": 127,
  "tokens": 95,
  "published_at": "2024-01-15T10:00:00Z",
  "modified_at": "2024-03-20T14:00:00Z",
  "crawl_ts": "2024-03-22T09:15:00Z",
  "content_sha1": "7d865e959b2466918c9863afca942d0fb89d7c9a",
  "original_sha1": "8b2466918c9863afca942d0fb89d7c9a7d865e95",
  "simhash": "1101011010101010",
  "retrieval_weight": 1.2,
  "source_confidence": 0.95,
  "is_low_signal": false,
  "low_signal_reason": "",
  "section_type": "structured",
  "pii_flags": {
    "email": false,
    "phone": false,
    "ssn": false,
    "credit_card": false,
    "ip_address": false,
    "person_name": false,
    "address": false,
    "id_number": false
  },
  "license": "MIT",
  "attribution_required": true,
  "noindex": false,
  "nofollow": false,
  "has_code": true,
  "has_table": false,
  "has_list": true,
  "headings": ["Authentication", "OAuth 2.0"],
  "links_out": 5,
  "chunk_index": 3,
  "total_chunks": 15,
  "chunk_char_start": 1250,
  "chunk_char_end": 2100,
  "service": ["auth"],
  "domain_exam": "",
  "certification": "",
  "provider": "technical",
  "resource_type": "document"
}
```

### Field Descriptions

#### Core Fields
| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique chunk identifier (format: `doc_id#index-hash`) |
| `doc_id` | string | Stable document ID from canonical URL hash |
| `text` | string | The actual chunk content (cleaned and processed) |
| `embedding` | float[] | Vector embedding (1536D for small, 3072D for large) |

#### Versioning & Auditability
| Field | Type | Description |
|-------|------|-------------|
| `schema_version` | string | Schema version for migrations |
| `pipeline_version` | string | ETL pipeline version hash |
| `embedding_model` | string | Model used for vector generation |
| `embedding_dim` | integer | Embedding dimensions (1536 or 3072) |
| `tokenizer` | string | Tokenizer used (e.g., `cl100k_base`) |

#### URL & Navigation
| Field | Type | Description |
|-------|------|-------------|
| `source_url` | string | Original URL with fragments |
| `canonical_url` | string | Normalized URL without fragments |
| `domain` | string | Domain for filtering |
| `path` | string | URL path for section filtering |
| `anchor_url` | string | Deep link to exact location |
| `page_num` | integer/null | PDF page number if applicable |
| `anchor_id` | string | HTML anchor/fragment ID |

#### Content Metadata
| Field | Type | Description |
|-------|------|-------------|
| `page_title` | string | Full hierarchical title string |
| `title_hierarchy` | string[] | Title components as array |
| `lang` | string | ISO 639-1 language code |
| `content_type` | string | Format: `html\|pdf\|docx\|markdown\|txt` |
| `source_type` | string | Source: `crawl\|upload\|api\|file` |
| `word_count` | integer | Word count for snippet generation |
| `tokens` | integer | Token count for context limits |

#### Timestamps & Hashing
| Field | Type | Description |
|-------|------|-------------|
| `published_at` | datetime/null | Document publication date (ISO 8601) |
| `modified_at` | datetime/null | Last modification date (ISO 8601) |
| `crawl_ts` | datetime | When DocuVec processed (ISO 8601) |
| `content_sha1` | string | SHA1 of cleaned text |
| `original_sha1` | string | SHA1 of raw content before cleaning |
| `simhash` | string | Simhash for near-duplicate detection |

#### Quality & Relevance
| Field | Type | Description |
|-------|------|-------------|
| `retrieval_weight` | float | 0.0-1.5 (boost FAQs, downweight footers) |
| `source_confidence` | float | 0.0-1.0 trust score |
| `is_low_signal` | boolean | Low-quality content flag |
| `low_signal_reason` | string | Reason: `navigation\|footer\|legal\|ad` |
| `section_type` | string | Type: `structured\|simple\|content` |

#### Privacy & Compliance
| Field | Type | Description |
|-------|------|-------------|
| `pii_flags` | object | PII detection results per type |
| `license` | string | Content license (e.g., MIT, CC-BY) |
| `attribution_required` | boolean | Whether attribution is needed |
| `noindex` | boolean | Respects robots meta noindex |
| `nofollow` | boolean | Respects robots meta nofollow |

#### Content Features
| Field | Type | Description |
|-------|------|-------------|
| `has_code` | boolean | Contains code blocks |
| `has_table` | boolean | Contains tables |
| `has_list` | boolean | Contains lists |
| `headings` | string[] | All headings in chunk |
| `links_out` | integer | Number of external links |

#### Chunk Position
| Field | Type | Description |
|-------|------|-------------|
| `chunk_index` | integer | Position in document (0-based) |
| `total_chunks` | integer | Total chunks from document |
| `chunk_char_start` | integer/null | Character offset start |
| `chunk_char_end` | integer/null | Character offset end |

#### Legacy/Optional Fields
| Field | Type | Description |
|-------|------|-------------|
| `service` | string[] | Service names for API docs |
| `domain_exam` | string | Domain/exam category |
| `certification` | string | Certification code |
| `provider` | string | Category/provider |
| `resource_type` | string | Type: `document\|service` |

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