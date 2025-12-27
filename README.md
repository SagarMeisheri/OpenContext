# 🌐 OpenContext — Free News Search for AI Agents

> **An experiment to make news-based web search free for AI agents.**

OpenContext is an attempt to build a **free news search API** by combining RSS feeds (Google News + others) with **Elasticsearch indexing** and **LLM-powered Q&A synthesis** — avoiding expensive search API subscriptions.

<p align="center">
  <img src="https://img.shields.io/badge/News%20Search-RSS%20Based-4285F4?style=for-the-badge" alt="RSS Based"/>
  <img src="https://img.shields.io/badge/Elasticsearch-Indexed-005571?style=for-the-badge&logo=elasticsearch" alt="Elasticsearch"/>
  <img src="https://img.shields.io/badge/Status-MVP-orange?style=for-the-badge" alt="MVP"/>
</p>

---

## 📋 Table of Contents

- [The Problem](#-the-problem-expensive-web-search-apis)
- [The Solution](#-opencontext-approach)
- [Limitations](#%EF%B8%8F-limitations)
- [Architecture](#%EF%B8%8F-architecture)
- [Quick Start](#-quick-start)
- [API Reference](#-api-endpoints)
- [Contributing](#-contributing--collaboration)

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

> **Note**: Costs compound quickly for agentic workflows making hundreds of searches daily.

---

## 💡 OpenContext Approach

### RSS Search + LLM Q&A Synthesis

Instead of paying per search, OpenContext:

1. **Fetches news via free RSS feeds** — Google News and other public sources (no API key)
2. **Synthesizes Q&A pairs with LLM** — Transforms headlines into structured answers
3. **Indexes everything in Elasticsearch** — Fast retrieval for future queries, scales to millions of entries

### How It Works

```
User Query → Check Elasticsearch Index
                      ↓
              ┌───────┴───────┐
           Found?          Not Found?
              ↓                ↓
        Return indexed    Fetch from RSS
          Q&A pairs            ↓
                         LLM synthesizes Q&A
                               ↓
                         Index in Elasticsearch
                               ↓
                         Return to user
```

**Key insight**: Elasticsearch excels at querying indexed news data and can scale to millions of entries. Once a topic is indexed, subsequent queries are instant.

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

- **Rate Limits**: Google News RSS may rate-limit heavy usage. Elasticsearch indexing helps reduce requests, but this isn't truly "unlimited."
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
│   │   Elasticsearch     │ ◄── Query indexed Q&A pairs           │
│   │   (News Index)      │     Fast retrieval, scales to millions│
│   └─────────┬───────────┘                                       │
│             │                                                   │
│       ┌─────┴─────┐                                             │
│       │           │                                             │
│    Found?      Not Found?                                       │
│       │           │                                             │
│       ▼           ▼                                             │
│   Return      ┌───────────────────┐                             │
│   Indexed     │   RSS Feed(s)     │ ◄── Free news fetching      │
│   Results     │ (Google News etc) │                             │
│               └─────────┬─────────┘                             │
│                         │                                       │
│                         ▼                                       │
│               ┌───────────────────┐                             │
│               │   LLM Synthesis   │ ◄── Generate Q&A pairs      │
│               └─────────┬─────────┘                             │
│                         │                                       │
│                         ▼                                       │
│               ┌───────────────────┐                             │
│               │  Index to ES      │ ◄── Store for future queries│
│               └───────────────────┘                             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| **📰 RSS News Fetching** | Google News RSS (default), extensible to any RSS source |
| **📦 Elasticsearch Index** | Fast querying of indexed news, scales to millions of entries |
| **🤖 LLM Q&A Synthesis** | Transforms headlines into structured Q&A pairs |
| **🔄 Smart Caching** | Index first, RSS + LLM only when needed |

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
| `POST` | `/search` | Search indexed Q&As, fetches from RSS + synthesizes if not found |
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
  -d '{"query": "latest AI news", "top_k": 10}'
```

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
| Index & Search | Elasticsearch |
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

## 🤝 Contributing & Collaboration

**This is an MVP and we're looking for collaborators!**

OpenContext is an early-stage experiment. To grow beyond MVP, we need help with:

### 🔧 Technical Contributions

- [ ] Add more RSS feed sources (Reuters, BBC, AP, etc.)
- [ ] Implement rate limit handling with source rotation
- [ ] Add semantic/vector search alongside keyword search
- [ ] Full article content extraction
- [ ] Better Q&A synthesis prompts

### 🏗️ Infrastructure

This project needs infrastructure support to scale:

- **Elasticsearch hosting** — Currently runs locally via Docker; production deployment needs hosted ES (Elastic Cloud, OpenSearch, etc.)
- **CI/CD pipeline** — Automated testing and deployment
- **Demo instance** — Hosted version for people to try

### 💡 Ideas & Feedback

- Open an [Issue](https://github.com/yourusername/OpenContext/issues) with suggestions
- Share use cases we haven't considered
- Report bugs or limitations you encounter

### 📬 Get in Touch

Interested in collaborating or sponsoring infrastructure?

- Open a GitHub Issue or Discussion
- Reach out via [Twitter/X](https://twitter.com/yourhandle) or [Email](mailto:your@email.com)

> **Note**: This is a passion project exploring whether free RSS feeds can meaningfully reduce search API costs for news-focused AI agents. All contributions welcome — code, ideas, or just feedback!

---

## 🔮 Roadmap

| Phase | Status | Description |
|-------|--------|-------------|
| MVP | ✅ Current | Local Elasticsearch, Google News RSS, basic Q&A |
| v0.2 | 🔜 Planned | Multiple RSS sources, rate limit handling |
| v0.3 | 💭 Future | Vector search, article extraction |
| v1.0 | 🎯 Goal | Production-ready with hosted demo |

---

## 📝 License

MIT License — use freely, contribute back if you can!

---

<p align="center">
  <em>An experiment to reduce web search costs for news-focused AI agents.</em><br/>
  <strong>📰 RSS Feeds • 📦 Elasticsearch Index • 🤖 LLM Q&A Synthesis</strong>
</p>
