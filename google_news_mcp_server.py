
from mcp.server.fastmcp import FastMCP
from typing import Optional
import json
from urllib.parse import quote
import feedparser
import requests
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

# Configuration
DEFAULT_DAYS = 7
DEFAULT_MAX_RESULTS = 10
REQUEST_TIMEOUT = 10
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "nvidia/nemotron-3-nano-30b-a3b:free")

# Initialize MCP server
mcp = FastMCP("Google News Search")


# ==============================================================================
# Google News Client
# ==============================================================================

class GoogleNewsClient:
    """Client for fetching Google News RSS feeds"""
    
    def __init__(self):
        self.base_url = "https://news.google.com/rss/search"
        self.session = requests.Session()
    
    def fetch_headlines(
        self,
        query: str,
        days: int = DEFAULT_DAYS,
        max_results: int = DEFAULT_MAX_RESULTS
    ) -> dict:
        """
        Fetch news headlines from Google News RSS.
        
        Args:
            query: Search terms or topic
            days: Number of days to look back
            max_results: Maximum number of articles to return
            
        Returns:
            Dictionary with articles and metadata
        """
        try:
            # Construct Google News RSS URL
            rss_url = f"{self.base_url}?q={quote(query)}+when:{days}d&hl=en-US&gl=US&ceid=US:en"
            
            # Fetch RSS feed
            response = self.session.get(rss_url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            
            # Parse the RSS feed
            feed = feedparser.parse(response.content)
            
            total_articles = len(feed.entries)
            
            if total_articles == 0:
                return {
                    "success": True,
                    "query": query,
                    "total_count": 0,
                    "articles": [],
                    "message": f"No news found for '{query}' in the last {days} day(s)."
                }
            
            # Extract articles
            articles = []
            for item in feed.entries[:max_results]:
                source = (
                    item.source.title
                    if hasattr(item, 'source') and hasattr(item.source, 'title')
                    else "Unknown"
                )
                # link = item.link if hasattr(item, 'link') else ""
                
                articles.append({
                    "title": item.title,
                    "source": source,
                    "published": item.published,
                    # "link": link
                })
            
            return {
                "success": True,
                "query": query,
                "total_count": total_articles,
                "articles": articles,
                "timespan": f"{days} days"
            }
            
        except requests.exceptions.Timeout:
            raise Exception(f"Request timed out while fetching news for '{query}'")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Error fetching news for '{query}': {str(e)}")
        except Exception as e:
            raise Exception(f"Unexpected error: {str(e)}")


# Initialize client
client = GoogleNewsClient()


# ==============================================================================
# LLM Service for News Context
# ==============================================================================

def get_llm(temperature: float = 0.3) -> ChatOpenAI:
    """
    Get a configured LLM instance.
    
    Args:
        temperature: Sampling temperature (0-1)
        
    Returns:
        Configured ChatOpenAI instance
    """
    return ChatOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
        model=OPENROUTER_MODEL,
        temperature=temperature
    )


# ==============================================================================
# MCP Tool
# ==============================================================================

@mcp.tool()
def get_news_headlines(
    query: str,
    days: int = 7,
    max_results: int = 50
) -> str:
    """
    Fetch Google News headlines for a query 
    
    This tool searches Google News for recent articles matching the query and
    returns headlines with sources and publication dates. The results provide
    news context about the topic, including what outlets are covering it and
    when stories were published.
    
    Args:
        query: Search terms or topic to find news about (e.g., "artificial intelligence",
               "climate change", "tech earnings")
        days: Number of days to look back for news (1-30, default 7)
        max_results: Maximum number of headlines to return (1-50, default 10)
    
    Returns:
        JSON string with:
        - List of headlines with titles, sources, and publication dates
        - Total count of articles found
    
    Examples:
        - get_news_headlines("Tesla stock", days=3, max_results=5)
        - get_news_headlines("Olympics 2024", days=1, max_results=15)
        - get_news_headlines("artificial intelligence regulation")
    """
    try:
        # Validate parameters
        days = max(1, min(days, 30))
        max_results = max(1, min(max_results, 50))
        
        # Fetch headlines
        result = client.fetch_headlines(
            query=query,
            days=days,
            max_results=max_results
        )
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "query": query
        }, indent=2)


# ==============================================================================
# Main Entry Point
# ==============================================================================

if __name__ == "__main__":
    # Run the MCP server using stdio transport
    mcp.run(transport="stdio")

