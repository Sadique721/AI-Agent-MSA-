import os
import ast
import sqlite3
import logging
from typing import Dict, Any, List

logger = logging.getLogger("msa.services.code_indexer")

class CodeIndexer:
    def __init__(self, db_path: str = "data/code_index.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS symbols (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT,
                    symbol_name TEXT,
                    symbol_type TEXT,
                    start_line INTEGER,
                    end_line INTEGER
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_symbol_name ON symbols (symbol_name)")
            conn.commit()

    def index_file(self, file_path: str):
        if not file_path.endswith(".py"):
            return
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                source = f.read()
            tree = ast.parse(source, filename=file_path)
            
            symbols = []
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    symbols.append((file_path, node.name, "class", node.lineno, getattr(node, "end_lineno", node.lineno)))
                elif isinstance(node, ast.FunctionDef):
                    symbols.append((file_path, node.name, "function", node.lineno, getattr(node, "end_lineno", node.lineno)))
                elif isinstance(node, ast.Import):
                    for name in node.names:
                        symbols.append((file_path, name.name, "import", node.lineno, getattr(node, "end_lineno", node.lineno)))
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    for name in node.names:
                        symbols.append((file_path, f"{module}.{name.name}", "import", node.lineno, getattr(node, "end_lineno", node.lineno)))

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM symbols WHERE file_path = ?", (file_path,))
                cursor.executemany("""
                    INSERT INTO symbols (file_path, symbol_name, symbol_type, start_line, end_line)
                    VALUES (?, ?, ?, ?, ?)
                """, symbols)
                conn.commit()
            logger.debug(f"Indexed {len(symbols)} symbols from {file_path}")
        except Exception as e:
            logger.error(f"Failed to index file {file_path}: {e}")

    def index_directory(self, dir_path: str):
        logger.info(f"Indexing directory: {dir_path}")
        for root, _, files in os.walk(dir_path):
            # Skip hidden folders and virtual environments
            if any(part.startswith(".") or part == "venv" or part == "node_modules" for part in Path(root).parts):
                continue
            for file in files:
                if file.endswith(".py"):
                    full_path = os.path.join(root, file)
                    self.index_file(full_path)

    def search_symbols(self, query: str) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT file_path, symbol_name, symbol_type, start_line, end_line
                FROM symbols
                WHERE symbol_name LIKE ?
                LIMIT 50
            """, (f"%{query}%",))
            return [dict(row) for row in cursor.fetchall()]
