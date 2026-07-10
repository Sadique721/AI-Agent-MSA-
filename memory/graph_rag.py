"""
memory/graph_rag.py
====================
Combines the existing FAISS vector search with an OPTIONAL Neo4j graph
layer for relationship-aware retrieval (e.g. "what depends on X").
Neo4j is entirely optional — if it's not installed/running, this silently
falls back to vector-only results. No hard dependency is added.
"""
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger("msa.graph_rag")


class GraphRAGCore:
    def __init__(self, vector_store, neo4j_uri: Optional[str] = None,
                 neo4j_user: Optional[str] = None, neo4j_password: Optional[str] = None):
        self.vector_store = vector_store
        self.graph_driver = None
        if neo4j_uri:
            try:
                from neo4j import GraphDatabase
                self.graph_driver = GraphDatabase.driver(
                    neo4j_uri, auth=(neo4j_user, neo4j_password)
                )
                # Verify connectivity immediately so failures surface at init, not query time
                self.graph_driver.verify_connectivity()
                logger.info("GraphRAG: Neo4j connected at %s", neo4j_uri)
            except Exception as e:
                logger.info("GraphRAG: Neo4j unavailable (%s) — using vector-only retrieval.", e)
                self.graph_driver = None

    def query_hybrid(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        vector_results = []
        if hasattr(self.vector_store, "search"):
            try:
                vector_results = self.vector_store.search(query, top_k=top_k)
            except Exception as e:
                logger.warning("Vector search failed: %s", e)

        graph_results = []
        if self.graph_driver:
            try:
                with self.graph_driver.session() as session:
                    rows = session.run(
                        "MATCH (a)-[r]->(b) WHERE toLower(a.name) CONTAINS toLower($q) "
                        "RETURN a.name AS src, type(r) AS rel, b.name AS dst LIMIT 20",
                        q=query,
                    )
                    graph_results = [f"({row['src']})-[{row['rel']}]->({row['dst']})" for row in rows]
            except Exception as e:
                logger.warning("Graph query failed: %s", e)

        return {
            "vector_results": vector_results,
            "graph_results": graph_results,
            "summary": f"{len(vector_results)} vector matches, {len(graph_results)} graph relations.",
        }

    def close(self):
        if self.graph_driver:
            self.graph_driver.close()
