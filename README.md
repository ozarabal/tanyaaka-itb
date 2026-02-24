# TanyaAka ITB

**AI-powered Academic Regulation Chatbot** built with a Retrieval-Augmented Generation (RAG) pipeline to help ITB students instantly find answers about academic policies and regulations.


## Overview

TanyaAka ITB is a full-stack RAG chatbot that ingests ITB's academic regulation PDF documents, processes them into semantically searchable chunks, and provides accurate, citation-backed answers through a conversational interface. The system uses a custom academic document processor that understands the hierarchical structure of Indonesian legal/academic documents (Pasal, Ayat).

## Architecture

```
┌─────────────────┐       ┌──────────────────────────────────────────────┐
│                 │       │  Backend (FastAPI)                          │
│  React/TS       │       │                                            │
│  Frontend       │ REST  │  ┌────────────┐    ┌─────────────────────┐ │
│                 ├──────►│  │ Chat API   ├───►│ RAG Chain           │ │
│  - Chat UI      │       │  │ /api/v1    │    │                     │ │
│  - Source Cards │◄──────┤  └────────────┘    │ Query → Retriever   │ │
│  - Suggested Q  │       │                    │      → LLM          │ │
│                 │       │  ┌────────────┐    │      → Response     │ │
└─────────────────┘       │  │ Document   │    └────────┬────────────┘ │
                          │  │ Ingestion  │             │              │
                          │  │ Pipeline   │    ┌────────▼────────────┐ │
                          │  └─────┬──────┘    │ ChromaDB            │ │
                          │        │           │ Vector Store        │ │
                          │        ▼           └─────────────────────┘ │
                          │  PDF → Chunk →                             │
                          │  Embed → Store                             │
                          └──────────────────────────────────────────────┘
                                       │
                                       ▼
                              ┌─────────────────┐
                              │ OpenAI API       │
                              │ - Embeddings     │
                              │ - GPT-4o-mini    │
                              └─────────────────┘
```

## Tech Stack

### Backend
| Component | Technology |
|---|---|
| Framework | **FastAPI** with async request handling |
| RAG Orchestration | **LangChain** |
| Vector Database | **ChromaDB** (persistent, embedded) |
| Embeddings | OpenAI `text-embedding-3-small` |
| LLM | OpenAI `gpt-4o-mini` |
| Document Processing | PyPDF2 + custom academic chunker |
| Data Validation | **Pydantic v2** |
| Logging | **structlog** (structured JSON logging) |
| Testing | **pytest** + pytest-asyncio + httpx |

### Frontend
| Component | Technology |
|---|---|
| Framework | React 19 + TypeScript |
| Build Tool | Vite |
| Styling | Tailwind CSS |

## Backend Deep Dive

### RAG Pipeline

The core retrieval pipeline follows a multi-stage process:

1. **Document Ingestion** - PDFs are loaded, pages are filtered (skipping TOC/cover), and text is extracted
2. **Academic Chunking** - A custom `DocumentProcessor` applies a 3-step chunking strategy (see below) to produce one chunk per Ayat with full Pasal context
3. **Embedding & Storage** - Chunks are embedded via OpenAI's `text-embedding-3-small` model and stored in ChromaDB with rich metadata (pasal name, ayat number, page, source file)
4. **Semantic Retrieval** - User queries are embedded and matched against stored vectors using cosine similarity (top-K=7)
5. **Augmented Generation** - Retrieved context is formatted with source citations and sent to GPT-4o-mini with a specialized system prompt

### Custom Document Processor

Unlike generic text splitters, the processor is aware of the hierarchical structure (Pasal → Ayat) of Indonesian academic regulation documents. Chunking happens in three passes:

**Step 1 — Split by page**
The PDF is loaded page-by-page. Cover pages and table-of-contents pages are discarded, and repeating headers/footers are stripped from every remaining page.

**Step 2 — Merge continuation pages**
Because an Ayat (verse/clause) can span a page boundary, every page whose first non-empty line is a mid-sentence continuation (not a Pasal declaration, not an Ayat number, not an all-caps chapter header) is merged into the preceding page. This guarantees that no Ayat is split across two separate chunks.

**Step 3 — Split into per-Ayat chunks with Pasal context**
Each merged page block is then split on Ayat markers `(1)`, `(2)`, … producing one `Document` per Ayat. Before the chunk is converted to a numerical vector, the detected `pasal_context` (e.g. `"Pasal 14 Rencana Studi Semester"`) is attached to its metadata and carried forward to Ayat that appear on pages without an explicit Pasal header.

```
PDF pages
   │
   ▼  Pass 1 – filter & clean
[page_3, page_4, page_5, …]
   │
   ▼  Pass 2 – merge continuation pages
[page_3, page_4+5_merged, …]        ← no Ayat is split across pages
   │
   ▼  Pass 3 – split into Ayat chunks
[{Pasal 7, Ayat 1}, {Pasal 7, Ayat 2}, {Pasal 8, Ayat None}, …]
   │
   ▼  Embed (text-embedding-3-small)
ChromaDB
```

Chunk metadata: `pasal_context` · `ayat` · `page` · `source_filename` · `merged_pages`

### API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/chat` | Send a question, receive RAG-powered answer with sources |
| `POST` | `/api/v1/documents/ingest` | Trigger PDF ingestion pipeline |
| `GET` | `/api/v1/documents` | List ingested documents and chunk counts |
| `GET` | `/health` | Health check with vector store status |

Auto-generated API documentation available at `/docs` (Swagger UI) and `/redoc`.

### Request/Response Schema

```json
// POST /api/v1/chat
// Request
{
  "question": "Apa syarat kelulusan di ITB?"
}

// Response
{
  "answer": "Berdasarkan peraturan akademik ITB...",
  "sources": [
    {
      "document": "Buku_Peraturan_Akademik_2024.pdf",
      "page": 42,
      "content_snippet": "Pasal 58 tentang Kelulusan..."
    }
  ],
  "model": "gpt-4o-mini"
}
```

### Testing

API tests cover health checks, chat with empty vector store (503 handling), input validation (422 on empty questions), and document listing. Tests use `httpx.AsyncClient` with `ASGITransport` for async FastAPI testing without a running server.

```bash
cd backend
pytest
```

## Getting Started

### Prerequisites
- Python 3.11+
- Node.js 18+
- OpenAI API key

### Backend Setup

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# Ingest documents
python -m scripts.ingest

# Start server
uvicorn app.main:app --reload
# API available at http://localhost:8000
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
# App available at http://localhost:5173
```

## Project Structure

```
backend/
├── app/
│   ├── api/routes/          # FastAPI route handlers
│   │   ├── chat.py          # Chat endpoint
│   │   ├── documents.py     # Document ingestion
│   │   └── health.py        # Health check
│   ├── core/
│   │   ├── config.py        # Pydantic Settings configuration
│   │   └── logging.py       # Structured logging setup
│   ├── models/
│   │   └── schemas.py       # Pydantic request/response schemas
│   ├── services/
│   │   ├── rag_chain.py     # RAG query pipeline
│   │   ├── vector_store.py  # ChromaDB interface
│   │   └── document_processor.py  # PDF processing & chunking
│   └── main.py              # FastAPI app initialization
├── scripts/
│   └── ingest.py            # CLI document ingestion tool
├── tests/
│   ├── conftest.py          # pytest fixtures
│   └── test_api.py          # API integration tests
└── data/pdfs/               # Source PDF documents

frontend/
├── src/
│   ├── components/          # React UI components
│   ├── api.ts               # API client
│   ├── types.ts             # TypeScript interfaces
│   └── App.tsx              # Root component
└── vite.config.ts           # Vite config with API proxy
```
