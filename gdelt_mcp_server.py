
from mcp.server.fastmcp import FastMCP
from typing import Optional, List, Dict, Any, Literal
import requests
from datetime import datetime, timedelta
from urllib.parse import urlencode
import json
from enum import Enum

# Configuration
GDELT_API_BASE = "https://api.gdeltproject.org/api/v2/doc/doc"
DEFAULT_TIMESPAN = "1week"
DEFAULT_LANGUAGE = "english"
DEFAULT_MAX_RESULTS = 75
MAX_RESULTS_LIMIT = 250
REQUEST_TIMEOUT = 30

# Initialize MCP server
mcp = FastMCP("GDELT News Search")


# ==============================================================================
# GDELT API Client
# ==============================================================================

class GDELTClient:
    """Client for interacting with GDELT DOC 2.0 API"""
    
    def __init__(self, base_url: str = GDELT_API_BASE):
        self.base_url = base_url
        self.session = requests.Session()
    
    def _build_query_string(self, operators: Dict[str, Any]) -> str:
        """Build GDELT query string from operators"""
        query_parts = []
        
        for key, value in operators.items():
            if value is None:
                continue
                
            if key == "keywords":
                query_parts.append(value)
            elif key == "domain":
                query_parts.append(f"domain:{value}")
            elif key == "domainis":
                query_parts.append(f"domainis:{value}")
            elif key == "sourcelang":
                query_parts.append(f"sourcelang:{value}")
            elif key == "sourcecountry":
                query_parts.append(f"sourcecountry:{value}")
            elif key == "theme":
                query_parts.append(f"theme:{value}")
            elif key == "tone_min":
                query_parts.append(f"tone>{value}")
            elif key == "tone_max":
                query_parts.append(f"tone<{value}")
            elif key == "toneabs_min":
                query_parts.append(f"toneabs>{value}")
            elif key == "toneabs_max":
                query_parts.append(f"toneabs<{value}")
            elif key == "near":
                distance, terms = value
                query_parts.append(f'near{distance}:"{terms}"')
            elif key == "repeat":
                count, term = value
                query_parts.append(f'repeat{count}:"{term}"')
        
        return " ".join(query_parts)
    
    def _make_request(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Make HTTP request to GDELT API"""
        try:
            response = self.session.get(
                self.base_url,
                params=params,
                timeout=REQUEST_TIMEOUT
            )
            response.raise_for_status()
            
            # Handle different content types
            content_type = response.headers.get('content-type', '')
            
            if 'application/json' in content_type:
                return response.json()
            elif 'text/csv' in content_type:
                return {"data": response.text, "format": "csv"}
            else:
                return {"data": response.text, "format": "text"}
                
        except requests.exceptions.Timeout:
            raise Exception("GDELT API request timed out")
        except requests.exceptions.RequestException as e:
            raise Exception(f"GDELT API request failed: {str(e)}")
    
    def search_articles(
        self,
        query: str,
        mode: str = "artlist",
        timespan: str = DEFAULT_TIMESPAN,
        max_records: int = DEFAULT_MAX_RESULTS,
        sourcelang: str = DEFAULT_LANGUAGE,
        sort: str = "hybridrel",
        output_format: str = "json"
    ) -> Dict[str, Any]:
        """Search for articles"""
        params = {
            "query": query,
            "mode": mode,
            "format": output_format,
            "timespan": timespan,
            "maxrecords": min(max_records, MAX_RESULTS_LIMIT),
            "sort": sort,
            "sourcelang": sourcelang
        }
        
        return self._make_request(params)
    
    def get_timeline(
        self,
        query: str,
        mode: str = "timelinevol",
        timespan: str = DEFAULT_TIMESPAN,
        smoothing: Optional[int] = None,
        output_format: str = "json"
    ) -> Dict[str, Any]:
        """Get timeline data"""
        params = {
            "query": query,
            "mode": mode,
            "format": output_format,
            "timespan": timespan
        }
        
        if smoothing:
            params["timelinesmooth"] = min(smoothing, 30)
        
        return self._make_request(params)
    
    def get_tone_chart(
        self,
        query: str,
        timespan: str = DEFAULT_TIMESPAN,
        output_format: str = "json"
    ) -> Dict[str, Any]:
        """Get tone distribution"""
        params = {
            "query": query,
            "mode": "tonechart",
            "format": output_format,
            "timespan": timespan
        }
        
        return self._make_request(params)


# Initialize client
client = GDELTClient()


# ==============================================================================
# MCP Tools
# ==============================================================================

@mcp.tool()
def search_articles(
    query: str,
    timespan: str = "1week",
    max_results: int = 75,
    sort: Literal["relevance", "date_desc", "date_asc", "tone_desc", "tone_asc"] = "relevance"
) -> str:
    """
    Search GDELT for news articles matching keywords.
    
    Supports:
    - Phrase searches: "donald trump"
    - Boolean OR: (clinton OR sanders OR trump)
    - Exclusion: -keyword
    
    Args:
        query: Search terms (keywords, phrases with quotes, OR statements)
        timespan: Time range - format: NUMBER + unit (min/h/d/w/m)
                 Examples: "1week", "3days", "24h", "2months"
        max_results: Number of results to return (1-250, default 75)
        sort: Sort order - relevance, date_desc, date_asc, tone_desc, tone_asc
    
    Returns:
        JSON string with article list including titles, URLs, dates, sources, and tone
    """
    try:
        # Map sort parameter to GDELT format
        sort_map = {
            "relevance": "hybridrel",
            "date_desc": "datedesc",
            "date_asc": "dateasc",
            "tone_desc": "tonedesc",
            "tone_asc": "toneasc"
        }
        
        result = client.search_articles(
            query=query,
            timespan=timespan,
            max_records=max_results,
            sort=sort_map.get(sort, "hybridrel")
        )
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)


@mcp.tool()
def search_with_filters(
    query: str,
    source_country: Optional[str] = None,
    source_language: Optional[str] = None,
    domain: Optional[str] = None,
    theme: Optional[str] = None,
    tone_min: Optional[float] = None,
    tone_max: Optional[float] = None,
    timespan: str = "1week",
    max_results: int = 75
) -> str:
    """
    Advanced article search with filtering options.
    
    Args:
        query: Base search terms
        source_country: Filter by country (e.g., "france", "india", "us")
        source_language: Filter by language (e.g., "english", "spanish", "french")
        domain: Filter by domain (e.g., "cnn.com", "bbc.co.uk")
        theme: GDELT theme code (e.g., "TERROR", "ENV_CLIMATECHANGE", "ECON_TRADE")
        tone_min: Minimum tone score (more positive than this, e.g., 5.0)
        tone_max: Maximum tone score (more negative than this, e.g., -5.0)
        timespan: Time range (e.g., "1week", "3days", "2months")
        max_results: Number of results (1-250)
    
    Returns:
        JSON string with filtered article list
    """
    try:
        # Build query with filters
        query_parts = [query]
        
        if source_country:
            query_parts.append(f"sourcecountry:{source_country.lower().replace(' ', '')}")
        if source_language:
            query_parts.append(f"sourcelang:{source_language.lower()}")
        if domain:
            query_parts.append(f"domain:{domain.lower()}")
        if theme:
            query_parts.append(f"theme:{theme.upper()}")
        if tone_min is not None:
            query_parts.append(f"tone>{tone_min}")
        if tone_max is not None:
            query_parts.append(f"tone<{tone_max}")
        
        combined_query = " ".join(query_parts)
        
        result = client.search_articles(
            query=combined_query,
            timespan=timespan,
            max_records=max_results
        )
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)


@mcp.tool()
def get_coverage_timeline(
    query: str,
    timespan: str = "1month",
    metric: Literal["volume", "tone", "language", "country"] = "volume",
    smoothing: Optional[int] = None
) -> str:
    """
    Get timeline showing how coverage changes over time.
    
    Args:
        query: Search terms
        timespan: Time period to analyze (e.g., "1week", "1month", "3months")
        metric: What to track over time:
               - volume: Percentage of all coverage mentioning query
               - tone: Average sentiment over time
               - language: Coverage breakdown by language
               - country: Coverage breakdown by source country
        smoothing: Optional moving average smoothing (1-30 days)
    
    Returns:
        JSON string with time-series data
    """
    try:
        mode_map = {
            "volume": "timelinevol",
            "tone": "timelinetone",
            "language": "timelinelang",
            "country": "timelinesourcecountry"
        }
        
        result = client.get_timeline(
            query=query,
            mode=mode_map[metric],
            timespan=timespan,
            smoothing=smoothing
        )
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)


@mcp.tool()
def analyze_sentiment(
    query: str,
    timespan: str = "1week"
) -> str:
    """
    Analyze sentiment/tone distribution of coverage.
    
    Returns a histogram showing how many articles fall into each
    emotional tone range from very negative to very positive.
    
    Args:
        query: Search terms
        timespan: Time period to analyze (e.g., "1week", "1month")
    
    Returns:
        JSON string with tone distribution data (histogram of sentiment)
    """
    try:
        result = client.get_tone_chart(
            query=query,
            timespan=timespan
        )
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)


@mcp.tool()
def search_by_proximity(
    terms: str,
    max_distance: int = 10,
    timespan: str = "1week",
    max_results: int = 75
) -> str:
    """
    Search for articles where terms appear near each other.
    
    Finds articles where all specified terms appear within a certain
    number of words of each other.
    
    Args:
        terms: Space-separated words that must appear together (e.g., "trump putin")
        max_distance: Maximum words apart (default 10)
        timespan: Time range
        max_results: Number of results
    
    Returns:
        JSON string with articles where terms appear in proximity
    """
    try:
        query = f'near{max_distance}:"{terms}"'
        
        result = client.search_articles(
            query=query,
            timespan=timespan,
            max_records=max_results
        )
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)


@mcp.tool()
def search_multiple_sources(
    query: str,
    countries: Optional[List[str]] = None,
    languages: Optional[List[str]] = None,
    timespan: str = "1week",
    max_results: int = 75
) -> str:
    """
    Search across multiple countries or languages simultaneously.
    
    Args:
        query: Search terms
        countries: List of countries (e.g., ["france", "germany", "italy"])
        languages: List of languages (e.g., ["english", "spanish", "french"])
        timespan: Time range
        max_results: Number of results
    
    Returns:
        JSON string with articles from specified sources
    """
    try:
        query_parts = [query]
        
        if countries:
            country_filters = " OR ".join([f"sourcecountry:{c.lower().replace(' ', '')}" for c in countries])
            query_parts.append(f"({country_filters})")
        
        if languages:
            lang_filters = " OR ".join([f"sourcelang:{l.lower()}" for l in languages])
            query_parts.append(f"({lang_filters})")
        
        combined_query = " ".join(query_parts)
        
        result = client.search_articles(
            query=combined_query,
            timespan=timespan,
            max_records=max_results
        )
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)


@mcp.tool()
def compare_topics(
    topic1: str,
    topic2: str,
    timespan: str = "1month"
) -> str:
    """
    Compare coverage volume of two topics over time.
    
    Useful for comparing attention to different issues, candidates,
    events, or trends.
    
    Args:
        topic1: First search query
        topic2: Second search query
        timespan: Time period (e.g., "1month", "3months")
    
    Returns:
        JSON string with timeline data for both topics
    """
    try:
        result1 = client.get_timeline(
            query=topic1,
            mode="timelinevol",
            timespan=timespan
        )
        
        result2 = client.get_timeline(
            query=topic2,
            mode="timelinevol",
            timespan=timespan
        )
        
        comparison = {
            "topic1": {
                "query": topic1,
                "data": result1
            },
            "topic2": {
                "query": topic2,
                "data": result2
            }
        }
        
        return json.dumps(comparison, indent=2)
        
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)


@mcp.tool()
def search_by_domain_list(
    query: str,
    domains: List[str],
    timespan: str = "1week",
    max_results: int = 75
) -> str:
    """
    Search within specific news domains/outlets.
    
    Args:
        query: Search terms
        domains: List of domains (e.g., ["cnn.com", "bbc.co.uk", "reuters.com"])
        timespan: Time range
        max_results: Number of results
    
    Returns:
        JSON string with articles from specified domains
    """
    try:
        domain_filters = " OR ".join([f"domain:{d.lower()}" for d in domains])
        combined_query = f"{query} ({domain_filters})"
        
        result = client.search_articles(
            query=combined_query,
            timespan=timespan,
            max_records=max_results
        )
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)


# ==============================================================================
# Main Entry Point
# ==============================================================================

if __name__ == "__main__":
    # Run the MCP server
    # Use stdio transport for local development
    # For production, can switch to streamable-http
    mcp.run(transport="stdio")
