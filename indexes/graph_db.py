"""
indexes/graph_db.py
===================
Persistent, thread-safe SQLite storage for the Knowledge Graph.
Tracks entities, relationships, document/repository mappings, and supports traversal queries.
"""

import os
import json
import sqlite3
import logging
import threading
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger("msa.indexes.graph_db")

# Default database path from config or fallback
try:
    from config import DB_PATH
    GRAPH_DB_PATH = DB_PATH.replace("msa_memory.db", "msa_graph.db")
except ImportError:
    GRAPH_DB_PATH = "data/memory/msa_graph.db"


class SQLiteGraphStore:
    """
    Manages Graph nodes and edges within SQLite database with thread-safe connection locking.
    """
    def __init__(self, db_path: str = GRAPH_DB_PATH):
        self.db_path = db_path
        # Ensure target folder exists
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
        """Initializes tables for nodes and edges."""
        with self._lock:
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS graph_nodes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entity_type TEXT NOT NULL,
                    name TEXT NOT NULL,
                    doc_link TEXT,
                    repo_link TEXT,
                    properties_json TEXT,
                    UNIQUE(entity_type, name)
                )
            """)
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS graph_edges (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source INTEGER NOT NULL,
                    target INTEGER NOT NULL,
                    edge_type TEXT NOT NULL,
                    description TEXT,
                    weight REAL DEFAULT 1.0,
                    FOREIGN KEY(source) REFERENCES graph_nodes(id) ON DELETE CASCADE,
                    FOREIGN KEY(target) REFERENCES graph_nodes(id) ON DELETE CASCADE,
                    UNIQUE(source, target, edge_type)
                )
            """)
            # Create indexes for optimal traversals
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_node_name ON graph_nodes(name)")
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_node_type ON graph_nodes(entity_type)")
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_edge_source ON graph_edges(source)")
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_edge_target ON graph_edges(target)")
            self._conn.commit()

    def add_node(
        self,
        entity_type: str,
        name: str,
        doc_link: Optional[str] = None,
        repo_link: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None
    ) -> int:
        """Inserts or updates a node, returning its unique integer ID."""
        props_str = json.dumps(properties or {})
        with self._lock:
            cursor = self._conn.cursor()
            try:
                cursor.execute(
                    """
                    INSERT INTO graph_nodes (entity_type, name, doc_link, repo_link, properties_json)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(entity_type, name) DO UPDATE SET
                        doc_link = COALESCE(excluded.doc_link, doc_link),
                        repo_link = COALESCE(excluded.repo_link, repo_link),
                        properties_json = excluded.properties_json
                    """,
                    (entity_type.strip(), name.strip(), doc_link, repo_link, props_str)
                )
                self._conn.commit()
                # Get the ID
                cursor.execute(
                    "SELECT id FROM graph_nodes WHERE entity_type = ? AND name = ?",
                    (entity_type.strip(), name.strip())
                )
                row = cursor.fetchone()
                return row[0] if row else -1
            except Exception as e:
                logger.error("Failed to add graph node: %s", e)
                return -1

    def add_edge(
        self,
        source_id: int,
        target_id: int,
        edge_type: str,
        description: str = "",
        weight: float = 1.0
    ) -> int:
        """Adds a relationship edge between two node IDs."""
        if source_id == -1 or target_id == -1:
            return -1
        with self._lock:
            cursor = self._conn.cursor()
            try:
                cursor.execute(
                    """
                    INSERT INTO graph_edges (source, target, edge_type, description, weight)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(source, target, edge_type) DO UPDATE SET
                        description = COALESCE(excluded.description, description),
                        weight = excluded.weight
                    """,
                    (source_id, target_id, edge_type.strip(), description.strip(), weight)
                )
                self._conn.commit()
                return cursor.lastrowid or -1
            except Exception as e:
                logger.error("Failed to add graph edge: %s", e)
                return -1

    def get_node(self, node_id: int) -> Optional[Dict[str, Any]]:
        """Retrieves a node by its ID."""
        with self._lock:
            row = self._conn.execute("SELECT * FROM graph_nodes WHERE id = ?", (node_id,)).fetchone()
        if not row:
            return None
        node = dict(row)
        node["properties"] = json.loads(node.pop("properties_json") or "{}")
        return node

    def get_node_by_name(self, name: str, entity_type: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Finds a node by name and optional type constraint."""
        with self._lock:
            if entity_type:
                row = self._conn.execute(
                    "SELECT * FROM graph_nodes WHERE name = ? AND entity_type = ?",
                    (name.strip(), entity_type.strip())
                ).fetchone()
            else:
                row = self._conn.execute("SELECT * FROM graph_nodes WHERE name = ?", (name.strip(),)).fetchone()
        if not row:
            return None
        node = dict(row)
        node["properties"] = json.loads(node.pop("properties_json") or "{}")
        return node

    def get_neighbors(self, node_id: int) -> List[Dict[str, Any]]:
        """Retrieves all adjacent nodes and relation descriptors."""
        neighbors = []
        with self._lock:
            # Query outgoing edges
            out_rows = self._conn.execute(
                """
                SELECT e.edge_type, e.description, e.weight, n.* 
                FROM graph_edges e
                JOIN graph_nodes n ON e.target = n.id
                WHERE e.source = ?
                """,
                (node_id,)
            ).fetchall()
            for r in out_rows:
                n_dict = dict(r)
                n_dict["direction"] = "out"
                n_dict["properties"] = json.loads(n_dict.pop("properties_json") or "{}")
                neighbors.append(n_dict)

            # Query incoming edges
            in_rows = self._conn.execute(
                """
                SELECT e.edge_type, e.description, e.weight, n.* 
                FROM graph_edges e
                JOIN graph_nodes n ON e.source = n.id
                WHERE e.target = ?
                """,
                (node_id,)
            ).fetchall()
            for r in in_rows:
                n_dict = dict(r)
                n_dict["direction"] = "in"
                n_dict["properties"] = json.loads(n_dict.pop("properties_json") or "{}")
                neighbors.append(n_dict)
        return neighbors

    def search_nodes(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Simple keyword search on node names for graph traversals."""
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM graph_nodes WHERE name LIKE ? LIMIT ?",
                (f"%{query.strip()}%", limit)
            ).fetchall()
        results = []
        for r in rows:
            node = dict(r)
            node["properties"] = json.loads(node.pop("properties_json") or "{}")
            results.append(node)
        return results

    def get_graph_export(self) -> Dict[str, List[Dict[str, Any]]]:
        """Exports all nodes and edges for visual rendering."""
        with self._lock:
            nodes_rows = self._conn.execute("SELECT * FROM graph_nodes").fetchall()
            edges_rows = self._conn.execute("SELECT * FROM graph_edges").fetchall()
        
        nodes = []
        for r in nodes_rows:
            node = dict(r)
            node["properties"] = json.loads(node.pop("properties_json") or "{}")
            nodes.append(node)
            
        edges = [dict(r) for r in edges_rows]
        return {"nodes": nodes, "edges": edges}

    def clear(self) -> None:
        """Wipes the knowledge graph database."""
        with self._lock:
            self._conn.execute("DELETE FROM graph_edges")
            self._conn.execute("DELETE FROM graph_nodes")
            self._conn.commit()
        logger.info("SQLite Graph: cleared nodes and edges.")

    def close(self) -> None:
        """Closes connection."""
        with self._lock:
            self._conn.close()
