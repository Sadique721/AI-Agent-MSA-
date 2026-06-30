"""
indexes/sqlite_db.py
====================
SQLite-backed metadata store for RAG chunks.
Tracks chunk details and document file hashes for incremental indexing and easy deletions.
"""

import sqlite3
import os
import json
import logging
import threading
from typing import List, Dict, Any, Optional

logger = logging.getLogger("msa.indexes.sqlite_db")


class SQLiteMetadataStore:
    """
    Manages SQLite storage for chunk metadata.
    Coordinates with FAISS vectors using unique IDs.
    """

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            from config import DB_PATH
            self.db_path = DB_PATH
        else:
            self.db_path = db_path
            
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._create_tables()

    def _create_tables(self) -> None:
        """Create the metadata tables if they do not exist."""
        with self._lock:
            # Table to track chunks
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS rag_chunks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    faiss_id INTEGER UNIQUE,
                    file_path TEXT,
                    chunk_index INTEGER,
                    content TEXT,
                    category TEXT,
                    tokens INTEGER,
                    timestamp TEXT,
                    metadata_json TEXT
                )
            """)
            # Table to track file hashes for incremental indexing
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS rag_files (
                    file_path TEXT PRIMARY KEY,
                    file_hash TEXT,
                    timestamp TEXT
                )
            """)
            self._conn.commit()

    def add_chunk(
        self,
        faiss_id: int,
        file_path: str,
        chunk_index: int,
        content: str,
        category: str,
        tokens: int,
        timestamp: str,
        metadata: Dict[str, Any]
    ) -> None:
        """Add metadata for a single chunk."""
        with self._lock:
            self._conn.execute(
                """
                INSERT OR REPLACE INTO rag_chunks 
                (faiss_id, file_path, chunk_index, content, category, tokens, timestamp, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (faiss_id, file_path, chunk_index, content, category, tokens, timestamp, json.dumps(metadata))
            )
            self._conn.commit()

    def get_chunk(self, faiss_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve chunk by FAISS vector index ID."""
        with self._lock:
            row = self._conn.execute(
                "SELECT faiss_id, file_path, chunk_index, content, category, tokens, timestamp, metadata_json "
                "FROM rag_chunks WHERE faiss_id = ?",
                (faiss_id,)
            ).fetchone()
        
        if not row:
            return None

        return {
            "faiss_id": row[0],
            "file_path": row[1],
            "chunk_index": row[2],
            "text": row[3],  # return content as 'text' to match recall expectation
            "content": row[3],
            "category": row[4],
            "tokens": row[5],
            "timestamp": row[6],
            "metadata": json.loads(row[7]) if row[7] else {}
        }

    def get_all_chunks(self) -> List[Dict[str, Any]]:
        """Retrieve all stored chunks."""
        with self._lock:
            rows = self._conn.execute(
                "SELECT faiss_id, file_path, chunk_index, content, category, tokens, timestamp, metadata_json "
                "FROM rag_chunks"
            ).fetchall()

        results = []
        for row in rows:
            results.append({
                "faiss_id": row[0],
                "file_path": row[1],
                "chunk_index": row[2],
                "text": row[3],
                "content": row[3],
                "category": row[4],
                "tokens": row[5],
                "timestamp": row[6],
                "metadata": json.loads(row[7]) if row[7] else {}
            })
        return results

    def get_chunks_for_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Retrieve all chunks associated with a specific file."""
        with self._lock:
            rows = self._conn.execute(
                "SELECT faiss_id, file_path, chunk_index, content, category, tokens, timestamp, metadata_json "
                "FROM rag_chunks WHERE file_path = ?",
                (file_path,)
            ).fetchall()

        results = []
        for row in rows:
            results.append({
                "faiss_id": row[0],
                "file_path": row[1],
                "chunk_index": row[2],
                "text": row[3],
                "content": row[3],
                "category": row[4],
                "tokens": row[5],
                "timestamp": row[6],
                "metadata": json.loads(row[7]) if row[7] else {}
            })
        return results

    def delete_chunks_for_file(self, file_path: str) -> List[int]:
        """Delete all chunks for a file, returning the deleted FAISS IDs."""
        with self._lock:
            cursor = self._conn.execute("SELECT faiss_id FROM rag_chunks WHERE file_path = ?", (file_path,))
            faiss_ids = [row[0] for row in cursor.fetchall()]
            
            self._conn.execute("DELETE FROM rag_chunks WHERE file_path = ?", (file_path,))
            self._conn.execute("DELETE FROM rag_files WHERE file_path = ?", (file_path,))
            self._conn.commit()
            
        logger.info("SQLite: deleted %d chunks for file '%s'", len(faiss_ids), file_path)
        return faiss_ids

    def get_file_hash(self, file_path: str) -> Optional[str]:
        """Get the last processed hash of a file."""
        with self._lock:
            row = self._conn.execute("SELECT file_hash FROM rag_files WHERE file_path = ?", (file_path,)).fetchone()
        return row[0] if row else None

    def update_file_hash(self, file_path: str, file_hash: str, timestamp: str) -> None:
        """Update file hash for incremental indexing tracking."""
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO rag_files (file_path, file_hash, timestamp) VALUES (?, ?, ?)",
                (file_path, file_hash, timestamp)
            )
            self._conn.commit()

    def get_stats(self) -> Dict[str, Any]:
        """Get database stats."""
        with self._lock:
            total_chunks = self._conn.execute("SELECT COUNT(*) FROM rag_chunks").fetchone()[0]
            total_files = self._conn.execute("SELECT COUNT(*) FROM rag_files").fetchone()[0]
            categories_rows = self._conn.execute("SELECT category, COUNT(*) FROM rag_chunks GROUP BY category").fetchall()
        
        categories = {row[0]: row[1] for row in categories_rows}
        return {
            "total_chunks": total_chunks,
            "total_files": total_files,
            "by_category": categories
        }

    def clear(self) -> None:
        """Clear all tables."""
        with self._lock:
            self._conn.execute("DELETE FROM rag_chunks")
            self._conn.execute("DELETE FROM rag_files")
            self._conn.commit()
        logger.info("SQLite: cleared all RAG tables.")

    def close(self) -> None:
        """Close the SQLite database connection."""
        with self._lock:
            self._conn.close()
        logger.info("SQLite: database connection closed.")
