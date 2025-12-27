"""
Elasticsearch client for Q&A storage and search operations.

Provides async operations for:
- Index creation and management
- Document indexing (single and bulk)
- BM25 search with relevance scoring
- Statistics and health checks
"""

import os
from datetime import datetime
from typing import Optional

from elasticsearch import AsyncElasticsearch, NotFoundError
from dotenv import load_dotenv

load_dotenv()

# Configuration
ES_HOST = os.getenv("ELASTICSEARCH_HOST", "http://localhost:9200")
ES_INDEX = os.getenv("ELASTICSEARCH_INDEX", "news-qa")

# Index mapping for Q&A documents
INDEX_MAPPING = {
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 0,
        "analysis": {
            "analyzer": {
                "custom_english": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": ["lowercase", "english_stemmer", "english_stop"]
                }
            },
            "filter": {
                "english_stemmer": {
                    "type": "stemmer",
                    "language": "english"
                },
                "english_stop": {
                    "type": "stop",
                    "stopwords": "_english_"
                }
            }
        }
    },
    "mappings": {
        "properties": {
            "question": {
                "type": "text",
                "analyzer": "custom_english",
                "fields": {
                    "raw": {"type": "keyword"}
                }
            },
            "answer": {
                "type": "text",
                "analyzer": "custom_english"
            },
            "topic": {
                "type": "keyword"
            },
            "source": {
                "type": "keyword"
            },
            "created_at": {
                "type": "date"
            }
        }
    }
}


class ElasticsearchClient:
    """Async Elasticsearch client for Q&A operations."""

    def __init__(self, host: str = ES_HOST, index_name: str = ES_INDEX):
        """
        Initialize the Elasticsearch client.

        Args:
            host: Elasticsearch host URL
            index_name: Name of the index to use
        """
        self.host = host
        self.index_name = index_name
        self._client: Optional[AsyncElasticsearch] = None

    async def get_client(self) -> AsyncElasticsearch:
        """Get or create the async ES client."""
        if self._client is None:
            self._client = AsyncElasticsearch(
                hosts=[self.host],
                retry_on_timeout=True,
                max_retries=3
            )
        return self._client

    async def close(self) -> None:
        """Close the ES client connection."""
        if self._client is not None:
            await self._client.close()
            self._client = None

    async def ensure_index(self) -> bool:
        """
        Ensure the index exists, create if not.

        Returns:
            True if index exists or was created successfully
        """
        client = await self.get_client()
        try:
            exists = await client.indices.exists(index=self.index_name)
            if not exists:
                await client.indices.create(
                    index=self.index_name,
                    body=INDEX_MAPPING
                )
                print(f"[ES] Created index: {self.index_name}")
            return True
        except Exception as e:
            print(f"[ES] Error ensuring index: {e}")
            return False

    async def is_healthy(self) -> bool:
        """Check if Elasticsearch is reachable and healthy."""
        try:
            client = await self.get_client()
            health = await client.cluster.health()
            return health.get("status") in ("green", "yellow")
        except Exception:
            return False

    async def search(
        self,
        query: str,
        top_k: int = 10,
        min_score: float = 1.0
    ) -> dict:
        """
        Search for Q&A pairs using BM25 multi-match.

        Args:
            query: The search query text
            top_k: Maximum number of results to return
            min_score: Minimum relevance score threshold

        Returns:
            Dict with hits, total count, and query time
        """
        client = await self.get_client()

        search_body = {
            "size": top_k,
            "min_score": min_score,
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": ["question^3", "answer"],
                    "type": "best_fields",
                    "fuzziness": "AUTO",
                    "prefix_length": 2
                }
            },
            "highlight": {
                "fields": {
                    "question": {"number_of_fragments": 0},
                    "answer": {"number_of_fragments": 2}
                }
            },
            "_source": ["question", "answer", "topic", "source", "created_at"],
            "sort": [
                "_score",
                {"created_at": {"order": "desc"}}
            ]
        }

        try:
            response = await client.search(
                index=self.index_name,
                body=search_body
            )

            hits = []
            for hit in response["hits"]["hits"]:
                score = hit["_score"]
                # Categorize relevance based on score
                if score >= 10:
                    relevance = "high"
                elif score >= 5:
                    relevance = "medium"
                else:
                    relevance = "low"

                hits.append({
                    "id": hit["_id"],
                    "question": hit["_source"]["question"],
                    "answer": hit["_source"]["answer"],
                    "topic": hit["_source"].get("topic"),
                    "source": hit["_source"].get("source"),
                    "created_at": hit["_source"].get("created_at"),
                    "score": round(score, 2),
                    "relevance": relevance,
                    "highlights": hit.get("highlight", {})
                })

            return {
                "hits": hits,
                "total": response["hits"]["total"]["value"],
                "took_ms": response["took"]
            }

        except NotFoundError:
            # Index doesn't exist yet
            return {"hits": [], "total": 0, "took_ms": 0}
        except Exception as e:
            print(f"[ES] Search error: {e}")
            raise

    async def index_document(
        self,
        question: str,
        answer: str,
        topic: Optional[str] = None,
        source: Optional[str] = None,
        doc_id: Optional[str] = None
    ) -> str:
        """
        Index a single Q&A document.

        Args:
            question: The question text
            answer: The answer text
            topic: Optional topic category
            source: Optional source identifier
            doc_id: Optional document ID (auto-generated if not provided)

        Returns:
            The document ID
        """
        client = await self.get_client()
        await self.ensure_index()

        document = {
            "question": question,
            "answer": answer,
            "topic": topic,
            "source": source,
            "created_at": datetime.utcnow().isoformat()
        }

        if doc_id:
            response = await client.index(
                index=self.index_name,
                id=doc_id,
                body=document,
                refresh=True
            )
        else:
            response = await client.index(
                index=self.index_name,
                body=document,
                refresh=True
            )

        return response["_id"]

    async def bulk_index(
        self,
        documents: list[dict]
    ) -> dict:
        """
        Bulk index multiple Q&A documents.

        Args:
            documents: List of dicts with question, answer, topic, source

        Returns:
            Dict with success count and errors
        """
        client = await self.get_client()
        await self.ensure_index()

        operations = []
        for doc in documents:
            operations.append({"index": {"_index": self.index_name}})
            operations.append({
                "question": doc["question"],
                "answer": doc["answer"],
                "topic": doc.get("topic"),
                "source": doc.get("source"),
                "created_at": datetime.utcnow().isoformat()
            })

        response = await client.bulk(
            body=operations,
            refresh=True
        )

        success_count = sum(1 for item in response["items"] if item["index"]["status"] in (200, 201))
        error_count = len(documents) - success_count

        return {
            "indexed": success_count,
            "errors": error_count,
            "took_ms": response["took"]
        }

    async def get_stats(self) -> dict:
        """
        Get index statistics.

        Returns:
            Dict with document count, size, and health
        """
        client = await self.get_client()

        try:
            # Check if index exists
            exists = await client.indices.exists(index=self.index_name)
            if not exists:
                return {
                    "index_name": self.index_name,
                    "document_count": 0,
                    "index_size_bytes": 0,
                    "index_size_human": "0 B",
                    "health": "not_created"
                }

            # Get index stats
            stats = await client.indices.stats(index=self.index_name)
            index_stats = stats["indices"][self.index_name]["primaries"]

            doc_count = index_stats["docs"]["count"]
            size_bytes = index_stats["store"]["size_in_bytes"]

            # Human-readable size
            if size_bytes < 1024:
                size_human = f"{size_bytes} B"
            elif size_bytes < 1024 * 1024:
                size_human = f"{size_bytes / 1024:.1f} KB"
            elif size_bytes < 1024 * 1024 * 1024:
                size_human = f"{size_bytes / (1024 * 1024):.1f} MB"
            else:
                size_human = f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

            # Get health
            health = await client.cluster.health(index=self.index_name)

            return {
                "index_name": self.index_name,
                "document_count": doc_count,
                "index_size_bytes": size_bytes,
                "index_size_human": size_human,
                "health": health.get("status", "unknown")
            }

        except NotFoundError:
            return {
                "index_name": self.index_name,
                "document_count": 0,
                "index_size_bytes": 0,
                "index_size_human": "0 B",
                "health": "not_created"
            }
        except Exception as e:
            print(f"[ES] Stats error: {e}")
            return {
                "index_name": self.index_name,
                "document_count": 0,
                "index_size_bytes": 0,
                "index_size_human": "0 B",
                "health": "error"
            }

    async def delete_all(self) -> int:
        """
        Delete all documents from the index.

        Returns:
            Number of documents deleted
        """
        client = await self.get_client()

        try:
            # Check if index exists
            exists = await client.indices.exists(index=self.index_name)
            if not exists:
                return 0

            # Delete by query (match all)
            response = await client.delete_by_query(
                index=self.index_name,
                body={"query": {"match_all": {}}},
                refresh=True
            )

            return response.get("deleted", 0)

        except NotFoundError:
            return 0
        except Exception as e:
            print(f"[ES] Delete error: {e}")
            raise

    async def delete_index(self) -> bool:
        """
        Delete the entire index.

        Returns:
            True if deleted successfully
        """
        client = await self.get_client()

        try:
            exists = await client.indices.exists(index=self.index_name)
            if exists:
                await client.indices.delete(index=self.index_name)
                print(f"[ES] Deleted index: {self.index_name}")
            return True
        except Exception as e:
            print(f"[ES] Error deleting index: {e}")
            return False


# Singleton instance for the application
es_client = ElasticsearchClient()

