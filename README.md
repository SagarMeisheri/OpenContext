# 🌐 OpenContext — Free News Search API for AI Agents

> **Building a public, free news search API powered by official sources and Elasticsearch.**

<p align="center">
  <img src="https://img.shields.io/badge/News%20Search-Official%20Sources-4285F4?style=for-the-badge" alt="Official Sources"/>
  <img src="https://img.shields.io/badge/Elasticsearch-Indexed-005571?style=for-the-badge&logo=elasticsearch" alt="Elasticsearch"/>
  <img src="https://img.shields.io/badge/Status-MVP-orange?style=for-the-badge" alt="MVP"/>
</p>

---

## 📋 Table of Contents

- [What is OpenContext?](#-what-is-opencontext)
- [Why? (The Problem)](#-why-web-search-apis-are-expensive)
- [How It Works](#-how-it-works)
- [Limitations](#%EF%B8%8F-limitations)
- [Copyright & Legal Considerations](#%EF%B8%8F-copyright--legal-considerations)
- [Current Status](#-current-status)
- [Try It Locally](#-try-it-locally)
- [API Reference](#-api-reference)
- [Contributing](#-contributing)
- [Roadmap](#-roadmap)
- [Technical Details](#-technical-details)

---

## 🎯 What is OpenContext?

OpenContext is an attempt to create a **free, public news search API** that AI agents can use without paying for expensive search subscriptions.

**The idea:**
- Build a shared Elasticsearch index with news Q&A data
- Anyone can query it for free
- Data comes from **copyright-safe official sources** (government releases, company press releases) + Open Source LLM synthesis
- The more the community uses it, the better the index becomes

> ⚠️ **Note**: Current MVP uses Google News for testing only. Production requires official sources to avoid copyright issues.

```
┌────────────────────────────────────────────────────────────────┐
│                                                                │
│   🌐 Public OpenContext API (the goal)                         │
│                                                                │
│   ┌──────────────────────────────────────────┐                 │
│   │     Shared Elasticsearch Index           │                 │
│   │     • Millions of news Q&A pairs         │                 │
│   │     • Continuously updated               │                 │
│   │     • Free to query for everyone         │                 │
│   └──────────────────────────────────────────┘                 │
│                         ▲                                      │
│         ┌───────────────┼───────────────┐                      │
│         ▼               ▼               ▼                      │
│      Your AI        Community       Researchers                │
│      Agent          Projects        & Developers               │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

---

## 💸 Why? Web Search APIs Are Expensive

| Service | Free Tier | Pricing |
|---------|-----------|---------|
| **Exa** | $10 credits (one-time) | $5-25 per 1K requests |
| **Perplexity** | $5/month (Pro only) | $0.20-$5 per 1M tokens |
| **Gemini Grounding** | 500-1,500/day | $35 per 1K prompts |
| **Brave Search** | 2,000/month | $3 per 1K queries |
| **Tavily** | 1,000 credits/month | $0.008 per credit |

For AI agents making hundreds of searches daily, costs add up fast.

**OpenContext approach**: Instead of everyone paying individually, build a shared index that everyone queries for free.

---

## 🔧 How It Works

```
User Query → Elasticsearch Index
                    ↓
            ┌───────┴───────┐
         Found?          Not Found?
            ↓                ↓
      Return from       Fetch from Official Sources
        index           (Gov/Company Press Releases)
                             ↓
                        LLM synthesizes
                          Q&A pairs
                             ↓
                        Add to index
                             ↓
                        Return to user
```

**Key components:**
1. **Official Sources** — Copyright-safe data from global government releases and company press releases *(MVP uses Google News for testing only)*
2. **LLM Synthesis** — Transforms headlines into structured Q&A pairs
3. **Elasticsearch** — Indexes everything for fast retrieval, scales to millions of entries

---

## ⚠️ Limitations

**This is news-specific, not a general web search replacement.**

| ✅ Works | ❌ Doesn't Work |
|----------|-----------------|
| Current news & events | General knowledge |
| Trending topics | Historical data |
| Breaking news | Product searches |
| Topic monitoring | Documentation lookup |

**Also note:**
- **Copyright concerns**: Google News is MVP-only. Production must use official sources (government/company releases)
- Official sources provide headlines/summaries, not full article content
- This is an MVP — public hosted index not yet available

---

## ⚖️ Copyright & Legal Considerations

**Important: OpenContext must use copyright-safe sources for legal redistribution.**

### Why Official Sources Only?

**ALL news RSS sources are copyrighted** — including Reuters, BBC, AP, Google News, and any news organization. Even when content is available via RSS feeds, it remains copyrighted and cannot be legally indexed/redistributed in an open-source project without permission.

### Copyright-Safe Sources

✅ **Government Press Releases (Global)**
- **India**: PIB (pib.gov.in), ministries, RBI statements
- **United States**: SEC filings, White House, NASA, CDC/FDA
- **United Kingdom**: GOV.UK press releases
- **European Union**: europa.eu official announcements
- **Canada**: canada.ca news releases
- **Australia**: minister.gov.au releases
- **International**: UN, WHO, IMF, World Bank statements

✅ **Company Press Releases (Worldwide)**
- Investor relations announcements
- Official company statements
- Corporate RSS feeds from IR departments

### Current MVP Status

⚠️ **Google News is used for MVP demonstration ONLY**

The current implementation uses Google News for testing purposes, but this poses copyright risks for production use. Any production deployment or public API must transition to official sources only.

### Why This Matters

Official sources are:
- Explicitly designed for public redistribution
- Copyright-safe and legally republishable
- Authoritative and trustworthy
- Free from legal liability
- Available globally from governments and companies worldwide

---

## 📊 Current Status

| Component | Status |
|-----------|--------|
| Core API | ✅ Built |
| Local Elasticsearch | ✅ Works (Docker) |
| Public hosted index | 🔜 Needs infrastructure |
| Quality news data | 🔜 Needs contributions |

---

## 🚀 Try It Locally

### 1. Setup

```bash
git clone https://github.com/yourusername/OpenContext.git
cd OpenContext
cp env.example .env
# Add OPENROUTER_API_KEY to .env
```

### 2. Start Elasticsearch

```bash
docker-compose up -d
```

### 3. Install & Run

```bash
uv sync                      # install dependencies
uvicorn main:app --reload    # start API (terminal 1)
streamlit run app.py         # start UI (terminal 2)
```

**Access:**
- Chat UI → http://localhost:8501
- API Docs → http://localhost:8000/docs

---

## 🔌 API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/search` | Search news Q&As (fetches from RSS if not indexed) |
| `POST` | `/generate` | Generate Q&As for a topic |
| `POST` | `/index` | Add a Q&A pair |
| `POST` | `/index/bulk` | Bulk add Q&A pairs |
| `GET` | `/stats` | Index statistics |
| `GET` | `/health` | Health check |
| `DELETE` | `/index` | Clear index |

### Example

```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "AI regulations"}'
```


---

## 🤝 Contributing

**This MVP needs help to become a real public API.**

### What We Need

| Area | Help Wanted |
|------|-------------|
| **Infrastructure** | Hosted Elasticsearch (Elastic Cloud, OpenSearch, etc.) |
| **Official Sources** | Add global government press releases, company IR feeds from any country (NOT Reuters/BBC/AP — copyrighted!) |
| **Code** | Rate limiting, vector search, article extraction |
| **Testing** | Try it out, report issues, suggest improvements |

### Get Involved

- ⭐ Star the repo
- 🐛 Open an [Issue](https://github.com/yourusername/OpenContext/issues)
- 💬 Start a [Discussion](https://github.com/yourusername/OpenContext/discussions)
- 🔧 Submit a PR

> This is a passion project exploring whether official sources + shared indexing can reduce search costs for AI agents. All help welcome!

---

## 🔮 Roadmap

| Phase | Status | Goal |
|-------|--------|------|
| MVP | ✅ Current | Local ES, **Google News (MVP only)**, basic Q&A |
| v0.2 | 🔜 Next | **Transition to official sources** (press releases, govt feeds), rate limiting |
| v0.3 | 💭 Future | Vector search, article extraction |
| v1.0 | 🎯 Goal | **Public hosted API** with copyright-safe sources |

---

## 🛠 Technical Details

<details>
<summary>Tech Stack</summary>

| Component | Technology |
|-----------|------------|
| News Source | Official Sources (Gov/Company) |
| Index | Elasticsearch |
| Backend | FastAPI |
| Frontend | Streamlit |
| LLM | OpenRouter |

</details>

<details>
<summary>Configuration</summary>

```bash
# .env file
OPENROUTER_API_KEY=your_key_here

# Optional
ELASTICSEARCH_HOST=http://localhost:9200
ELASTICSEARCH_INDEX=news-qa
LLM_MODEL=google/gemini-2.0-flash-001
```

</details>

<details>
<summary>Requirements</summary>

- Python 3.10+
- Docker
- OpenRouter API key

</details>

<details>
<summary>News Sources (Copyright-Safe)</summary>

```python
# Copyright-Safe Sources (ONLY these for production):
# 
# Global Government Sources:
# - India: pib.gov.in (Press Information Bureau), RBI, ministries
# - United States: whitehouse.gov, sec.gov, nasa.gov, CDC, FDA
# - United Kingdom: gov.uk press releases
# - European Union: europa.eu announcements
# - Canada: canada.ca news releases
# - Australia: minister.gov.au
# - International: UN, WHO, IMF, World Bank
#
# Company Sources (Worldwide):
# - Company investor relations (official IR RSS feeds)
# - Corporate press releases

# MVP Testing Only (COPYRIGHT RISK - Do NOT use in production):
# - Google News (currently used for MVP demonstration only)
# - Reuters, BBC, AP, and other news organizations (all copyrighted)
```

**Note**: Any production deployment must use official sources only to avoid copyright infringement.

</details>

---

## 📝 License

MIT — Use freely, contribute back if you can!

---

<p align="center">
  <strong>🏛️ Official Sources → 📦 Shared Index → 🤖 Free News Search for AI</strong><br/>
  <em>An experiment in making agentic web search accessible with copyright-safe sources.</em>
</p>
