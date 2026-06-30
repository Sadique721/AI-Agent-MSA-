"""
knowledge/graph_rag.py
======================
Enterprise Graph RAG Engine.
Performs entity and relationship extraction (LLM-based with high-performance regex/lexical fallbacks),
semantic graph traversal, and multi-hop query context construction.
"""

import re
import json
import logging
from typing import List, Dict, Any, Optional, Set, Tuple

from indexes.graph_db import SQLiteGraphStore

logger = logging.getLogger("msa.knowledge.graph_rag")

VALID_ENTITY_TYPES = {
    "Person", "Organization", "Location", "Project", "Repository", 
    "API", "Class", "Method", "Function", "Database", "Table", 
    "Documentation", "Technology", "Library", "Framework"
}

# Synonyms/keywords for fallback regex entity matching
TECH_KEYWORDS = {"python", "java", "javascript", "typescript", "rust", "go", "flutter", "sqlite", "faiss", "flask", "websocket", "docker", "spring", "react"}
ORG_KEYWORDS = {"google", "deepmind", "github", "microsoft", "openai", "meta", "huggingface"}


class GraphRAGEngine:
    """
    Handles extraction of nodes/relationships and traverses the knowledge graph to build multi-hop context.
    """
    def __init__(self, graph_store: Optional[SQLiteGraphStore] = None, llm_client: Optional[Any] = None):
        self.store = graph_store or SQLiteGraphStore()
        self.llm = llm_client

    def extract_and_index(self, text: str, source_doc: Optional[str] = None, repo_link: Optional[str] = None) -> None:
        """Extracts entities and relationships, then saves them to the persistent graph db."""
        if not text or not text.strip():
            return

        entities, relations = self._extract_entities_and_relations(text)

        # 1. Store nodes
        node_ids = {}
        for entity in entities:
            name = entity.get("name")
            etype = entity.get("type")
            if not name or not etype:
                continue
            if etype not in VALID_ENTITY_TYPES:
                # Map to closest matching type or default to Technology
                etype = "Technology"

            props = entity.get("properties", {})
            if source_doc:
                props["source"] = source_doc

            nid = self.store.add_node(
                entity_type=etype,
                name=name,
                doc_link=source_doc,
                repo_link=repo_link,
                properties=props
            )
            if nid != -1:
                node_ids[(etype, name)] = nid

        # 2. Store edges
        for rel in relations:
            src = rel.get("source")
            src_type = rel.get("source_type", "Technology")
            tgt = rel.get("target")
            tgt_type = rel.get("target_type", "Technology")
            rtype = rel.get("type", "ASSOCIATED_WITH")
            desc = rel.get("description", "")

            src_id = node_ids.get((src_type, src))
            if not src_id:
                # Try finding or inserting on the fly
                src_id = self.store.add_node(src_type, src, doc_link=source_doc, repo_link=repo_link)
                node_ids[(src_type, src)] = src_id

            tgt_id = node_ids.get((tgt_type, tgt))
            if not tgt_id:
                tgt_id = self.store.add_node(tgt_type, tgt, doc_link=source_doc, repo_link=repo_link)
                node_ids[(tgt_type, tgt)] = tgt_id

            if src_id != -1 and tgt_id != -1:
                self.store.add_edge(
                    source_id=src_id,
                    target_id=tgt_id,
                    edge_type=rtype,
                    description=desc,
                    weight=rel.get("weight", 1.0)
                )

    def retrieve_context(self, query: str, max_depth: int = 2, max_nodes: int = 15) -> Dict[str, Any]:
        """
        Locates seed nodes matching the query, performs multi-hop traversal, and compiles context.
        """
        # Find seed nodes via name matches
        seeds = self.store.search_nodes(query, limit=3)
        if not seeds:
            # Try splitting query terms
            terms = [t for t in re.findall(r"\w+", query) if len(t) > 3]
            for term in terms:
                seeds.extend(self.store.search_nodes(term, limit=2))
        
        # De-duplicate seeds
        seen_ids = set()
        unique_seeds = []
        for s in seeds:
            if s["id"] not in seen_ids:
                seen_ids.add(s["id"])
                unique_seeds.append(s)

        if not unique_seeds:
            return {"context_str": "", "nodes_visited": 0, "entities": []}

        # Multi-hop DFS/BFS traversal
        visited_nodes = {}
        relationships_found = []
        queue = [(node["id"], 0) for node in unique_seeds]

        while queue and len(visited_nodes) < max_nodes:
            curr_id, depth = queue.pop(0)
            if curr_id in visited_nodes:
                continue

            node_data = self.store.get_node(curr_id)
            if not node_data:
                continue

            visited_nodes[curr_id] = node_data

            if depth < max_depth:
                neighbors = self.store.get_neighbors(curr_id)
                for neighbor in neighbors:
                    neigh_id = neighbor["id"]
                    relationships_found.append({
                        "source": node_data["name"],
                        "target": neighbor["name"],
                        "type": neighbor["edge_type"],
                        "description": neighbor.get("description", "")
                    })
                    if neigh_id not in visited_nodes:
                        queue.append((neigh_id, depth + 1))

        # Format textual representation
        lines = []
        lines.append("=== KNOWLEDGE GRAPH CONTEXT ===")
        lines.append("Entities Identified:")
        for nid, n in visited_nodes.items():
            props_str = ", ".join(f"{k}: {v}" for k, v in n["properties"].items())
            props_suffix = f" ({props_str})" if props_str else ""
            lines.append(f"- [{n['entity_type']}] {n['name']}{props_suffix}")

        lines.append("\nRelationships Found:")
        # De-duplicate relationships
        seen_rels = set()
        for r in relationships_found:
            rel_key = tuple(sorted([r["source"], r["target"]])) + (r["type"],)
            if rel_key not in seen_rels:
                seen_rels.add(rel_key)
                desc = f" ({r['description']})" if r["description"] else ""
                lines.append(f"- {r['source']} --[{r['type']}]--> {r['target']}{desc}")

        context_str = "\n".join(lines) if len(visited_nodes) > 0 else ""
        return {
            "context_str": context_str,
            "nodes_visited": len(visited_nodes),
            "entities": [n["name"] for n in visited_nodes.values()]
        }

    def _extract_entities_and_relations(self, text: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Extracts nodes and relations. Tries LLM first, falls back to AST/regex rules."""
        if self.llm:
            try:
                return self._llm_extract(text)
            except Exception as e:
                logger.warning("LLM graph extraction failed, falling back to rule-based: %s", e)
        return self._rule_based_extract(text)

    def _llm_extract(self, text: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Calls the local LLM to perform structured extraction."""
        prompt = f"""Extract entities and their relationships from this text.
Return ONLY valid JSON with this exact structure:
{{
  "entities": [
    {{"name": "entity name", "type": "Person|Organization|Location|Project|Repository|API|Class|Method|Function|Database|Table|Documentation|Technology|Library|Framework", "properties": {{}}}}
  ],
  "relations": [
    {{"source": "source name", "source_type": "source entity type", "target": "target name", "target_type": "target entity type", "type": "CONNECTED_TO|DEPENDS_ON|IMPLEMENTS|USES|LOCATED_IN|WORKS_AT", "description": "relation details"}}
  ]
}}
Text to extract:
{text[:2000]}"""

        res = self.llm(prompt, max_tokens=1024, temperature=0.1)
        resp_text = res["choices"][0]["text"].strip()
        
        start = resp_text.find("{")
        end = resp_text.rfind("}") + 1
        if 0 <= start < end:
            data = json.loads(resp_text[start:end])
            return data.get("entities", []), data.get("relations", [])
        return [], []

    def _rule_based_extract(self, text: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """High-performance regex/lexical entity and relationship extractor fallback."""
        entities = []
        relations = []
        
        # 1. Match code definitions (classes and functions)
        class_matches = re.findall(r"\bclass\s+(\w+)\b", text)
        for name in class_matches:
            entities.append({"name": name, "type": "Class", "properties": {}})

        func_matches = re.findall(r"\bdef\s+(\w+)\b", text)
        for name in func_matches:
            entities.append({"name": name, "type": "Function", "properties": {}})

        # 2. Match known technologies and organizations
        words = re.findall(r"\b[A-Za-z0-9\-\.]+\b", text)
        found_techs = set()
        found_orgs = set()

        for w in words:
            wl = w.lower()
            if wl in TECH_KEYWORDS:
                found_techs.add(w)
            elif wl in ORG_KEYWORDS:
                found_orgs.add(w)

        for tech in found_techs:
            entities.append({"name": tech, "type": "Technology", "properties": {}})
        for org in found_orgs:
            entities.append({"name": org, "type": "Organization", "properties": {}})

        # 3. Form basic connections
        # Connect classes to functions defined in the same chunk
        for c in class_matches:
            for f in func_matches:
                relations.append({
                    "source": c,
                    "source_type": "Class",
                    "target": f,
                    "target_type": "Function",
                    "type": "CONTAINS",
                    "description": f"Class {c} defines function {f}"
                })

        # Connect tech to organization (e.g. Flutter -> Google)
        for tech in found_techs:
            for org in found_orgs:
                relations.append({
                    "source": tech,
                    "source_type": "Technology",
                    "target": org,
                    "target_type": "Organization",
                    "type": "CREATED_BY",
                    "description": f"{tech} is managed/created by {org}"
                })

        return entities, relations
