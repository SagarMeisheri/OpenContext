"""
FastAPI application for News Q&A Search and Generation.

Provides REST API endpoints for:
- Searching Q&A pairs in Elasticsearch
- Generating new Q&A pairs from news via LLM
- Managing the Q&A index
"""

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from elasticsearch_client import es_client
from llm_service import generate_qa_from_news
from models import (
    BulkIndexRequest,
    DeleteResponse,
    ErrorResponse,
    GenerateRequest,
    GenerateResponse,
    HealthResponse,
    IndexRequest,
    IndexResponse,
    QAPair,
    SearchRequest,
    SearchResponse,
    StatsResponse,
)

# API version
API_VERSION = "1.0.0"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown."""
    # Startup
    print("[API] Starting up...")

    # Ensure ES index exists
    if await es_client.is_healthy():
        await es_client.ensure_index()
        print("[API] Elasticsearch connected and index ready")
    else:
        print("[API] WARNING: Elasticsearch not available at startup")

    yield

    # Shutdown
    print("[API] Shutting down...")
    await es_client.close()


# Create FastAPI app
app = FastAPI(
    title="News Q&A API",
    description="Search and generate Q&A pairs from news using Elasticsearch and LLM",
    version=API_VERSION,
    lifespan=lifespan,
    responses={
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["Health"])
async def root():
    """Root endpoint with API info."""
    return {
        "name": "News Q&A API",
        "version": API_VERSION,
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Check API and Elasticsearch health."""
    es_healthy = await es_client.is_healthy()

    if es_healthy:
        status = "healthy"
    else:
        status = "degraded"

    return HealthResponse(
        status=status,
        elasticsearch=es_healthy,
        version=API_VERSION
    )


@app.post("/search", response_model=SearchResponse, tags=["Search"])
async def search_qa(request: SearchRequest):
    """
    Search for relevant Q&A pairs.

    Uses Elasticsearch BM25 search to find the most relevant Q&A pairs.
    If no matches are found and fallback_to_llm is True, generates new
    Q&A pairs using LLM and indexes them.
    """
    start_time = time.time()

    try:
        # Search Elasticsearch
        search_result = await es_client.search(
            query=request.query,
            top_k=request.top_k,
            min_score=request.min_score
        )

        hits = search_result["hits"]
        source = "elasticsearch"

        # If no matches and fallback enabled, generate via LLM
        if not hits and request.fallback_to_llm:
            gen_result = await generate_qa_from_news(
                topic=request.query,
                days=7,
                num_pairs=5
            )

            if gen_result.success and gen_result.qa_pairs:
                # Index generated Q&As
                for qa in gen_result.qa_pairs:
                    await es_client.index_document(
                        question=qa.question,
                        answer=qa.answer,
                        topic=qa.topic,
                        source=qa.source
                    )

                # Convert to response format
                hits = [
                    {
                        "id": None,
                        "question": qa.question,
                        "answer": qa.answer,
                        "topic": qa.topic,
                        "source": qa.source,
                        "score": None,
                        "relevance": "high",
                        "created_at": None
                    }
                    for qa in gen_result.qa_pairs
                ]
                source = "llm_generated"

        # Build response
        results = [
            QAPair(
                id=hit.get("id"),
                question=hit["question"],
                answer=hit["answer"],
                topic=hit.get("topic"),
                source=hit.get("source"),
                score=hit.get("score"),
                relevance=hit.get("relevance"),
                created_at=hit.get("created_at")
            )
            for hit in hits
        ]

        query_time_ms = (time.time() - start_time) * 1000

        return SearchResponse(
            query=request.query,
            results=results,
            total_hits=len(results),
            source=source,
            query_time_ms=round(query_time_ms, 2)
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate", response_model=GenerateResponse, tags=["Generate"])
async def generate_qa(request: GenerateRequest):
    """
    Generate Q&A pairs from news about a topic.

    Fetches current news headlines and uses LLM to create
    question-answer pairs. Optionally indexes results in Elasticsearch.
    """
    start_time = time.time()

    try:
        result = await generate_qa_from_news(
            topic=request.topic,
            days=request.days,
            num_pairs=request.num_pairs
        )

        if not result.success:
            raise HTTPException(status_code=400, detail=result.error)

        # Index generated Q&As
        indexed = False
        if result.qa_pairs:
            for qa in result.qa_pairs:
                await es_client.index_document(
                    question=qa.question,
                    answer=qa.answer,
                    topic=qa.topic,
                    source=qa.source
                )
            indexed = True

        # Convert to response format
        results = [
            QAPair(
                question=qa.question,
                answer=qa.answer,
                topic=qa.topic,
                source=qa.source,
                relevance="high"
            )
            for qa in result.qa_pairs
        ]

        generation_time_ms = (time.time() - start_time) * 1000

        return GenerateResponse(
            topic=request.topic,
            results=results,
            news_count=result.news_count,
            indexed=indexed,
            generation_time_ms=round(generation_time_ms, 2)
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/index", response_model=IndexResponse, tags=["Index"])
async def index_single_qa(request: IndexRequest):
    """
    Manually index a single Q&A pair.
    """
    try:
        doc_id = await es_client.index_document(
            question=request.question,
            answer=request.answer,
            topic=request.topic,
            source=request.source
        )

        return IndexResponse(
            success=True,
            id=doc_id,
            indexed_count=1,
            message="Q&A pair indexed successfully"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/index/bulk", response_model=IndexResponse, tags=["Index"])
async def index_bulk_qa(request: BulkIndexRequest):
    """
    Bulk index multiple Q&A pairs.
    """
    try:
        documents = [
            {
                "question": item.question,
                "answer": item.answer,
                "topic": item.topic,
                "source": item.source
            }
            for item in request.items
        ]

        result = await es_client.bulk_index(documents)

        return IndexResponse(
            success=result["errors"] == 0,
            indexed_count=result["indexed"],
            message=f"Indexed {result['indexed']} documents, {result['errors']} errors"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats", response_model=StatsResponse, tags=["Index"])
async def get_stats():
    """
    Get index statistics.
    """
    try:
        stats = await es_client.get_stats()
        return StatsResponse(**stats)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/index", response_model=DeleteResponse, tags=["Index"])
async def delete_all_qa():
    """
    Delete all Q&A documents from the index.
    """
    try:
        deleted_count = await es_client.delete_all()

        return DeleteResponse(
            success=True,
            deleted_count=deleted_count,
            message=f"Deleted {deleted_count} documents"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/index/full", response_model=DeleteResponse, tags=["Index"])
async def delete_index():
    """
    Delete the entire index (use with caution).
    """
    try:
        success = await es_client.delete_index()

        return DeleteResponse(
            success=success,
            deleted_count=0,
            message="Index deleted" if success else "Failed to delete index"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)

