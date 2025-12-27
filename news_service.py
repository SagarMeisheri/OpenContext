"""
Google News RSS fetching service.

Fetches news headlines from Google News RSS feed for a given topic.
"""

from dataclasses import dataclass
from urllib.parse import quote

import feedparser
import requests


@dataclass
class NewsArticle:
    """Represents a single news article."""
    title: str
    source: str
    published: str
    link: str = ""


@dataclass
class NewsResult:
    """Result from fetching news."""
    success: bool
    articles: list[NewsArticle]
    total_count: int
    query: str
    error: str = ""


def fetch_google_news(query: str, days: int = 7, max_results: int = 10) -> NewsResult:
    """
    Fetch news headlines from Google News RSS.

    Args:
        query: The search topic or keywords
        days: Number of days to look back for news
        max_results: Maximum number of articles to return

    Returns:
        NewsResult with list of articles or error
    """
    try:
        # Construct Google News RSS URL
        rss_url = f"https://news.google.com/rss/search?q={quote(query)}+when:{days}d&hl=en-US&gl=US&ceid=US:en"

        # Fetch RSS feed with timeout
        response = requests.get(rss_url, timeout=10)
        response.raise_for_status()

        # Parse the RSS feed
        feed = feedparser.parse(response.content)

        total_articles = len(feed.entries)

        if total_articles == 0:
            return NewsResult(
                success=True,
                articles=[],
                total_count=0,
                query=query,
                error=f"No news found for '{query}' in the last {days} day(s)."
            )

        # Extract articles
        articles = []
        for item in feed.entries[:max_results]:
            source = (
                item.source.title
                if hasattr(item, 'source') and hasattr(item.source, 'title')
                else "Unknown"
            )
            link = item.link if hasattr(item, 'link') else ""

            articles.append(NewsArticle(
                title=item.title,
                source=source,
                published=item.published,
                link=link
            ))

        return NewsResult(
            success=True,
            articles=articles,
            total_count=total_articles,
            query=query
        )

    except requests.exceptions.Timeout:
        return NewsResult(
            success=False,
            articles=[],
            total_count=0,
            query=query,
            error=f"Request timed out while fetching news for '{query}'"
        )
    except requests.exceptions.RequestException as e:
        return NewsResult(
            success=False,
            articles=[],
            total_count=0,
            query=query,
            error=f"Error fetching news for '{query}': {str(e)}"
        )
    except Exception as e:
        return NewsResult(
            success=False,
            articles=[],
            total_count=0,
            query=query,
            error=f"Unexpected error: {str(e)}"
        )


def format_news_for_llm(result: NewsResult) -> str:
    """
    Format news results as a string for LLM consumption.

    Args:
        result: NewsResult from fetch_google_news

    Returns:
        Formatted string with headlines
    """
    if not result.success:
        return f"Error: {result.error}"

    if not result.articles:
        return f"No news found for '{result.query}'."

    lines = [
        f"Found {result.total_count} articles for '{result.query}' "
        f"(showing top {len(result.articles)}):\n"
    ]

    for i, article in enumerate(result.articles, 1):
        lines.append(
            f"{i}. {article.title}\n"
            f"   Source: {article.source}\n"
            f"   Published: {article.published}"
        )

    return "\n\n".join(lines)
