"""
Semantic Cache Layer using Sentence Transformers.

Caches tool results with vector embeddings and matches similar queries
via cosine similarity to reduce redundant API calls.
Persists cache to JSON file for durability across sessions.
"""

import json
import os
from typing import Optional, Tuple
import numpy as np
from sentence_transformers import SentenceTransformer


class SemanticCache:
    """
    A semantic cache that stores query-result pairs with embeddings.
    Uses cosine similarity to find cached results for similar queries.
    Persists to JSON file for durability.
    """
    
    def __init__(
        self, 
        model_name: str = 'all-MiniLM-L6-v2', 
        threshold: float = 0.85,
        cache_file: str = 'cache.json'
    ):
        """
        Initialize the semantic cache.
        
        Args:
            model_name: Sentence transformer model to use for embeddings.
            threshold: Minimum cosine similarity (0-1) to consider a cache hit.
            cache_file: Path to JSON file for persisting cache.
        """
        self.model = SentenceTransformer(model_name)
        self.threshold = threshold
        self.cache_file = cache_file
        self.hits = 0
        self.misses = 0
        
        # Load existing cache from file
        self._load_cache()
    
    def _load_cache(self) -> None:
        """Load cache from JSON file if it exists."""
        self.cache: list[dict] = []
        
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.cache = data.get('entries', [])
                    self.hits = data.get('hits', 0)
                    self.misses = data.get('misses', 0)
                print(f"[Cache] Loaded {len(self.cache)} entries from {self.cache_file}")
            except (json.JSONDecodeError, IOError) as e:
                print(f"[Cache] Error loading cache file: {e}")
                self.cache = []
    
    def _save_cache(self) -> None:
        """Save cache to JSON file."""
        try:
            data = {
                'entries': self.cache,
                'hits': self.hits,
                'misses': self.misses
            }
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"[Cache] Error saving cache file: {e}")
    
    def get_embedding(self, text: str) -> np.ndarray:
        """Generate embedding for a text query."""
        return self.model.encode(text, convert_to_numpy=True)
    
    def cosine_similarity(self, emb1: np.ndarray, emb2: np.ndarray) -> float:
        """Compute cosine similarity between two embeddings."""
        dot_product = np.dot(emb1, emb2)
        norm1 = np.linalg.norm(emb1)
        norm2 = np.linalg.norm(emb2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return float(dot_product / (norm1 * norm2))
    
    def get_cached_result(self, query: str) -> Optional[Tuple[str, float]]:
        """
        Look up a cached result for a semantically similar query.
        
        Args:
            query: The query to search for in cache.
            
        Returns:
            Tuple of (cached_result, similarity_score) if found, None otherwise.
        """
        if not self.cache:
            self.misses += 1
            self._save_cache()
            return None
        
        # Normalize query for comparison
        query_normalized = query.strip().lower()
        
        # First check for exact match (fast path)
        for entry in self.cache:
            if entry['query'].strip().lower() == query_normalized:
                self.hits += 1
                self._save_cache()
                print(f"[Cache] Exact match for: {query}")
                return (entry['result'], 1.0)
        
        # Semantic similarity search
        query_embedding = self.get_embedding(query)
        
        best_match = None
        best_similarity = 0.0
        
        for entry in self.cache:
            cached_embedding = np.array(entry['embedding'])
            similarity = self.cosine_similarity(query_embedding, cached_embedding)
            if similarity > best_similarity:
                best_similarity = similarity
                best_match = (entry['result'], similarity)
        
        if best_similarity >= self.threshold:
            self.hits += 1
            self._save_cache()
            print(f"[Cache] Semantic match ({best_similarity:.2%}) for: {query}")
            return best_match
        
        self.misses += 1
        self._save_cache()
        print(f"[Cache] Miss for: {query}")
        return None
    
    def store_result(self, query: str, result: str) -> None:
        """
        Store a query-result pair in the cache.
        
        Args:
            query: The original query.
            result: The result to cache.
        """
        # Check if query already exists (avoid duplicates)
        query_normalized = query.strip().lower()
        for entry in self.cache:
            if entry['query'].strip().lower() == query_normalized:
                print(f"[Cache] Query already cached: {query}")
                return
        
        embedding = self.get_embedding(query)
        entry = {
            'query': query,
            'result': result,
            'embedding': embedding.tolist()  # Convert to list for JSON serialization
        }
        self.cache.append(entry)
        self._save_cache()
        print(f"[Cache] Stored: {query}")
    
    def get_stats(self) -> dict:
        """Get cache statistics."""
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0.0
        return {
            "entries": len(self.cache),
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": f"{hit_rate:.1f}%"
        }
    
    def clear(self) -> None:
        """Clear all cached entries and reset stats."""
        self.cache = []
        self.hits = 0
        self.misses = 0
        self._save_cache()
        print("[Cache] Cleared")
    
    def list_queries(self) -> list[str]:
        """List all cached queries."""
        return [entry['query'] for entry in self.cache]
