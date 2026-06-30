"""
agent/MemoryAgent.py
====================
Dedicated Memory Agent responsible for all memory operations in MSA AI AGENT.
Manages Working Memory, Conversation history, Long-Term Semantic/Episodic/Procedural memory,
Profile/Project configurations, caching, ranking, compression, deduplication, and consolidation.
"""

import os
import time
import logging
import math
from typing import Dict, Any, List, Optional
from datetime import datetime

from memory.rag_memory import RAGMemory
from services.performance_cache import RAGPerformanceCache
from indexes.sqlite_db import SQLiteMetadataStore
from infrastructure.service_registry import BaseService

logger = logging.getLogger("msa.agent.memory_agent")


class MemoryAgent(BaseService):
    """
    Enterprise Memory Agent orchestrating session-level and persistent memory tiers.
    """

    def __init__(self, sqlite_memory=None, cache=None):
        super().__init__()
        self.rag = RAGMemory(sqlite_memory=sqlite_memory)
        self.cache = cache or RAGPerformanceCache()
        self.meta_store = SQLiteMetadataStore()
        
        # Working memory: active session-level state
        self.working_memory: Dict[str, Any] = {
            "current_tasks": [],
            "temp_vars": {},
            "session_start": datetime.now().isoformat(),
            "owner_profile": {}
        }
        
        self._load_owner_profile()
        logger.info("MemoryAgent initialized successfully.")

    def start(self) -> None:
        """Starts the MemoryAgent service."""
        super().start()
        logger.info("MemoryAgent service is running and active.")

    def stop(self) -> None:
        """Stops the MemoryAgent service."""
        super().stop()
        logger.info("MemoryAgent service has stopped.")

    def _load_owner_profile(self) -> None:
        """Loads profile configuration into working memory."""
        try:
            from config import USER_PROFILE
            self.working_memory["owner_profile"] = USER_PROFILE
        except ImportError:
            pass

    def add_working_memory(self, key: str, value: Any) -> None:
        """Stores a temporary variable in fast working RAM memory."""
        self.working_memory["temp_vars"][key] = value

    def get_working_memory(self, key: str, default: Any = None) -> Any:
        """Retrieves a temporary variable from working RAM memory."""
        return self.working_memory["temp_vars"].get(key, default)

    def remember(self, text: str, category: str = "fact", importance: float = 0.5) -> bool:
        """
        Stores semantic, episodic, or procedural text inside RAG memory.
        Automatically handles metadata enrichment.
        """
        if not text or not text.strip():
            return False
        
        metadata = {
            "importance": importance,
            "category": category,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            return self.rag.remember(text, category)
        except Exception as e:
            logger.error("MemoryAgent failed to remember text (%s)", e)
            return False

    def recall(self, query: str, top_k: int = 5, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Retrieves relevant long-term semantic, episodic, or project memories.
        Utilizes memory performance cache to optimize latency.
        """
        if not query or not query.strip():
            return []

        # Check Cache
        cache_key = f"recall:{query}:{top_k}:{category}"
        cached = self.cache.embeddings.get(cache_key)
        if cached is not None:
            return cached

        try:
            results = self.rag.recall(query, top_k=top_k)
            # Apply category filtering if requested
            if category:
                results = [r for r in results if r.get("category") == category]
            
            # Rank results dynamically by incorporating age penalty & importance score
            ranked = self._rank_memories(results)
            
            # Cache results
            self.cache.embeddings.put(cache_key, ranked)
            return ranked
        except Exception as e:
            logger.error("MemoryAgent failed to recall memories (%s)", e)
            return []

    def _rank_memories(self, memories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Ranks retrieved memories based on semantic score, age decay, and importance."""
        ranked = []
        now = datetime.now()
        
        for m in memories:
            score = m.get("score", 0.5)
            
            # Extract timestamp from metadata
            meta = m.get("metadata", {})
            ts_str = meta.get("timestamp")
            importance = float(meta.get("importance", 0.5))
            
            decay = 1.0
            if ts_str:
                try:
                    ts = datetime.fromisoformat(ts_str)
                    hours_old = (now - ts).total_seconds() / 3600.0
                    # Decays slowly over days
                    decay = math.exp(-0.005 * hours_old)
                except Exception:
                    pass
            
            # Final ranking score formula
            m["ranking_score"] = (score * 0.6) + (importance * 0.3) + (decay * 0.1)
            ranked.append(m)
            
        ranked.sort(key=lambda x: x.get("ranking_score", 0.0), reverse=True)
        return ranked

    def compress_conversations(self, limit: int = 20) -> bool:
        """
        Compresses and consolidates old conversation turns into summarized episodic memories.
        Reduces history bloat in SQLite metadata.
        """
        try:
            chunks = self.meta_store.get_all_chunks()
            # Select oldest conversation entries
            convs = [c for c in chunks if c.get("category") == "conversation"]
            if len(convs) <= limit:
                return True # No compression needed

            # Keep the newest ones, summarize the older ones
            to_compress = convs[:-limit]
            summary_text = f"Consolidated Conversation Summary (Timestamp: {datetime.now().isoformat()}):\n"
            for c in to_compress:
                summary_text += f"- {c['content']}\n"
                # Delete old chunk from SQLite & FAISS
                self.meta_store.delete_chunk(c["faiss_id"])
            
            # Save the summarized context back as a semantic fact memory
            self.remember(summary_text, category="fact", importance=0.8)
            logger.info("MemoryAgent compressed %d old conversation turns.", len(to_compress))
            return True
        except Exception as e:
            logger.error("MemoryAgent failed to compress history (%s)", e)
            return False

    def clean_duplicates(self) -> int:
        """Finds and removes duplicate vector/metadata entries."""
        try:
            chunks = self.meta_store.get_all_chunks()
            seen_hashes = set()
            duplicates_removed = 0
            
            import hashlib
            for c in chunks:
                content = c["content"].strip()
                h = hashlib.sha256(content.encode("utf-8")).hexdigest()
                if h in seen_hashes:
                    # Remove duplicate
                    self.meta_store.delete_chunk(c["faiss_id"])
                    duplicates_removed += 1
                else:
                    seen_hashes.add(h)
            
            if duplicates_removed > 0:
                logger.info("MemoryAgent cleaned %d duplicate memories.", duplicates_removed)
            return duplicates_removed
        except Exception as e:
            logger.error("MemoryAgent duplicate cleanup failed (%s)", e)
            return 0

    def get_stats(self) -> Dict[str, Any]:
        """Gathers memory sizing, cache metrics, and usage statistics."""
        db_stats = self.meta_store.get_stats()
        cache_stats = self.cache.get_stats()
        
        return {
            "status": "online",
            "total_files": db_stats.get("total_files", 0),
            "total_chunks": db_stats.get("total_chunks", 0),
            "working_memory_keys": list(self.working_memory["temp_vars"].keys()),
            "owner": self.working_memory["owner_profile"].get("name", "Unknown"),
            "cache_hits": cache_stats.get("embeddings", {}).get("hits", 0),
            "cache_misses": cache_stats.get("embeddings", {}).get("misses", 0)
        }
