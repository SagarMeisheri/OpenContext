"""
API Client for calling FastAPI backend services.

Provides sync wrapper functions for Streamlit to call the FastAPI backend.
"""

import os
from typing import Optional

import httpx
from dotenv import load_dotenv

load_dotenv()

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
API_TIMEOUT = float(os.getenv("API_TIMEOUT", "30.0"))


class APIClient:
    """Synchronous API client for FastAPI backend."""

    def __init__(self, base_url: str = API_BASE_URL, timeout: float = API_TIMEOUT):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _request(self, method: str, endpoint: str, **kwargs) -> dict:
        """Make HTTP request to the API."""
        url = f"{self.base_url}{endpoint}"
        kwargs.setdefault("timeout", self.timeout)

        with httpx.Client() as client:
            response = client.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()

    def health_check(self) -> dict:
        """Check if the API is healthy."""
        try:
            return self._request("GET", "/health")
        except Exception:
            return {"status": "unhealthy", "elasticsearch": False, "version": "unknown"}

    def is_healthy(self) -> bool:
        """Quick check if API is reachable."""
        try:
            health = self.health_check()
            return health.get("status") in ("healthy", "degraded")
        except Exception:
            return False

    def search(
        self,
        query: str,
        top_k: int = 10,
        min_score: float = 1.0,
        fallback_to_llm: bool = True
    ) -> dict:
        """
        Search for Q&A pairs.

        Args:
            query: The search query
            top_k: Number of results to return
            min_score: Minimum relevance score
            fallback_to_llm: Generate via LLM if no matches found

        Returns:
            Search response with results
        """
        return self._request(
            "POST",
            "/search",
            json={
                "query": query,
                "top_k": top_k,
                "min_score": min_score,
                "fallback_to_llm": fallback_to_llm
            }
        )

    def generate(
        self,
        topic: str,
        days: int = 7,
        num_pairs: int = 5
    ) -> dict:
        """
        Generate Q&A pairs from news.

        Args:
            topic: News topic to generate Q&As for
            days: Days to look back for news
            num_pairs: Number of Q&A pairs to generate

        Returns:
            Generation response with Q&A pairs
        """
        return self._request(
            "POST",
            "/generate",
            json={
                "topic": topic,
                "days": days,
                "num_pairs": num_pairs
            }
        )

    def get_stats(self) -> dict:
        """Get Elasticsearch index statistics."""
        try:
            return self._request("GET", "/stats")
        except Exception:
            return {
                "index_name": "news-qa",
                "document_count": 0,
                "index_size_human": "N/A",
                "health": "unknown"
            }

    def clear_index(self) -> dict:
        """Clear all Q&A documents from the index."""
        return self._request("DELETE", "/index")


# Singleton instance
api_client = APIClient()


def format_qa_response(response: dict) -> str:
    """
    Format API response as readable text for chat display.

    Args:
        response: Search or generate response from API

    Returns:
        Formatted string for display
    """
    results = response.get("results", [])
    source = response.get("source", "unknown")
    query_time = response.get("query_time_ms") or response.get("generation_time_ms", 0)

    if not results:
        return "No relevant Q&A pairs found for your query."

    lines = []

    # Header
    if source == "llm_generated":
        lines.append("**Generated new Q&A pairs from current news:**\n")
    else:
        lines.append(f"**Found {len(results)} relevant Q&A pairs:**\n")

    # Q&A pairs
    for i, qa in enumerate(results, 1):
        question = qa.get("question", "")
        answer = qa.get("answer", "")
        score = qa.get("score")
        relevance = qa.get("relevance", "")

        lines.append(f"**Q{i}:** {question}")
        lines.append(f"**A{i}:** {answer}")

        if score is not None:
            lines.append(f"*Relevance: {relevance} (score: {score})*")

        lines.append("")  # Empty line between pairs

    # Footer
    lines.append(f"---\n*Query time: {query_time:.0f}ms | Source: {source}*")

    return "\n".join(lines)

