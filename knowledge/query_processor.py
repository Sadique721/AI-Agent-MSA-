"""
knowledge/query_processor.py
============================
Enterprise Query Processing Engine.
Implements Query Expansion (synonyms/semantics), Query Rewriting (context-aware),
and Multi-Query generation for high-recall document retrieval.
"""

import re
import json
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger("msa.knowledge.query_processor")

SYNONYM_DICT = {
    "spring": ["Spring Boot", "Spring Framework", "Dependency Injection", "REST API", "Hibernate", "Microservices"],
    "rag": ["Retrieval-Augmented Generation", "embeddings", "vector search", "FAISS", "context window", "BM25"],
    "llm": ["Large Language Model", "DeepSeek", "Ollama", "GGUF", "prompt engineering", "inference"],
    "android": ["adb", "emulator", "mobile device", "APK", "Flutter app", "device telemetry"],
    "flutter": ["dart", "mobile app", "WebView", "pubspec.yaml", "scaffolding", "UI widget"],
    "voice": ["Offline speech recognition", "Vosk", "wakeword", "Siamese network", "audio transcript"],
    "vision": ["computer vision", "OpenCV", "image extraction", "template matching", "screenshot"]
}


class QueryProcessor:
    """
    Rewrites and expands natural language queries to maximize recall of the retrieval engine.
    """
    def __init__(self, llm_client: Optional[Any] = None):
        self.llm = llm_client

    def rewrite_query(self, query: str, conversation_history: Optional[List[Dict[str, Any]]] = None) -> str:
        """Corrects typos, clarifies reference variables, and returns a search-optimized query."""
        if not query or not query.strip():
            return ""

        if self.llm:
            try:
                return self._llm_rewrite(query, conversation_history or [])
            except Exception as e:
                logger.warning("LLM query rewrite failed, using local rule-based rewrite: %s", e)

        return self._rule_based_rewrite(query, conversation_history or [])

    def expand_query(self, query: str) -> List[str]:
        """Expands query using synonyms and semantic associations."""
        expanded = [query]
        query_lower = query.lower()

        # Find matching keywords in synonym dictionary
        for key, synonyms in SYNONYM_DICT.items():
            if key in query_lower:
                expanded.extend(synonyms)

        if self.llm:
            try:
                llm_expanded = self._llm_expand(query)
                for item in llm_expanded:
                    if item not in expanded:
                        expanded.append(item)
            except Exception as e:
                logger.warning("LLM query expansion failed: %s", e)

        return list(set(expanded))[:6]

    def generate_multi_queries(self, query: str, count: int = 3) -> List[str]:
        """Generates multiple semantic search variations for parallel/iterative lookup."""
        queries = [query]
        
        if self.llm:
            try:
                llm_queries = self._llm_multi_queries(query, count)
                for q in llm_queries:
                    if q not in queries:
                        queries.append(q)
            except Exception as e:
                logger.warning("LLM multi-query generation failed: %s", e)

        # Heuristic fallbacks if LLM is absent or returned empty
        if len(queries) < count:
            # Word dropping / swapping
            words = [w for w in re.findall(r"\w+", query) if len(w) > 3]
            if len(words) > 2:
                queries.append(" ".join(words[:-1]))
                queries.append(" ".join(words[1:]))
            elif len(words) == 2:
                queries.append(words[0])
                queries.append(words[1])

        return list(set(queries))[:count]

    # ── LLM Assisted Implementations ──────────────────────────────────────────

    def _llm_rewrite(self, query: str, history: List[Dict[str, Any]]) -> str:
        """Asks LLM to resolve pronouns or typos using conversation context."""
        context_str = ""
        if history:
            recent = history[-3:]
            context_str = "\n".join(f"User: {turn.get('user', '')}\nAgent: {turn.get('agent', '')}" for turn in recent)

        prompt = f"""You are a search query optimizer. Rewrite the User Query to be search-engine friendly. 
Resolve pronouns (like 'it', 'them', 'that code') using the recent conversation context if needed.
Correct typos. Do NOT answer the query, just return the optimized query.

Recent Conversation:
{context_str}

User Query: {query}
Optimized Query:"""

        res = self.llm(prompt, max_tokens=128, temperature=0.1)
        return res["choices"][0]["text"].strip()

    def _llm_expand(self, query: str) -> List[str]:
        """Asks LLM to list synonym keywords associated with the query."""
        prompt = f"""Given the search query: '{query}'
List 3 associated technology synonyms or keywords. Return them as a comma-separated list.
Example: 'Spring' -> 'Spring Boot, Dependency Injection, REST API'
List:"""
        res = self.llm(prompt, max_tokens=64, temperature=0.2)
        words = [w.strip() for w in res["choices"][0]["text"].strip().split(",") if w.strip()]
        return words

    def _llm_multi_queries(self, query: str, count: int) -> List[str]:
        """Asks LLM to rewrite the query into search variations."""
        prompt = f"""Generate {count} search query variations for: '{query}'
Return them as a JSON array of strings.
Example: ["query 1", "query 2"]
JSON Array:"""
        res = self.llm(prompt, max_tokens=256, temperature=0.3)
        text = res["choices"][0]["text"].strip()
        start = text.find("[")
        end = text.rfind("]") + 1
        if 0 <= start < end:
            return json.loads(text[start:end])
        return []

    # ── Rule-Based Fallbacks ──────────────────────────────────────────────────

    def _rule_based_rewrite(self, query: str, history: List[Dict[str, Any]]) -> str:
        """Resolves basic reference variables and corrects simple contractions."""
        rewritten = query
        # Remove punctuation marks
        rewritten = re.sub(r"[?!.,]", "", rewritten)
        # Typo/Contraction replacements
        replacements = {
            "dont": "don't",
            "cant": "can't",
            "wont": "won't",
            "rag": "Retrieval-Augmented Generation",
            "db": "database"
        }
        for k, v in replacements.items():
            rewritten = re.sub(rf"\b{k}\b", v, rewritten, flags=re.IGNORECASE)
            
        # Context-aware pronoun replacement via last query keyword
        if history and any(p in rewritten.lower() for p in ["it", "that", "this"]):
            last_turn = history[-1]
            last_user = last_turn.get("user", "")
            # Find first capitalized word or specific keyword in previous user prompt
            found_subject = re.findall(r"\b[A-Z]\w+\b", last_user)
            if found_subject:
                subject = found_subject[0]
                rewritten = re.sub(r"\b(it|that|this)\b", subject, rewritten, flags=re.IGNORECASE)

        return rewritten
