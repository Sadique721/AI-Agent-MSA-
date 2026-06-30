"""
knowledge/chunker.py
====================
Configurable Semantic and Sliding Window Chunker for document content.
Groups sentences semantically based on embedding similarity, falling back to sliding-window chunks.
"""

import re
import logging
import numpy as np
from typing import List, Dict, Any, Optional

logger = logging.getLogger("msa.knowledge.chunker")


class Chunker:
    """
    Splits document text into logical, semantic chunks.
    Configurable: chunk_size, chunk_overlap, and embedder for semantic grouping.
    """

    def __init__(
        self,
        chunk_size: int = 500,  # Max characters per chunk (default)
        chunk_overlap: int = 50,  # Overlap in characters (default)
        embedder: Optional[Any] = None,
        hierarchical: bool = True,
        parent_size: int = 2000,
        parent_overlap: int = 200
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.embedder = embedder
        self.hierarchical = hierarchical
        self.parent_size = parent_size
        self.parent_overlap = parent_overlap

    def chunk_document(self, doc_text: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Split a document into chunks.
        If hierarchical is True, it first creates large parent chunks,
        then splits each parent into smaller child chunks, embedding the children
        but linking them back to the parents.
        """
        if not doc_text or not doc_text.strip():
            return []

        if self.hierarchical:
            # 1. Create parent chunks
            temp_chunk_size = self.chunk_size
            temp_chunk_overlap = self.chunk_overlap
            
            # Temporarily configure chunker for parent chunking
            self.chunk_size = self.parent_size
            self.chunk_overlap = self.parent_overlap
            
            parents = self._sliding_window_chunking(doc_text, metadata)
            
            # Revert config
            self.chunk_size = temp_chunk_size
            self.chunk_overlap = temp_chunk_overlap
            
            child_chunks = []
            child_idx = 0
            for p_idx, parent in enumerate(parents):
                parent_text = parent["text"]
                # 2. Slice each parent into child chunks
                children = self._sliding_window_chunking(parent_text, metadata)
                for child in children:
                    child_meta = dict(child["metadata"])
                    child_meta["parent_text"] = parent_text
                    child_meta["parent_index"] = p_idx
                    child_meta["is_child"] = True
                    
                    child_chunks.append({
                        "text": child["text"],
                        "tokens": child["tokens"],
                        "metadata": child_meta,
                        "chunk_index": child_idx
                    })
                    child_idx += 1
            return child_chunks

        # Try semantic chunking if embedder is active
        if self.embedder and hasattr(self.embedder, "is_semantic") and self.embedder.is_semantic():
            try:
                return self._semantic_chunking(doc_text, metadata)
            except Exception as e:
                logger.error("Chunker: semantic chunking failed (%s). Falling back to sliding window.", e)

        return self._sliding_window_chunking(doc_text, metadata)

    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences using simple regex boundaries."""
        sentence_end = re.compile(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|\!)\s+')
        sentences = sentence_end.split(text)
        return [s.strip() for s in sentences if s.strip()]

    def _semantic_chunking(self, text: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Groups sentences based on cosine similarity of their embeddings.
        Splits when similarity drops significantly.
        """
        sentences = self._split_into_sentences(text)
        if not sentences:
            return []

        # If we have very few sentences, treat them as a single chunk
        if len(sentences) <= 2:
            return [{
                "text": text,
                "tokens": len(text.split()),
                "metadata": metadata,
                "chunk_index": 0
            }]

        # Generate embeddings for each sentence
        embeddings = self.embedder.embed_batch(sentences)
        
        # Calculate cosine similarities between adjacent sentences
        # Since vectors from embedder are L2 normalized, similarity = dot product
        similarities = []
        for i in range(len(sentences) - 1):
            vec1 = embeddings[i]
            vec2 = embeddings[i + 1]
            sim = float(np.dot(vec1, vec2))
            similarities.append(sim)

        # Determine split points where similarity is below a dynamic threshold
        # Threshold: mean similarity - 1.0 * standard deviation (or 0.5 minimum)
        if similarities:
            import numpy as np_stats
            mean_sim = np_stats.mean(similarities)
            std_sim = np_stats.std(similarities)
            threshold = max(0.4, mean_sim - std_sim)
        else:
            threshold = 0.5

        chunks = []
        current_chunk_sentences = []
        current_chunk_len = 0
        chunk_idx = 0

        for i, sentence in enumerate(sentences):
            current_chunk_sentences.append(sentence)
            current_chunk_len += len(sentence)

            # Check if we should split
            # Split conditions:
            # 1. We reached the last sentence
            # 2. The next sentence similarity is below threshold AND current chunk is large enough
            # 3. The current chunk exceeds self.chunk_size
            should_split = False
            if i == len(sentences) - 1:
                should_split = True
            elif current_chunk_len >= self.chunk_size:
                should_split = True
            elif similarities[i] < threshold and current_chunk_len >= self.chunk_size // 2:
                should_split = True

            if should_split:
                chunk_text = " ".join(current_chunk_sentences)
                chunks.append({
                    "text": chunk_text,
                    "tokens": len(chunk_text.split()),
                    "metadata": dict(metadata),
                    "chunk_index": chunk_idx
                })
                chunk_idx += 1
                
                # Setup overlap: keep last N sentences for overlap if current chunk is split
                overlap_len = 0
                overlap_sentences = []
                # Traverse backwards to collect overlapping sentences up to self.chunk_overlap
                for s in reversed(current_chunk_sentences):
                    if overlap_len + len(s) > self.chunk_overlap:
                        break
                    overlap_sentences.insert(0, s)
                    overlap_len += len(s)

                current_chunk_sentences = overlap_sentences
                current_chunk_len = overlap_len

        return chunks

    def _sliding_window_chunking(self, text: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Fall back to simple character-based sliding window chunking with configurable overlap.
        """
        chunks = []
        start = 0
        chunk_idx = 0
        text_len = len(text)

        # Safeguard to prevent infinite loops if overlap is greater than or equal to chunk_size
        overlap = min(self.chunk_overlap, self.chunk_size - 5)
        if overlap < 0:
            overlap = 0

        while start < text_len:
            end = min(start + self.chunk_size, text_len)
            
            # Try to align end of chunk with a space/newline to avoid cutting words
            if end < text_len:
                while end > start and text[end] not in (" ", "\n", "\t", ".", "?", "!"):
                    end -= 1
                if end == start:  # No space found, force split
                    end = start + self.chunk_size

            chunk_text = text[start:end].strip()
            if chunk_text:
                chunks.append({
                    "text": chunk_text,
                    "tokens": len(chunk_text.split()),
                    "metadata": dict(metadata),
                    "chunk_index": chunk_idx
                })
                chunk_idx += 1

            # Move start pointer forward considering overlap
            next_start = end - overlap
            if next_start <= start:
                # Force progress to prevent infinite loop
                start = start + max(1, self.chunk_size // 5)
            else:
                start = next_start

            if start >= text_len or end == text_len:
                break

        return chunks
