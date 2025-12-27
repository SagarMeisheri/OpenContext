"""
Pydantic models for FastAPI request/response schemas.
"""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


# Request Models
class SearchRequest(BaseModel):
    """Request model for searching Q&A pairs."""
    query: str = Field(..., min_length=1, max_length=500, description="The search query")
    top_k: int = Field(default=10, ge=1, le=50, description="Number of results to return")
    min_score: float = Field(default=1.0, ge=0, description="Minimum relevance score threshold")
    fallback_to_llm: bool = Field(default=True, description="Generate via LLM if no ES matches found")


class GenerateRequest(BaseModel):
    """Request model for generating Q&A pairs from a news topic."""
    topic: str = Field(..., min_length=1, max_length=200, description="News topic to generate Q&As for")
    days: int = Field(default=7, ge=1, le=30, description="Number of days to look back for news")
    num_pairs: int = Field(default=5, ge=1, le=10, description="Number of Q&A pairs to generate")


class IndexRequest(BaseModel):
    """Request model for manually indexing a Q&A pair."""
    question: str = Field(..., min_length=1, max_length=1000, description="The question text")
    answer: str = Field(..., min_length=1, max_length=5000, description="The answer text")
    topic: Optional[str] = Field(default=None, max_length=100, description="Topic category")
    source: Optional[str] = Field(default="manual", max_length=100, description="Source of the Q&A")


class BulkIndexRequest(BaseModel):
    """Request model for bulk indexing multiple Q&A pairs."""
    items: list[IndexRequest] = Field(..., min_length=1, max_length=100, description="List of Q&A pairs to index")


# Response Models
class QAPair(BaseModel):
    """A single Q&A pair with metadata."""
    id: Optional[str] = Field(default=None, description="Document ID in Elasticsearch")
    question: str = Field(..., description="The question text")
    answer: str = Field(..., description="The answer text")
    topic: Optional[str] = Field(default=None, description="Topic category")
    source: Optional[str] = Field(default=None, description="Source of the Q&A")
    score: Optional[float] = Field(default=None, description="Relevance score from search")
    relevance: Optional[Literal["high", "medium", "low"]] = Field(default=None, description="Relevance category")
    created_at: Optional[datetime] = Field(default=None, description="When the Q&A was indexed")


class SearchResponse(BaseModel):
    """Response model for search results."""
    query: str = Field(..., description="The original search query")
    results: list[QAPair] = Field(default_factory=list, description="List of matching Q&A pairs")
    total_hits: int = Field(default=0, description="Total number of matches found")
    source: Literal["elasticsearch", "llm_generated"] = Field(..., description="Where results came from")
    query_time_ms: float = Field(..., description="Query execution time in milliseconds")


class GenerateResponse(BaseModel):
    """Response model for Q&A generation."""
    topic: str = Field(..., description="The news topic")
    results: list[QAPair] = Field(default_factory=list, description="Generated Q&A pairs")
    news_count: int = Field(default=0, description="Number of news articles processed")
    indexed: bool = Field(default=False, description="Whether results were indexed in ES")
    generation_time_ms: float = Field(..., description="Generation time in milliseconds")


class IndexResponse(BaseModel):
    """Response model for indexing operations."""
    success: bool = Field(..., description="Whether the operation succeeded")
    id: Optional[str] = Field(default=None, description="Document ID if single item indexed")
    indexed_count: int = Field(default=0, description="Number of items indexed")
    message: str = Field(..., description="Status message")


class StatsResponse(BaseModel):
    """Response model for index statistics."""
    index_name: str = Field(..., description="Name of the ES index")
    document_count: int = Field(default=0, description="Total documents in index")
    index_size_bytes: int = Field(default=0, description="Size of index in bytes")
    index_size_human: str = Field(default="0 B", description="Human-readable index size")
    health: str = Field(default="unknown", description="Index health status")


class DeleteResponse(BaseModel):
    """Response model for delete operations."""
    success: bool = Field(..., description="Whether the operation succeeded")
    deleted_count: int = Field(default=0, description="Number of documents deleted")
    message: str = Field(..., description="Status message")


class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    detail: Optional[str] = Field(default=None, description="Additional error details")


class HealthResponse(BaseModel):
    """Health check response."""
    status: Literal["healthy", "degraded", "unhealthy"] = Field(..., description="Overall health status")
    elasticsearch: bool = Field(..., description="ES connection status")
    version: str = Field(..., description="API version")

