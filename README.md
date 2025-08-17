# 📄 DocuVec

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

**In simple terms:** Feed it your documents → Get back AI-ready knowledge that can answer questions about your content.

## Features

### **Intelligent Processing**
- **MIME-based routing** - Automatically detects and routes content to appropriate extractors
- **Multi-format support** - PDF, HTML, DOCX, PPTX, XLSX, JSON, CSV, Markdown
- **Tiered HTML extraction** - trafilatura → readability → BeautifulSoup with fallback
- **Rich metadata preservation** - Extracts title, author, dates, Open Graph, Twitter Cards, Schema.org
- **Advanced boilerplate removal** - Strips nav, comments, ads, "related posts", cookie banners
- **Language detection** - Auto-detects content language from HTML tags or content
- **Advanced text cleaning** that actually works (goodbye, corrupted PDFs!)
- **Structure-aware chunking** - Splits by headings → paragraphs → sentences, preserving document hierarchy
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
    A[📄 Your Documents] --> B[🔄 DocuVec Pipeline]
    B --> C[🧹 Clean & Normalize]
    C --> D[✂️ Smart Chunking]
    D --> E[🔢 Generate Embeddings]
    E --> F[💾 Vector Database]
    F --> G[🤖 Your RAG App]
```

1. **Fetch** - Downloads and detects content type via HTTP headers
2. **Route** - MIME-based routing to appropriate extractor
3. **Extract** - Tiered extraction (trafilatura → readability → BeautifulSoup)
4. **Clean** - Removes boilerplate, normalizes text, strips repeated content
5. **Chunk** - Structure-aware splitting by headings with hierarchical context
6. **Filter** - Quality gates remove low-signal content (ads, link lists, etc.)
7. **Embed** - Generates vector embeddings via OpenAI
8. **Store** - Outputs JSONL ready for any vector database with rich metadata

## What You Get

```json
{
  "id": "doc#00001-a3f5b2c8",
  "text": "Your intelligently chunked content here...",
  "embedding": [0.1234, -0.5678, ...],  // 1536 dimensions
  "metadata": {
    "source": "document.pdf",
    "page": 42,
    "category": "technical",
    "topics": ["api", "authentication"]
  }
}
```

## Real-World Example

I used DocuVec to process **970+ cloud certification documents** and built an exam question generator. It went from scattered PDFs to a working Q&A system in under an hour:

- **Input**: 150+ PDFs from AWS, Azure, GCP
- **Output**: 972 semantic chunks with embeddings
- **Cost**: ~$0.50 total
- **Result**: AI that answers certification questions with 85% accuracy

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