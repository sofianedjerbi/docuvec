# 🚀 DocuVec

<div align="center">

**The intelligent ETL pipeline that transforms your documentation into production-ready RAG systems.**

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![OpenAI](https://img.shields.io/badge/OpenAI-Embeddings-green.svg)](https://openai.com/)
[![License](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

*From scattered documents to queryable knowledge. Any domain. Any scale.*

[Features](#-features) • [Quick Start](#-quick-start) • [Use Cases](#-use-cases) • [How It Works](#-how-it-works) • [Contributing](CONTRIBUTING.md)

</div>

---

## What is DocuVec?

Ever wanted to build a ChatGPT for your own documents? **DocuVec** is the missing piece that transforms ANY collection of documents (PDFs, HTML, text) into a vector database ready for Retrieval-Augmented Generation (RAG).

**In simple terms:** Feed it your documents, get back AI-ready knowledge that can answer questions about your content.

## Features

### **Intelligent Processing**
- **MIME-based routing** - Automatically detects and routes content to appropriate extractors
- **Multi-format support** - PDF, HTML, DOCX, PPTX, XLSX, JSON, CSV, Markdown
- **Tiered HTML extraction** - trafilatura, then readability, then BeautifulSoup with fallback
- **Rich metadata preservation** - Extracts title, author, dates, Open Graph, Twitter Cards, Schema.org
- **Advanced boilerplate removal** - Strips nav, comments, ads, "related posts", cookie banners
- **Language detection** - Auto-detects content language from HTML tags or content
- **Advanced text cleaning** that actually works (goodbye, corrupted PDFs!)
- **Structure-aware chunking** - Splits by headings, paragraphs, sentences, preserving document hierarchy
- **Hierarchical titles** - Each chunk gets context: "Page Title > Section > Subsection"
- **Quality gates** - Automatically filters low-signal chunks (link lists, ads, short fragments)
- **Automatic deduplication** - why embed the same content twice?
- **Low-signal detection** - filters out references, footers, and noise
- **OCR support** (optional) - Extract text from images and scanned PDFs

### **Production Ready**
- **Batched embeddings** - 10x faster than individual API calls
- **Smart caching** - Never process the same document twice
- **Cost optimized** - ~$0.001 per 100 pages with OpenAI
- **Modular architecture** - Swap components without breaking everything

### **Developer Friendly**
```bash
# It's literally this simple
pip install -r requirements.txt
python main.py --sources your_docs.yaml
```

## Quick Start

### 1. Clone & Setup
```bash
git clone https://github.com/sofianedjerbi/docuvec.git
cd docuvec
pip install -r requirements.txt
cp .env.example .env
```

### 2. Add your OpenAI key
```bash
# Edit .env
OPENAI_API_KEY=your-key-here
```

### 3. Define your sources
```yaml
# sources.yaml
- id: "my-docs"
  url: "https://example.com/important.pdf"
  title: "Important Document"
  tags:
    type: "technical"
    category: "documentation"
    subcategory: "api"
```

### 4. Run!
```bash
python main.py
```

**That's it!** Your documents are now vector embeddings ready for RAG.

## Use Cases

### **Build a ChatGPT for your:**

- 📖 **Technical Documentation** - "How do I configure X in our system?"
- 🏥 **Medical Records** - "What treatments were recommended for condition Y?"
- ⚖️ **Legal Documents** - "What does section 5.2 say about liability?"
- 🎓 **Educational Content** - "Explain concept Z from the course materials"
- 💼 **Company Knowledge** - "What's our policy on remote work?"
- 🔬 **Research Papers** - "What methods did Smith et al. use?"

## Supported Formats

DocuVec uses intelligent MIME-type detection to automatically route content to the appropriate extractor:

| Format | MIME Type | Extraction Method | OCR Support |
|--------|-----------|-------------------|-------------|
| **PDF** | `application/pdf` | PyPDF/PDFPlumber | ✅ Optional |
| **HTML** | `text/html` | Trafilatura | - |
| **Word** | `application/vnd.openxmlformats-officedocument.wordprocessingml.document` | python-docx/mammoth | - |
| **PowerPoint** | `application/vnd.openxmlformats-officedocument.presentationml.presentation` | python-pptx | - |
| **Excel** | `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` | openpyxl/pandas | - |
| **JSON** | `application/json` | Native parser | - |
| **CSV** | `text/csv` | pandas | - |
| **Markdown** | `text/markdown` | Direct extraction | - |
| **Images** | `image/*` | - | ✅ Tesseract |
| **Plain Text** | `text/plain` | Direct extraction | - |

## How It Works

```mermaid
graph LR
    A[Your Documents] --> B[DocuVec Pipeline]
    B --> C[Clean & Normalize]
    C --> D[Smart Chunking]
    D --> E[Generate Embeddings]
    E --> F[Vector Database]
    F --> G[Your RAG App]
```

1. **Fetch** - Downloads and detects content type via HTTP headers
2. **Route** - MIME-based routing to appropriate extractor
3. **Extract** - Tiered extraction (trafilatura, readability, BeautifulSoup)
4. **Clean** - Removes boilerplate, normalizes text, strips repeated content
5. **Chunk** - Structure-aware splitting by headings with hierarchical context
6. **Filter** - Quality gates remove low-signal content (ads, link lists, etc.)
7. **Embed** - Generates vector embeddings via OpenAI
8. **Store** - Outputs JSONL ready for any vector database with rich metadata

## Chunk Schema

DocuVec produces comprehensive, production-ready chunks with rich metadata:

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

This comprehensive schema enables:
- **Better retrieval** through weighted scoring and confidence metrics
- **Duplicate control** for efficient recrawling using content hashes
- **Advanced filtering** by domain, date, language, quality, or PII
- **Context reconstruction** using character offsets for larger windows
- **Compliance** with privacy regulations and content licensing
- **Full auditability** of the entire pipeline and processing versions

## Real-World Example

DocuVec has been used to process large collections of technical documents for building Q&A systems. Here's an example deployment:

- **Input**: Hundreds of PDFs from various technical sources
- **Output**: Thousands of semantic chunks with embeddings
- **Cost**: Minimal (typically under $1 for large document sets)
- **Result**: AI that answers domain-specific questions accurately

## Advanced Features

<details>
<summary><b>Smart Caching System</b></summary>

Never waste tokens on duplicate processing:
- Content cache (24hr TTL)
- Pipeline cache (settings-aware)
- Embeddings cache (model-specific)

```bash
python main.py --cache-info    # Check cache status
python main.py --clear-cache   # Start fresh
```
</details>

<details>
<summary><b>Flexible Configuration</b></summary>

Customize everything via `.env`:
```bash
MAX_TOKENS=700          # Chunk size
OVERLAP_TOKENS=80       # Semantic overlap
EMBED_MODEL=text-embedding-3-small
EMBED_BATCH=64          # Batch size
ENABLE_OCR=false        # Enable OCR for images/scanned PDFs
```
</details>

<details>
<summary><b>Quality Metrics</b></summary>

Get detailed insights on your processed data:
```json
{
  "total_chunks": 972,
  "by_category": {"technical": 597, "legal": 178},
  "low_signal_percentage": 2.3,
  "processing_time": "5m 23s"
}
```
</details>

## Contributing

We love contributions! Check out [CONTRIBUTING.md](CONTRIBUTING.md) for:
- Technical architecture details
- Code style guidelines
- How to add new extractors
- Pipeline extension points

## License

MIT - Use it for anything!

## Show Your Support

If DocuVec helped you build something cool:
- Star this repo
- Share your use case in [Discussions](https://github.com/sofianedjerbi/docuvec/discussions)
- Report bugs in [Issues](https://github.com/sofianedjerbi/docuvec/issues)

---

<div align="center">

**Built by developers who were tired of wrestling with PDFs**

*Transform your documents into intelligence. Today.*

[Get Started](#-quick-start) • [Read the Docs](CONTRIBUTING.md) • [Join Discussion](https://github.com/sofianedjerbi/docuvec/discussions)

</div>