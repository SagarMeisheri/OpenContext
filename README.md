# OpenContext - News Q&A API

A FastAPI REST API for searching and generating Q&A pairs from news using Elasticsearch and LLM.

## Features

- **BM25 Search**: Fast keyword search with relevance scoring (10-30ms)
- **LLM Fallback**: Auto-generates Q&A pairs from Google News when no matches found
- **Hybrid Approach**: Search first, generate only when needed

## Quick Start

### 1. Setup Environment

```bash
cp env.example .env
# Edit .env and add your OPENROUTER_API_KEY
```

### 2. Start Elasticsearch

```bash
docker-compose up -d
```

### 3. Install Dependencies

```bash
# With conda (activate your env first)
uv pip install -e .

# Or with uv managed venv
uv sync
```

### 4. Run Both Services

```bash
# Terminal 1: Start FastAPI backend
uvicorn main:app --reload

# Terminal 2: Start Streamlit chat UI
streamlit run app.py
```

- API docs: http://localhost:8000/docs
- Chat UI: http://localhost:8501

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/search` | Search Q&As with LLM fallback |
| `POST` | `/generate` | Generate Q&As from news topic |
| `POST` | `/index` | Index a single Q&A |
| `GET` | `/stats` | Index statistics |
| `DELETE` | `/index` | Clear all Q&As |

## Example Usage

```bash
# Search for Q&As
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "stock market crash", "top_k": 10}'

# Generate Q&As from news
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"topic": "artificial intelligence", "num_pairs": 5}'
```

## Architecture

```
User Query → FastAPI → Elasticsearch (BM25 search)
                ↓ (no matches)
              LLM → Google News → Generate Q&As → Store in ES
```

## Requirements

- Python 3.10+
- Docker (for Elasticsearch)
- OpenRouter API key

