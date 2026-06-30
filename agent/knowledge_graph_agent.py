"""
agent/knowledge_graph_agent.py
================================
Knowledge Graph Agent for MSA AI Agent V5.0.
Uses networkx in-memory graph by default.
Upgrades to Neo4j when enable_neo4j: true in features.yaml.
"""
from __future__ import annotations

import json
import logging
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

logger = logging.getLogger("msa.agent.kg")

try:
    import networkx as nx  # type: ignore
    _nx_ok = True
except ImportError:
    nx = None  # type: ignore
    _nx_ok = False


class KnowledgeGraphAgent:
    """
    Manages a knowledge graph of entities and relationships.

    Backends:
      - networkx  (default, in-memory, no extra services needed)
      - neo4j     (enabled via feature flag)

    The graph stores:
      - Nodes: entities (concepts, code symbols, topics, files, URLs)
      - Edges: relationships (imports, related_to, causes, uses, defines, etc.)
    """

    def __init__(self, backend: str = "networkx", neo4j_config: Optional[Dict] = None) -> None:
        self.backend = backend
        self._graph = None
        self._neo4j = None

        if backend == "neo4j" and neo4j_config:
            self._init_neo4j(neo4j_config)
        if backend in ("networkx", "fallback") or self._neo4j is None:
            self._init_networkx()

    def _init_networkx(self) -> None:
        if not _nx_ok:
            logger.warning("networkx not installed — KG functionality disabled")
            return
        self._graph = nx.DiGraph()
        logger.info("Knowledge graph initialized (networkx backend)")

    def _init_neo4j(self, config: Dict) -> None:
        try:
            from neo4j import GraphDatabase  # type: ignore
            uri = config.get("uri", "bolt://localhost:7687")
            user = config.get("user", "neo4j")
            password = config.get("password", "password")
            self._neo4j = GraphDatabase.driver(uri, auth=(user, password))
            self._neo4j.verify_connectivity()
            logger.info("Neo4j knowledge graph connected: %s", uri)
        except Exception as e:
            logger.warning("Neo4j unavailable (%s) — falling back to networkx", e)
            self._neo4j = None

    # ── Entity Management ─────────────────────────────────────────────────────
    def add_entity(
        self, entity_id: str, entity_type: str,
        properties: Optional[Dict] = None,
    ) -> None:
        """Add or update an entity node."""
        props = properties or {}
        if self._neo4j:
            with self._neo4j.session() as session:
                session.run(
                    f"MERGE (n:{entity_type} {{id: $id}}) SET n += $props",
                    id=entity_id, props=props,
                )
        elif self._graph is not None:
            self._graph.add_node(entity_id, type=entity_type, **props)

    def add_relationship(
        self,
        source_id: str,
        target_id: str,
        relation: str,
        properties: Optional[Dict] = None,
    ) -> None:
        """Add a directed relationship between two entities."""
        props = properties or {}
        if self._neo4j:
            with self._neo4j.session() as session:
                session.run(
                    f"""
                    MATCH (a {{id: $src}}), (b {{id: $tgt}})
                    MERGE (a)-[r:{relation}]->(b)
                    SET r += $props
                    """,
                    src=source_id, tgt=target_id, props=props,
                )
        elif self._graph is not None:
            self._graph.add_edge(source_id, target_id, relation=relation, **props)

    # ── Query ─────────────────────────────────────────────────────────────────
    def find_related(
        self, entity_id: str, max_hops: int = 2, max_results: int = 20
    ) -> List[Dict]:
        """Find entities related to the given entity within max_hops."""
        if self._neo4j:
            return self._neo4j_find_related(entity_id, max_hops, max_results)
        return self._nx_find_related(entity_id, max_hops, max_results)

    def _nx_find_related(self, entity_id: str, max_hops: int, max_results: int) -> List[Dict]:
        if not self._graph or entity_id not in self._graph:
            return []
        try:
            # BFS up to max_hops
            visited = {entity_id}
            frontier = [entity_id]
            results = []

            for _ in range(max_hops):
                next_frontier = []
                for node in frontier:
                    for neighbor in list(self._graph.successors(node)) + list(self._graph.predecessors(node)):
                        if neighbor not in visited:
                            visited.add(neighbor)
                            next_frontier.append(neighbor)
                            node_data = dict(self._graph.nodes[neighbor])
                            results.append({"id": neighbor, **node_data})
                            if len(results) >= max_results:
                                return results
                frontier = next_frontier
            return results
        except Exception as e:
            logger.warning("KG graph traversal error: %s", e)
            return []

    def _neo4j_find_related(self, entity_id: str, max_hops: int, max_results: int) -> List[Dict]:
        try:
            with self._neo4j.session() as session:
                result = session.run(
                    f"""
                    MATCH (start {{id: $id}})-[*1..{max_hops}]-(related)
                    RETURN DISTINCT related LIMIT {max_results}
                    """,
                    id=entity_id,
                )
                return [dict(record["related"]) for record in result]
        except Exception as e:
            logger.warning("Neo4j query error: %s", e)
            return []

    def search_entities(self, query: str, entity_type: Optional[str] = None, limit: int = 10) -> List[Dict]:
        """Full-text search over entity properties."""
        if not self._graph:
            return []
        query_lower = query.lower()
        results = []
        for node_id, data in self._graph.nodes(data=True):
            if entity_type and data.get("type") != entity_type:
                continue
            # Match against node id and all string properties
            searchable = " ".join([str(node_id)] + [str(v) for v in data.values()])
            if query_lower in searchable.lower():
                results.append({"id": node_id, **data})
                if len(results) >= limit:
                    break
        return results

    def format_context(self, entities: List[Dict], query: str) -> str:
        """Format graph results into a prompt-injectable context string."""
        if not entities:
            return ""
        lines = [f"[Knowledge Graph: related to '{query}']"]
        for e in entities:
            eid = e.get("id", "unknown")
            etype = e.get("type", "entity")
            lines.append(f"  [{etype}] {eid}")
        return "\n".join(lines)

    def get_stats(self) -> Dict:
        if self._graph is not None:
            return {
                "backend": "networkx",
                "nodes": self._graph.number_of_nodes(),
                "edges": self._graph.number_of_edges(),
            }
        return {"backend": "neo4j" if self._neo4j else "none", "nodes": -1, "edges": -1}


# ── Module singleton ──────────────────────────────────────────────────────────
_kg_agent: Optional[KnowledgeGraphAgent] = None


def get_kg_agent(backend: str = "networkx", neo4j_config: Optional[Dict] = None) -> KnowledgeGraphAgent:
    global _kg_agent
    if _kg_agent is None:
        _kg_agent = KnowledgeGraphAgent(backend=backend, neo4j_config=neo4j_config)
    return _kg_agent
