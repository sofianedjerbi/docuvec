# Cloud Certification ETL Pipeline - Clean Architecture

A modular Python ETL pipeline that processes cloud certification documentation with advanced text cleaning and generates embeddings for RAG systems.

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
   - id: "exam-guide-clf-c02"
     url: "https://..."
     title: "AWS CLF-C02 Exam Guide"
     tags:
       type: "cert"         # REQUIRED: 'cert' or 'service'
       provider: "AWS"      # REQUIRED: 'AWS', 'Azure', or 'GCP'
       certification: "CLF-C02"
       service: []          # For service docs: ["EC2"], ["S3"], etc.
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
  type: "cert"         # → {provider}/cert/{certification}.jsonl
  type: "service"      # → {provider}/service/{service_name}.jsonl
  provider: "AWS"      # → aws/...
  certification: "CLF-C02"  # Used for cert filename
  service: ["EC2"]     # Used for service filename
```

**Path Logic (No Guessing!):**
- `type: "cert"` + `provider: "AWS"` + `certification: "CLF-C02"` → `aws/cert/clf-c02.jsonl`
- `type: "service"` + `provider: "AWS"` + `service: ["EC2"]` → `aws/service/ec2.jsonl`

### Organized Directory Structure
```
data/
├── chunks/
│   ├── aws/
│   │   ├── cert/
│   │   │   ├── clf-c02.jsonl    # Cloud Practitioner
│   │   │   ├── saa-c03.jsonl    # Solutions Architect
│   │   │   ├── dva-c02.jsonl    # Developer Associate
│   │   │   ├── soa-c02.jsonl    # SysOps Administrator
│   │   │   └── sap-c02.jsonl    # Solutions Architect Pro
│   │   └── service/
│   │       ├── ec2.jsonl        # EC2 documentation
│   │       ├── s3.jsonl         # S3 documentation
│   │       ├── lambda.jsonl     # Lambda documentation
│   │       ├── vpc.jsonl        # VPC documentation
│   │       └── iam.jsonl        # IAM documentation
│   ├── azure/
│   │   ├── cert/
│   │   │   ├── az-900.jsonl     # Azure Fundamentals
│   │   │   ├── az-104.jsonl     # Azure Administrator
│   │   │   └── az-305.jsonl     # Azure Solutions Architect
│   │   └── service/
│   │       ├── vm.jsonl         # Virtual Machines
│   │       └── storage.jsonl    # Azure Storage
│   └── gcp/
│       ├── cert/
│       │   ├── ace.jsonl        # Associate Cloud Engineer
│       │   └── pca.jsonl        # Professional Cloud Architect
│       └── service/
│           ├── compute-engine.jsonl
│           ├── cloud-storage.jsonl
│           └── gke.jsonl
├── embeds/
│   └── [same structure as chunks/]
└── summary.json
```

### JSONL Chunks Format
**Certification Resource** (`aws/cert/clf-c02.jsonl`):
```json
{
  "id": "exam-guide-clf-c02#00001-a3f5b2c8d9e1f4a7",
  "text": "The AWS Certified Cloud Practitioner validates...",
  "source_url": "https://.../AWS-Certified-Cloud-Practitioner_Exam-Guide.pdf",
  "page_title": "AWS CLF-C02 Exam Guide",
  "service": [],
  "domain_exam": "Cloud Concepts",
  "certification": "CLF-C02",
  "provider": "AWS",
  "chunk_index": 1,
  "total_chunks": 45,
  "is_low_signal": false,
  "section_type": "content"
}
```

**Service Resource** (`aws/service/ec2.jsonl`):
```json
{
  "id": "ec2-concepts#00012-6c9a1b5f0b5a3f7e",
  "text": "Amazon EC2 provides scalable computing...",
  "source_url": "https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/concepts.html",
  "page_title": "EC2 Concepts",
  "service": ["EC2"],
  "domain_exam": "Cloud Technology and Services",
  "certification": "CLF-C02",
  "provider": "AWS",
  "chunk_index": 12,
  "total_chunks": 87,
  "is_low_signal": false,
  "section_type": "content"
}
```

### JSONL Embeddings (`aws/service/ec2.jsonl` in embeds/)
```json
{
  "id": "ec2-concepts#00012-6c9a1b5f0b5a3f7e",
  "embedding": [0.1234, -0.5678, ... 1536 floats ...]
}
```

## Quality Metrics & Summary

The pipeline generates an enhanced `summary.json` with:

### Organization Structure
```json
{
  "organization": {
    "aws": {
      "certifications": [
        {"code": "clf-c02", "chunks": 450, "file": "aws/cert/clf-c02.jsonl"},
        {"code": "saa-c03", "chunks": 380, "file": "aws/cert/saa-c03.jsonl"}
      ],
      "services": [
        {"name": "ec2", "chunks": 120, "file": "aws/service/ec2.jsonl"},
        {"name": "s3", "chunks": 95, "file": "aws/service/s3.jsonl"}
      ],
      "total_chunks": 1045
    }
  }
}
```

### Statistics Tracked
- **By Provider**: AWS, Azure, GCP chunk distribution
- **By Certification**: CLF-C02, SAA-C03, DVA-C02, etc.
- **By Service**: EC2, S3, Lambda, VPC, etc.
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
  service       text[],
  domain_exam   text,
  certification text,
  provider      text,
  chunk_index   int,
  total_chunks  int,
  is_low_signal boolean,
  section_type  text,
  embedding     vector(1536)  -- For text-embedding-3-small
);

CREATE INDEX idx_embedding ON rag_chunks 
  USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX idx_service ON rag_chunks USING GIN (service);
CREATE INDEX idx_cert ON rag_chunks (certification);
```