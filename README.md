# 🧬 DocuVec

**Transform any document into AI-ready knowledge in minutes.**

DocuVec is the missing piece between your documents and ChatGPT-like systems. Feed it PDFs, websites, or any text - get back perfect chunks ready for AI search.

## Why DocuVec?

Building RAG (Retrieval-Augmented Generation) systems is hard. You need to:
- Extract text from dozens of formats
- Clean out ads, navigation, and junk
- Split content intelligently 
- Generate embeddings efficiently
- Track everything for updates

**DocuVec does all of this in one command.**

## Quick Start

```bash
# Install
pip install -r requirements.txt

# Configure your OpenAI key
cp .env.example .env
# Add your key to .env

# Run on any documents
python main.py --sources your_docs.yaml
```

That's it. Your documents are now AI-ready.

## What Can You Build?

- 💬 **Chat with your docs** - "What does our policy say about remote work?"
- 🔍 **Semantic search** - Find information by meaning, not just keywords
- 🤖 **Support bots** - Answer customer questions from your documentation
- 📚 **Knowledge bases** - Make years of documents instantly searchable
- 🎓 **Study assistants** - "Explain this concept from my textbook"

## Features That Matter

### 🎯 **It Just Works**
- Handles PDFs, Word docs, HTML, Markdown automatically
- Extracts content from even the messiest websites
- Cleans out ads, popups, and navigation junk

### 🧠 **Smart Chunking**
- Keeps paragraphs and sections together
- Preserves context with hierarchical titles
- Never cuts sentences in half

### 💰 **Cost Effective**
- Process thousands of pages for under $1
- Intelligent caching prevents reprocessing
- Batched API calls save time and money

### 🔒 **Production Ready**
- Detects and flags PII (emails, phone numbers, SSNs)
- Respects robots.txt and content licenses
- Full audit trail for compliance

## Real Examples

### Customer Support Knowledge Base
```yaml
# sources.yaml
- url: "https://docs.yourcompany.com/help/"
  title: "Help Center"
  tags:
    category: "support"
```
**Result**: AI that instantly answers customer questions

### Research Paper Analysis
```yaml
- url: "https://arxiv.org/pdf/2301.00001.pdf"
  title: "Machine Learning Paper"
  tags:
    category: "research"
```
**Result**: "What methods did the authors use?" - instant answers

### Internal Documentation
```yaml
- url: "file:///shared/policies/handbook.pdf"
  title: "Employee Handbook"
  tags:
    category: "internal"
```
**Result**: Employees can ask questions instead of searching PDFs

## The Output

DocuVec creates clean, structured data ready for any vector database:

```json
{
  "text": "Your perfectly chunked content...",
  "embedding": [0.123, -0.456, ...],
  "metadata": {
    "source": "document.pdf",
    "page": 42,
    "confidence": 0.95
  }
}
```

Each chunk includes:
- Clean, extracted text
- Vector embeddings for AI search
- Rich metadata for filtering
- Quality scores for ranking

## Supported Formats

| Format | Examples | Quality |
|--------|----------|---------|
| **PDF** | Reports, papers, ebooks | Excellent |
| **HTML** | Websites, documentation | Excellent |
| **Word** | .docx, .doc files | Excellent |
| **Markdown** | README files, wikis | Excellent |
| **PowerPoint** | Presentations | Good |
| **Excel** | Spreadsheets | Good |
| **Plain Text** | Log files, code | Good |

## Advanced Features

<details>
<summary><b>🔄 Incremental Updates</b></summary>

Only process what's changed:
```bash
python main.py --sources updated_docs.yaml
```
DocuVec automatically skips unchanged content using content hashing.
</details>

<details>
<summary><b>🎛️ Fine-Tuning</b></summary>

Customize chunking for your use case:
```bash
# .env
MAX_TOKENS=700      # Chunk size
OVERLAP_TOKENS=80   # Context overlap
```
</details>

<details>
<summary><b>🔍 Quality Control</b></summary>

DocuVec automatically:
- Filters out navigation, footers, and ads
- Detects and flags low-quality content
- Identifies duplicate and near-duplicate chunks
- Weights content by relevance (FAQs get boosted, footers get reduced)
</details>

## How It Works

```mermaid
graph LR
    A[Your Documents] --> B[DocuVec]
    B --> C[Clean Text]
    C --> D[Smart Chunks]
    D --> E[Embeddings]
    E --> F[Vector Database]
    F --> G[Your AI App]
```

1. **Fetch** - Gets your documents from any source
2. **Extract** - Pulls text from PDFs, HTML, etc.
3. **Clean** - Removes ads, navigation, and junk
4. **Chunk** - Splits intelligently by structure
5. **Embed** - Creates vectors via OpenAI
6. **Output** - Ready for your vector database

## Installation

### Requirements
- Python 3.8+
- OpenAI API key

### Setup
```bash
# Clone the repository
git clone https://github.com/yourusername/docuvec.git
cd docuvec

# Install dependencies
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env and add your OpenAI API key

# Run
python main.py
```

## Configuration

Create a `sources.yaml` file listing your documents:

```yaml
# Web pages
- url: "https://docs.example.com"
  title: "API Documentation"
  
# PDFs
- url: "https://example.com/whitepaper.pdf"
  title: "Technical Whitepaper"
  
# Local files
- url: "file:///path/to/document.docx"
  title: "Internal Document"
```

## FAQ

**Q: How much does it cost?**
A: Typically under $0.01 per 100 pages with OpenAI's API.

**Q: Can it handle messy websites?**
A: Yes! It uses multiple extraction methods and cleans aggressively.

**Q: What vector databases work with this?**
A: Any! Pinecone, Weaviate, Qdrant, pgvector, ChromaDB, etc.

**Q: Can I use local models instead of OpenAI?**
A: The architecture supports it, but currently uses OpenAI for best quality.

**Q: How do I update documents?**
A: Just run again - DocuVec only processes changed content.

## Get Started

1. **Have documents?** PDFs, websites, anything text-based
2. **Want AI search?** Make them searchable with meaning, not just keywords
3. **Use DocuVec** → Get production-ready vectors in minutes

```bash
python main.py --sources your_docs.yaml
```

## Contributing

We love contributions! DocuVec is MIT licensed and welcomes:
- New format support
- Better extraction methods
- Performance improvements
- Bug fixes

See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## License

MIT - Use it for anything!

---

<div align="center">

**Stop wrestling with documents. Start building AI.**

[Get Started](#quick-start) • [Examples](#real-examples) • [Documentation](CONTRIBUTING.md)

Built with ❤️ by developers tired of PDF parsing

</div>