
from mcp.server.fastmcp import FastMCP
from typing import Optional
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
# MCP Tools
# ==============================================================================

@mcp.tool()
def search_google_news(
    query: str,
    days: int = 7
) -> str:
    """
    Search Google News and get AI-synthesized insights about any topic.
    
    This universal tool works for any query - simple or complex. It fetches recent
    news articles from Google News and uses AI to synthesize key insights, themes,
    and important information from the articles.
    
    For complex topics, agents can call this tool multiple times in parallel with
    different focused queries, then combine the results.
    
    Args:
        query: Any search query - can be simple keywords or a complex question
               Examples: "Tesla stock", "AI regulation", "climate change policy"
        days: Number of days to look back for news (1-30, default 7)
    
    Returns:
        String with AI-synthesized answer and source metadata
    
    Examples:
        Simple query:
            search_google_news("Tesla earnings")
        
        Complex topic (agent can parallelize):
            search_google_news("AI regulation")
            search_google_news("tech policy")
            search_google_news("AI ethics")
    """
    try:
        # Validate parameters
        days = max(1, min(days, 30))
        max_results = 20  # Fetch reasonable amount for synthesis
        
        # Fetch headlines from Google News
        result = client.fetch_headlines(
            query=query,
            days=days,
            max_results=max_results
        )
        
        # Check if any articles were found
        if not result.get("success") or not result.get("articles"):
            return f"No recent news found for '{query}' in the last {days} days."
        
        articles = result["articles"]
        
        # Format articles for LLM
        articles_text = "\n\n".join([
            f"Title: {article['title']}\n"
            f"Source: {article.get('source', 'Unknown')}\n"
            f"Date: {article.get('published', 'Unknown')}"
            for article in articles[:15]  # Limit to top 15 for context window
        ])
        
        # Create synthesis prompt
        prompt = f"""You are a news analyst providing insights from recent news articles.

Query: "{query}"
Timeframe: Last {days} days

News articles found ({len(articles)} total, showing top {min(len(articles), 15)}):

{articles_text}

Provide a concise, insightful summary that:
1. Highlights the key themes and developments
2. Identifies important facts and patterns
3. Cites specific sources when mentioning information
4. Is clear, well-structured, and actionable
5. Notes any significant trends or breaking developments

Your analysis:"""

        # Get AI synthesis
        llm = get_llm(temperature=0.2)
        response = llm.invoke(prompt)
        synthesis = response.content
        
        # Return simplified response - just the answer
        total_articles = result.get("total_count", len(articles))
        num_sources = len(set(a.get("source", "") for a in articles))
        
        return f"{synthesis}\n\n---\n[Based on {total_articles} articles from {num_sources} sources, last {days} days]"
        
    except Exception as e:
        return f"Error searching news for '{query}': {str(e)}"


# ==============================================================================
# Main Entry Point
# ==============================================================================

if __name__ == "__main__":
    # Run the MCP server using stdio transport
    mcp.run(transport="stdio")

