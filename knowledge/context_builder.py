"""
knowledge/context_builder.py
============================
Context Builder Agent.
Aggregates retrieved RAG chunks, trims them within token limits,
and constructs optimized context prompts for LLM queries.
"""

import logging
from typing import List, Dict, Any

logger = logging.getLogger("msa.knowledge.context_builder")


class ContextBuilder:
    """
    Constructs contextual prompts from retrieved database chunks.
    Ensures the combined context does not exceed LLM context window boundaries.
    """

    def __init__(self, max_tokens: int = 1500):
        self.max_tokens = max_tokens

    def build_context(self, retrieved_chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Formats chunks and builds an augmented context prompt.
        Trims results if they exceed the max_tokens constraint (approximate token calculation).
        """
        if not retrieved_chunks:
            return {
                "context_str": "",
                "chunks_used": 0,
                "total_tokens": 0,
                "sources": []
            }

        formatted_parts = []
        tokens_used = 0
        chunks_used = 0
        sources = set()

        for chunk in retrieved_chunks:
            # Format chunk nicely
            file_path = chunk.get("file_path", "unknown")
            text = chunk.get("text", chunk.get("content", ""))
            category = chunk.get("category", "document")
            
            source_label = os.path.basename(file_path) if os.path.sep in file_path or "/" in file_path else file_path
            formatted_chunk = f"Source: {source_label} ({category})\nContent: {text}\n---\n"
            
            # Approximate token count (1 token ≈ 4 characters)
            chunk_tokens = len(formatted_chunk) // 4
            
            # Check budget
            if tokens_used + chunk_tokens > self.max_tokens:
                # If this is the first chunk and it's too big, truncate it
                if chunks_used == 0:
                    allowed_chars = self.max_tokens * 4
                    truncated_text = text[:allowed_chars]
                    formatted_chunk = f"Source: {source_label} ({category})\nContent: {truncated_text} [TRUNCATED]\n---\n"
                    formatted_parts.append(formatted_chunk)
                    tokens_used += self.max_tokens
                    chunks_used += 1
                    sources.add(file_path)
                break
                
            formatted_parts.append(formatted_chunk)
            tokens_used += chunk_tokens
            chunks_used += 1
            sources.add(file_path)

        context_str = "\n".join(formatted_parts)
        
        logger.info(
            "ContextBuilder: assembled context using %d/%d chunks (%d approx tokens).",
            chunks_used, len(retrieved_chunks), tokens_used
        )

        return {
            "context_str": context_str,
            "chunks_used": chunks_used,
            "total_tokens": tokens_used,
            "sources": list(sources)
        }
import os
