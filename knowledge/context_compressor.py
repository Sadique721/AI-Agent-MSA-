"""
knowledge/context_compressor.py
==============================
Context Compressor Service.
Filters duplicate text blocks, merges adjacent/overlapping file chunks,
and dynamically summarizes contexts to optimize prompt token budgets.
"""

import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger("msa.knowledge.context_compressor")


class ContextCompressor:
    """
    Optimizes retrieved RAG contexts by removing redundancy and packing maximum info within token budgets.
    """
    def __init__(self, max_tokens: int = 1500):
        self.max_tokens = max_tokens

    def compress_chunks(self, chunks: List[Dict[str, Any]], query: Optional[str] = None) -> Dict[str, Any]:
        """
        Deduplicates, merges overlapping sequences, and truncates contexts to stay within the token budget.
        """
        if not chunks:
            return {"context_str": "", "chunks_used": 0, "compressed_ratio": 0.0}

        # 1. Deduplicate by content hash or direct exact string match
        seen_texts = set()
        deduped_chunks = []
        
        for c in chunks:
            text = c.get("text", c.get("content", "")).strip()
            # Normalize text for deduplication
            norm_text = "".join(text.split()).lower()
            if norm_text not in seen_texts and len(text) > 0:
                seen_texts.add(norm_text)
                deduped_chunks.append(c)

        # 2. Merge adjacent chunks of the same file
        # Sort chunks by source file path and chunk index
        merged_chunks = []
        # Group by file path
        by_file = {}
        for c in deduped_chunks:
            fpath = c.get("file_path", c.get("metadata", {}).get("source", "unknown"))
            by_file.setdefault(fpath, []).append(c)

        for fpath, file_chunks in by_file.items():
            # Sort by chunk_index
            file_chunks.sort(key=lambda x: x.get("chunk_index", 0))
            
            curr_merged = None
            for c in file_chunks:
                if curr_merged is None:
                    curr_merged = dict(c)
                else:
                    curr_idx = curr_merged.get("chunk_index", 0)
                    next_idx = c.get("chunk_index", 0)
                    # If chunk indices are adjacent, merge contents
                    if next_idx == curr_idx + 1:
                        c_text = c.get("text", c.get("content", ""))
                        curr_merged["text"] = curr_merged.get("text", curr_merged.get("content", "")) + "\n" + c_text
                        curr_merged["chunk_index"] = next_idx
                        # Average score
                        curr_merged["score"] = (curr_merged.get("score", 0.0) + c.get("score", 0.0)) / 2.0
                    else:
                        merged_chunks.append(curr_merged)
                        curr_merged = dict(c)
            if curr_merged:
                merged_chunks.append(curr_merged)

        # Sort all chunks by relevance score descending
        merged_chunks.sort(key=lambda x: x.get("score", 1.0), reverse=True)

        # 3. Pack within token budget (4 chars approx = 1 token)
        max_chars = self.max_tokens * 4
        current_chars = 0
        final_chunks = []

        for c in merged_chunks:
            text = c.get("text", c.get("content", ""))
            fpath = c.get("file_path", c.get("metadata", {}).get("source", "unknown"))
            idx = c.get("chunk_index", 0)
            
            formatted = f"Source: {fpath} (Index: {idx})\nContent: {text}\n---\n"
            if current_chars + len(formatted) <= max_chars:
                final_chunks.append(formatted)
                current_chars += len(formatted)
            else:
                # Add truncated portion
                remaining = max_chars - current_chars
                if remaining > 100:
                    truncated_text = text[:remaining - 50] + "... [truncated due to token budget]"
                    formatted_trunc = f"Source: {fpath} (Index: {idx})\nContent: {truncated_text}\n---\n"
                    final_chunks.append(formatted_trunc)
                    current_chars += len(formatted_trunc)
                break

        context_str = "".join(final_chunks)
        raw_size = sum(len(c.get("text", c.get("content", ""))) for c in chunks)
        compressed_ratio = 1.0 - (current_chars / raw_size) if raw_size > 0 else 0.0

        return {
            "context_str": context_str,
            "chunks_used": len(final_chunks),
            "compressed_ratio": round(compressed_ratio, 2)
        }
