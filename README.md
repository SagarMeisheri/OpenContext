# 🌐 OpenContext — Free News Search for AI Agents

> **An experiment to make news-based web search free for AI agents.**

OpenContext provides a **free web search API** for the news domain, combining RSS feeds (Google News + others) with **Elasticsearch caching** to deliver news intelligence without paying for expensive search APIs.

<p align="center">
  <img src="https://img.shields.io/badge/News%20Search-RSS%20Based-4285F4?style=for-the-badge" alt="RSS Based"/>
  <img src="https://img.shields.io/badge/Elasticsearch-BM25%20Cache-005571?style=for-the-badge&logo=elasticsearch" alt="Elasticsearch"/>
  <img src="https://img.shields.io/badge/Status-Experimental-orange?style=for-the-badge" alt="Experimental"/>
</p>

---

## 📋 Table of Contents

- [The Problem](#-the-problem-expensive-web-search-apis)
- [The Solution](#-opencontext-approach)
- [Limitations](#%EF%B8%8F-limitations)
- [Architecture](#%EF%B8%8F-architecture)
- [Quick Start](#-quick-start)
- [API Reference](#-api-endpoints)
- [Use Cases](#-use-cases)

---

## 💸 The Problem: Expensive Web Search APIs

Building AI agents with web search capabilities gets expensive fast.

### Web Search API Pricing Comparison

| Service | Free Tier | Pricing |
|---------|-----------|---------|
| **Exa** | $10 credits (one-time) | $5 per 1K requests (1-25 results)<br>$25 per 1K requests (26-100 results) |
| **Perplexity** | $5/month (Pro subscribers) | $0.20-$5 per 1M tokens (varies by model) |
| **Gemini Grounding** | 500-1,500 requests/day | $35 per 1K grounded prompts |
| **Brave Search** | 2,000 queries/month | $3 per 1K queries |
| **Tavily** | 1,000 credits/month | $0.008 per credit (1-2 credits per search) |
| **Grok (xAI)** | Limited free access | $5 per 1K web/X search calls |

> **Note**: All services charge separately for additional features like content extraction, tokens, etc. Costs compound quickly for agentic workflows making hundreds of searches daily.

---

## 💡 OpenContext Approach

### The Idea: RSS Feeds + Smart Caching

Instead of paying per search, OpenContext:

1. **Uses free RSS feeds** — Google News RSS and other public news sources (no API key required)
2. **Caches aggressively** — Elasticsearch stores generated Q&A pairs for instant reuse
3. **Calls LLM only on cache miss** — Minimizes paid API calls to ~20% of queries

### How It Works

```
User Query → Elasticsearch Cache (10-30ms)
                    ↓
            ┌───────┴───────┐
         Found?          Not Found?
            ↓                ↓
      Return cached     RSS Feed (free)
        results              ↓
                        LLM generates Q&A
                             ↓
                        Cache in ES
```

---

## ⚠️ Limitations

**This is a news-specific tool, not a general web search replacement.**

| ✅ What Works | ❌ What Doesn't |
|---------------|-----------------|
| Current news & events | General knowledge queries |
| Trending topics | Historical data |
| Breaking news Q&A | Non-news web content |
| Topic monitoring | Product searches, how-tos |

### Important Notes

- **Rate Limits**: Google News RSS may rate-limit heavy usage. The Elasticsearch cache helps reduce requests, but this isn't truly "unlimited."
- **Scope**: For searches beyond news (documentation, products, forums), you'll still need a paid API.
- **Headlines Only**: RSS provides headlines and metadata, not full article content.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    NEWS SEARCH FOR AI AGENTS                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   User Query (news-related)                                     │
│       │                                                         │
│       ▼                                                         │
│   ┌─────────────────────┐                                       │
│   │   Elasticsearch     │ ◄── BM25 Search (10-30ms)             │
│   │   (Q&A Cache)       │     Check for existing answers        │
│   └─────────┬───────────┘                                       │
│             │                                                   │
│       ┌─────┴─────┐                                             │
│       │           │                                             │
│    Found?      Not Found?                                       │
│       │           │                                             │
│       ▼           ▼                                             │
│   Return      ┌───────────────────┐                             │
│   Cached      │   RSS Feed(s)     │ ◄── Free, but rate-limited  │
│   Results     │ (Google News etc) │                             │
│               └─────────┬─────────┘                             │
│                         │                                       │
│                         ▼                                       │
│               ┌───────────────────┐                             │
│               │   LLM Processing  │ ◄── Generate Q&A pairs      │
│               └─────────┬─────────┘                             │
│                         │                                       │
│                         ▼                                       │
│               ┌───────────────────┐                             │
│               │  Index to ES      │ ◄── Cache for future        │
│               └───────────────────┘                             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| **📰 RSS News Fetching** | Google News RSS (default), extensible to any RSS source |
| **📦 Elasticsearch Cache** | BM25 ranking, instant retrieval (10-30ms), auto-indexing |
| **🤖 LLM Q&A Generation** | Transforms headlines into structured Q&A pairs |
| **🔄 Hybrid Strategy** | Search cache first, fallback to RSS + LLM on miss |

### Extensible RSS Sources

The architecture supports **any RSS feed**, not just Google News:

```python
# Current: Google News RSS
"https://news.google.com/rss/search?q={query}"

# Easy to add:
# - Reuters, BBC, AP News
# - TechCrunch, Hacker News
# - Industry-specific feeds
# - Regional news sources
```

Diversifying sources helps avoid rate limits and broadens coverage.

---

## 🚀 Quick Start

### 1. Setup

```bash
git clone https://github.com/yourusername/OpenContext.git
cd OpenContext
cp env.example .env
# Edit .env → add OPENROUTER_API_KEY
```

### 2. Start Elasticsearch

```bash
docker-compose up -d
```

### 3. Install Dependencies

```bash
uv sync          # recommended
# or: pip install -e .
```

### 4. Run

```bash
# Terminal 1: Backend
uvicorn main:app --reload

# Terminal 2: Chat UI
streamlit run app.py
```

**Access:**
- Chat UI → http://localhost:8501
- API Docs → http://localhost:8000/docs

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/search` | Search Q&As with LLM fallback |
| `POST` | `/generate` | Generate Q&As from news topic |
| `POST` | `/index` | Manually index a Q&A pair |
| `POST` | `/index/bulk` | Bulk index multiple Q&As |
| `GET` | `/stats` | Elasticsearch index stats |
| `GET` | `/health` | API health check |
| `DELETE` | `/index` | Clear all Q&As |

### Example

```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "latest AI news", "top_k": 10, "fallback_to_llm": true}'
```

---

## 📊 Cost Comparison

| Scenario | Paid Search API | OpenContext |
|----------|-----------------|-------------|
| First query on topic | API call cost | RSS (free) + LLM call |
| Repeated queries | API call cost each time | **Cached — free** |
| Non-news queries | Works | ❌ Not supported |

**Best for**: News-heavy use cases with repeating queries (topic monitoring, news chatbots).

---

## 🎯 Use Cases

### ✅ Good Fit

- **News Monitoring Agents** — Track topics, generate summaries
- **News Chatbots** — Answer questions about current events
- **Research Pipelines** — Build news-based knowledge graphs
- **Alert Systems** — Monitor for specific news triggers

### ❌ Not Suitable

- General web search (use Exa, Perplexity, Brave, etc.)
- Documentation/API reference lookup
- Product or service searches
- Historical research beyond news

---

## 🧩 LangChain Integration

```python
from news_service import create_news_tool

# Create tool for news-related queries
news_tool = create_news_tool()
tools = [news_tool]
```

---

## 🛠 Tech Stack

| Component | Technology |
|-----------|------------|
| News Source | RSS Feeds (Google News, etc.) |
| Cache | Elasticsearch (BM25) |
| Backend | FastAPI |
| Frontend | Streamlit |
| LLM | OpenRouter |

---

## 🔧 Configuration

```bash
# .env file

# Required
OPENROUTER_API_KEY=your_key_here

# Optional
ELASTICSEARCH_HOST=http://localhost:9200
ELASTICSEARCH_INDEX=news-qa
LLM_MODEL=google/gemini-2.0-flash-001
```

---

## 📋 Requirements

- Python 3.10+
- Docker (for Elasticsearch)
- OpenRouter API key

---

## 🔮 Future Ideas

- [ ] Add more RSS sources (Reuters, BBC, AP)
- [ ] Rate limit handling with source rotation
- [ ] Semantic search with embeddings
- [ ] Full article extraction

---

## 📝 License

MIT License

---

<p align="center">
  <em>An experiment to reduce web search costs for news-focused AI agents.</em><br/>
  <strong>📰 RSS Feeds • 📦 Elasticsearch Cache • 🤖 LLM Q&A</strong>
</p>
