# Contributing to DocuVec

Technical documentation and contribution guidelines for DocuVec - the intelligent ETL pipeline for RAG systems.

## Features

### Core Capabilities
- ✅ **Modern OpenAI API**: Uses `text-embedding-3-small` (latest model)
- ✅ **Token-based chunking**: Proper token counting with `tiktoken` (700 tokens/chunk, 80 overlap)
- ✅ **Real PDF extraction**: Extracts actual text from PDFs using `pypdf`
- ✅ **Batched embeddings**: Processes 64 chunks per API call for efficiency
- ✅ **JSONL output**: RAG-ready format for pgvector and vector databases
- ✅ **Stable chunk IDs**: Content-hash based IDs that don't change
- ✅ **Smart caching**: Settings-aware caching prevents duplicate token usage

### Advanced Text Cleaning
- ✅ **Intelligent extraction**: Uses trafilatura for boilerplate removal
- ✅ **Content-density heuristics**: Automatically removes nav/footer/sidebar/ads
- ✅ **Unicode normalization**: NFC normalization, ligature fixes (ﬁ→fi, ﬀ→ff)
- ✅ **Header/footer stripping**: Removes repetitive page elements
- ✅ **Bullet normalization**: Consistent list formatting (•→-)
- ✅ **Low-signal detection**: Identifies and tags reference sections
- ✅ **Deduplication**: Removes duplicate chunks via content hashing
- ✅ **Sentence boundary polish**: Clean chunk edges
- ✅ **Quality validation**: Filters tiny/empty chunks (<40 tokens)

### Clean Architecture
- ✅ **SOLID principles**: Single responsibility per service
- ✅ **Modular design**: Separate services for each concern
- ✅ **Comprehensive logging**: File + console with detailed tracking
- ✅ **Environment configuration**: Flexible `.env` configuration
- ✅ **Retry logic**: Exponential backoff for network requests
- ✅ **Content caching**: Avoid re-fetching same URLs
- ✅ **Pipeline caching**: Settings-aware caching for chunks and embeddings

## Project Structure

```
src/
├── core/
│   ├── config.py          # Centralized configuration
│   ├── logger.py          # Logging setup
│   └── orchestrator.py    # Main pipeline orchestrator
├── models/
│   ├── source.py          # Source data model
│   └── chunk.py           # Chunk data model with metadata
├── services/
│   ├── source_loader.py   # YAML source loading
│   ├── content_fetcher.py # Content fetching with retry
│   ├── text_processor.py  # Advanced text cleaning
│   ├── text_chunker.py    # Token-based chunking
│   ├── embeddings_generator.py # Batched embeddings
│   └── data_writer.py     # JSONL output writer
└── utils/
    └── validation.py      # Chunk quality validation
main.py                    # CLI entry point
```

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your OpenAI API key
   ```

3. **Prepare sources with explicit types:**
   ```yaml
   # sources.yaml must include 'type' field for each source
   - id: "doc-001"
     url: "https://..."
     title: "Technical Documentation"
     tags:
       type: "document"     # Type of document
       category: "technical" # Category for organization
       topic: "api"        # Specific topic
       language: "en"      # Language code
   ```

4. **Run the pipeline:**
   ```bash
   python main.py
   
   # With custom options
   python main.py --sources custom.yaml --output results --model text-embedding-3-large
   
   # Cache management
   python main.py --cache-info          # Show cache status
   python main.py --clear-cache         # Clear all caches
   ```

## Text Processing Pipeline

1. **Normalize early**: Unicode NFC, fix ligatures, collapse whitespace
2. **Strip headers/footers**: Remove page numbers, copyright notices
3. **Clean lists**: Normalize bullets (•→-), fix numbered lists
4. **Detect low-signal**: Tag reference/resource sections
5. **Polish boundaries**: Clean sentence endings at chunk edges
6. **Deduplicate**: Remove exact duplicate chunks
7. **Validate**: Filter chunks <40 tokens, check quality

## Output Format

### How Output Paths Are Determined

The output path for each chunk is determined by explicit fields in `sources.yaml`:

```yaml
tags:
  type: "document"     # → {category}/documents/{doc_id}.jsonl
  type: "service"      # → {category}/service/{service_name}.jsonl
  category: "technical" # → technical/...
  topic: "api"         # Used for categorization
  service: ["auth"]    # Used for service filename
```

**Path Logic (No Guessing!):**
- `type: "document"` + `category: "technical"` → `technical/documents/{doc_id}.jsonl`
- `type: "service"` + `category: "api"` → `api/service/{service_name}.jsonl`

### Organized Directory Structure
```
data/
├── chunks/
│   ├── technical/              # Category: Technical docs
│   │   ├── documents/
│   │   │   ├── api-guide.jsonl
│   │   │   ├── user-manual.jsonl
│   │   │   └── reference.jsonl
│   │   └── service/
│   │       ├── auth.jsonl
│   │       ├── database.jsonl
│   │       └── storage.jsonl
│   ├── medical/                # Category: Medical docs
│   │   ├── documents/
│   │   │   ├── protocols.jsonl
│   │   │   └── guidelines.jsonl
│   │   └── research/
│   │       └── papers.jsonl
│   └── legal/                  # Category: Legal docs
│       ├── documents/
│       │   ├── contracts.jsonl
│       │   └── policies.jsonl
│       └── compliance/
│           └── regulations.jsonl
├── embeds/
│   └── [same structure as chunks/]
└── summary.json
```

### JSONL Chunks Format
**Document Resource** (`technical/programming/python-docs.jsonl`):
```json
{
  "id": "python-docs#00001-a3f5b2c8d9e1f4a7",
  "text": "Python is an interpreted, high-level programming language...",
  "source_url": "https://docs.python.org/3/",
  "page_title": "Python 3 Documentation",
  "category": "technical",
  "subcategory": "programming",
  "tags": ["python", "programming", "reference"],
  "chunk_index": 1,
  "total_chunks": 45,
  "is_low_signal": false,
  "section_type": "content"
}
```

**Research Paper** (`research/ml/transformers.jsonl`):
```json
{
  "id": "transformers#00012-6c9a1b5f0b5a3f7e",
  "text": "The Transformer model architecture relies entirely on self-attention...",
  "source_url": "https://arxiv.org/abs/1706.03762",
  "page_title": "Attention Is All You Need",
  "category": "research",
  "subcategory": "machine_learning",
  "tags": ["transformers", "nlp", "deep_learning"],
  "metadata": {"authors": ["Vaswani et al."], "year": 2017},
  "chunk_index": 12,
  "total_chunks": 87,
  "is_low_signal": false,
  "section_type": "content"
}
```

### JSONL Embeddings (`technical/programming/python-docs.jsonl` in embeds/)
```json
{
  "id": "python-docs#00012-6c9a1b5f0b5a3f7e",
  "embedding": [0.1234, -0.5678, ... 1536 floats ...]
}
```

## Quality Metrics & Summary

The pipeline generates an enhanced `summary.json` with:

### Organization Structure
```json
{
  "organization": {
    "technical": {
      "documents": [
        {"id": "python-docs", "chunks": 450, "file": "technical/programming/python-docs.jsonl"},
        {"id": "kubernetes-docs", "chunks": 380, "file": "technical/infrastructure/kubernetes-docs.jsonl"}
      ],
      "total_chunks": 830
    },
    "research": {
      "documents": [
        {"id": "transformers-paper", "chunks": 120, "file": "research/ml/transformers.jsonl"},
        {"id": "bert-paper", "chunks": 95, "file": "research/ml/bert.jsonl"}
      ],
      "total_chunks": 215
    }
  }
}
```

### Statistics Tracked
- **By Category**: Technical, Research, Medical, Legal distribution
- **By Subcategory**: Programming, Infrastructure, ML, etc.
- **By Tags**: Common topics and themes across documents
- **By Section Type**: content, references, toc, code
- **Low-signal percentage**: Target <5%
- **Files written**: Complete list of output files

## Configuration (.env)

```bash
# OpenAI Settings
OPENAI_API_KEY=your-key-here
EMBED_MODEL=text-embedding-3-small  # or text-embedding-3-large
EMBED_BATCH=64                      # Batch size for embeddings

# Chunking Settings
MAX_TOKENS=700                      # Target tokens per chunk
OVERLAP_TOKENS=80                   # Overlap between chunks
MIN_TOKENS=40                       # Minimum tokens (skip smaller)

# Network Settings
REQUEST_DELAY=1.0                   # Seconds between requests
EMBEDDING_DELAY=0.1                 # Seconds between batches
MAX_RETRIES=4                       # Retry attempts
TIMEOUT=30                          # Request timeout
```

## Cost Optimization

- **Batched embeddings**: 10x faster than individual calls
- **text-embedding-3-small**: 5x cheaper than ada-002
- **Content caching**: Avoids re-fetching same URLs
- **Pipeline caching**: Skips processing when settings unchanged
- **Embedding caching**: Reuses embeddings across runs
- **Deduplication**: Reduces redundant embeddings
- **Estimated cost**: ~$0.001-$0.005 for 70+ sources (first run only)

## Smart Caching System

The pipeline includes comprehensive caching to prevent token waste:

### Cache Types
1. **Content Cache**: Fetched URLs (24hr TTL)
2. **Pipeline Cache**: Processed chunks based on settings hash
3. **Embeddings Cache**: Generated embeddings by model

### Cache Logic
- **Settings Hash**: Includes tokens, model, overlap - if unchanged, uses cache
- **Source Hash**: Detects changes in sources.yaml content
- **Automatic Invalidation**: 24hr age limit for freshness
- **Chunk-level Caching**: Reuses embeddings even for partial runs

### Cache Commands
```bash
python main.py --cache-info     # Show cache status and age
python main.py --clear-cache    # Force fresh processing
```

Cache prevents duplicate token usage when:
- Running with same settings multiple times
- Interrupted runs (resumes from cached chunks)
- Model changes (keeps chunks, regenerates embeddings)
- Minor source.yaml edits (processes only changed sources)

## Validation Checklist

✅ No repeating headers/footers in chunks  
✅ Bullets appear as `- item` (not jammed paragraphs)  
✅ <5% chunks tagged as low-signal/references  
✅ Stable chunk IDs that don't change between runs  
✅ Clean sentence boundaries at chunk edges  
✅ No duplicate chunks in output  
✅ Quality metrics logged and tracked  

## PostgreSQL Integration

Ready for pgvector with proper schema:

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE rag_chunks (
  id            text PRIMARY KEY,
  text          text NOT NULL,
  source_url    text,
  page_title    text,
  category      text,
  subcategory   text,
  tags          text[],
  metadata      jsonb,
  chunk_index   int,
  total_chunks  int,
  is_low_signal boolean,
  section_type  text,
  embedding     vector(1536)  -- For text-embedding-3-small
);

CREATE INDEX idx_embedding ON rag_chunks 
  USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX idx_category ON rag_chunks (category);
CREATE INDEX idx_tags ON rag_chunks USING GIN (tags);
```

---

# Technical Documentation

## Chunk Schema

Complete schema specification for DocuVec chunks with enhanced metadata and compliance fields:

### Chunk ID Format

Chunks use a stable, deterministic ID format: `<doc_id>#<zero-padded_index>-<sha1_8>`

Example: `ceh-cert#00000-b3869028`

- **doc_id**: Stable document identifier (SHA256 hash of canonical URL)
- **index**: Zero-padded 5-digit chunk index (00000-99999)
- **sha1_8**: First 8 characters of content SHA1 hash

This format ensures:
- Stable IDs across re-processing
- Efficient deduplication
- Sortable by document and position
- Content verification via hash

### Enhanced Chunk Fields

#### Complete Example Chunk
```json
{
  "id": "doc_abc123#00001-7d865e95",
  "doc_id": "doc_abc123",
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
  "category": "technical",
  "subcategory": "api_documentation",
  "tags": ["auth", "api", "security"],
  "metadata": {"version": "2.0", "deprecated": false}
}
```

### Chunk Format Improvements

The chunk format has been enhanced with the following improvements:

#### 1. **Stable Chunk IDs**
- Format: `<doc_id>#<zero-padded_index>-<sha1_8>`
- Example: `ceh-cert#00000-b3869028`
- Ensures consistent IDs across re-processing for deduplication

#### 2. **Domain Normalization**
- Automatically removes `www.` prefix from domains
- `www.example.com` → `example.com`
- Consistent domain filtering and grouping

#### 3. **Content Cleaning**
- **YAML Frontmatter Stripping**: Removes `---...---` metadata blocks
- **Page Chrome Removal**: Strips navigation, breadcrumbs, footers
- **Meta Pattern Cleaning**: Removes `title:`, `url:`, `author:` lines
- Results in cleaner, more relevant chunk content

#### 4. **Character Offset Tracking**
- `char_start` and `char_end` fields track exact positions
- Enables accurate context reconstruction
- Supports highlight generation in source documents

#### 5. **Enhanced Metadata**
- **source_type**: Categorizes content (official_docs, academic, news, etc.)
- **modality**: Content type (text, table, code, equation)
- **language_confidence**: Confidence score for language detection
- **robots_noindex/robots_nofollow**: Respects HTML meta directives
- **doc_sha1**: Document-level hash for re-crawl detection

#### 6. **Section Type Detection**
- Automatically detects content structure
- `"structured"`: Content with headings/sections
- `"simple"`: Plain text without structure
- Improves retrieval accuracy

#### 7. **Content Feature Detection**
- Detects headings, code blocks, tables, lists
- Counts outbound links
- Enables feature-based filtering and ranking

#### 8. **Enhanced Embedding Support**
- **embedding**: Vector for ANN index (Approximate Nearest Neighbor)
- **embedding_model**: Track which model generated the vectors
- **embedding_dim**: Dimension count for proper index configuration
- Enables efficient vector search and model versioning

#### 9. **Improved Document Structure**
- **doc_type**: Clearer than `format` for document type identification
- **section_path**: Complete section hierarchy (e.g., ["Overview", "Eligibility", "Requirements"])
- **tokens**: Pre-computed for efficient context window management
- Better navigation and more granular content targeting

### Field Descriptions

#### Core Fields
| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique chunk identifier (format: `doc_id#index-hash`) |
| `doc_id` | string | Stable document ID from canonical URL hash |
| `text` | string | The actual chunk content (cleaned and processed) |
| `embedding` | float[] | Vector embedding for ANN index |
| `embedding_model` | string | Model used (e.g., text-embedding-3-small) |
| `embedding_dim` | integer | Embedding dimensions (1536 or 3072) |
| `tokens` | integer | Token count for context budgets |

#### Versioning & Auditability
| Field | Type | Description |
|-------|------|-------------|
| `schema_version` | string | Schema version for migrations |
| `pipeline_version` | string | ETL pipeline version hash |
| `tokenizer` | string | Tokenizer used (e.g., `cl100k_base`) |

#### URL & Navigation
| Field | Type | Description |
|-------|------|-------------|
| `source_url` | string | Original URL with fragments |
| `canonical_url` | string | Normalized URL without fragments |
| `domain` | string | Normalized domain (www. removed) |
| `path` | string | URL path for section filtering |
| `anchor_url` | string | Deep link to exact location |
| `page_num` | integer/null | PDF page number if applicable |
| `anchor_id` | string | HTML anchor/fragment ID |

#### Content Metadata
| Field | Type | Description |
|-------|------|-------------|
| `page_title` | string | Full hierarchical title string |
| `title_hierarchy` | string[] | Title components as array (limited) |
| `section_path` | string[] | Complete section hierarchy path |
| `lang` | string | ISO 639-1 language code |
| `language_confidence` | float | Confidence in language detection (0.0-1.0) |
| `format` | string | Content format: `html\|pdf\|docx\|markdown\|txt` |
| `doc_type` | string | Document type (clearer than format) |
| `modality` | string | Content type: `text\|table\|code\|equation` |
| `source_type` | string | Source category: `official_docs\|academic\|news\|community` |
| `word_count` | integer | Word count for snippet generation |

#### Timestamps & Hashing
| Field | Type | Description |
|-------|------|-------------|
| `published_at` | datetime/null | Document publication date (ISO 8601) |
| `modified_at` | datetime/null | Last modification date (ISO 8601) |
| `crawl_ts` | datetime | When DocuVec processed (ISO 8601) |
| `content_sha1` | string | SHA1 of cleaned text (40 chars) |
| `doc_sha1` | string | SHA1 of full document (16 chars for dedup) |
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
| `robots_noindex` | boolean | Respects robots meta noindex directive |
| `robots_nofollow` | boolean | Respects robots meta nofollow directive |

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
| `char_start` | integer/null | Character offset start in document |
| `char_end` | integer/null | Character offset end in document |

#### Legacy/Optional Fields
| Field | Type | Description |
|-------|------|-------------|
| `category` | string | Document category (technical, medical, legal, etc.) |
| `subcategory` | string | Subcategory for finer organization |
| `tags` | string[] | Flexible tagging system |
| `metadata` | object | Custom metadata specific to domain |

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