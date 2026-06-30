"""
knowledge/code_rag.py
=====================
AST-Aware Code RAG Engine.
Implements code parsing and tokenizing for 14+ languages (Python, Java, JS, TS, Go, Rust, etc.),
symbol extraction, import graphs, code summarization, and git metadata linkage.
"""

import os
import ast
import re
import subprocess
import logging
from typing import List, Dict, Any, Optional, Set, Tuple

logger = logging.getLogger("msa.knowledge.code_rag")


class CodeRAGEngine:
    """
    Parses code repositories, extracts symbols (classes, functions, imports), and builds dependency graphs.
    """
    def __init__(self):
        # Maps file extensions to programming languages
        self.extension_map = {
            ".py": "python",
            ".java": "java",
            ".js": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".cs": "csharp",
            ".cpp": "cpp",
            ".h": "cpp",
            ".c": "cpp",
            ".go": "go",
            ".rs": "rust",
            ".kt": "kotlin",
            ".dart": "flutter",
            ".sql": "sql",
            ".yaml": "yaml",
            ".yml": "yaml",
            "dockerfile": "dockerfile",
            ".md": "markdown"
        }

    def detect_language(self, filepath: str) -> str:
        """Determines programming language based on file extension or filename."""
        basename = os.path.basename(filepath).lower()
        if basename == "dockerfile":
            return "dockerfile"
        _, ext = os.path.splitext(basename)
        return self.extension_map.get(ext, "text")

    def chunk_code_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Parses a code file and chunks it by classes/functions/modules."""
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                code_text = f.read()
        except Exception as e:
            logger.error("Failed to read code file '%s': %s", file_path, e)
            return []

        lang = self.detect_language(file_path)
        git_meta = self.get_git_metadata(file_path)

        if lang == "python":
            return self._chunk_python_ast(code_text, file_path, git_meta)
        else:
            return self._chunk_regex_structural(code_text, file_path, lang, git_meta)

    def _chunk_python_ast(self, code: str, filepath: str, git_meta: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Uses Python's AST parser to divide file into classes and functions."""
        chunks = []
        try:
            tree = ast.parse(code)
            
            # Module level chunk
            module_doc = ast.get_docstring(tree) or ""
            chunks.append({
                "text": f"# File: {filepath}\n# Module Docs: {module_doc}\n" + code[:1000],
                "chunk_index": 0,
                "tokens": len(code[:1000]) // 4,
                "metadata": {
                    "source": filepath,
                    "language": "python",
                    "type": "module",
                    "docstring": module_doc,
                    **git_meta
                }
            })

            idx = 1
            for node in tree.body:
                if isinstance(node, ast.ClassDef):
                    class_code = ast.get_source_segment(code, node) or ""
                    doc = ast.get_docstring(node) or ""
                    chunks.append({
                        "text": f"# Class: {node.name} in {filepath}\n" + class_code,
                        "chunk_index": idx,
                        "tokens": len(class_code) // 4,
                        "metadata": {
                            "source": filepath,
                            "language": "python",
                            "type": "class",
                            "name": node.name,
                            "docstring": doc,
                            **git_meta
                        }
                    })
                    idx += 1

                elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                    func_code = ast.get_source_segment(code, node) or ""
                    doc = ast.get_docstring(node) or ""
                    chunks.append({
                        "text": f"# Function: {node.name} in {filepath}\n" + func_code,
                        "chunk_index": idx,
                        "tokens": len(func_code) // 4,
                        "metadata": {
                            "source": filepath,
                            "language": "python",
                            "type": "function",
                            "name": node.name,
                            "docstring": doc,
                            **git_meta
                        }
                    })
                    idx += 1
        except Exception as err:
            logger.warning("AST parse failed for '%s' (%s). Falling back to regex chunking.", filepath, err)
            return self._chunk_regex_structural(code, filepath, "python", git_meta)

        return chunks if len(chunks) > 1 else self._chunk_regex_structural(code, filepath, "python", git_meta)

    def _chunk_regex_structural(self, code: str, filepath: str, lang: str, git_meta: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Falls back to regex structure matching for non-python files (Java, JS, Go, Rust)."""
        chunks = []
        lines = code.splitlines()
        
        # Regexes for class & function declarations
        class_rx = re.compile(r"\b(class|struct|interface|enum)\s+(\w+)")
        func_rx = re.compile(r"\b(function|fn|def|func)\s+(\w+)\b|(\w+)\s*\([^)]*\)\s*\{")

        current_chunk = []
        current_type = "module"
        current_name = "global"
        chunk_idx = 0
        line_count = 0

        for line in lines:
            current_chunk.append(line)
            line_count += 1
            
            # Detect structure triggers
            class_match = class_rx.search(line)
            func_match = func_rx.search(line)

            is_split_point = (line_count >= 60) or (class_match) or (func_match and line_count >= 30)

            if is_split_point and len(current_chunk) > 10:
                chunk_text = "\n".join(current_chunk)
                chunks.append({
                    "text": f"// File: {filepath} ({lang})\n// Symbol: {current_name}\n" + chunk_text,
                    "chunk_index": chunk_idx,
                    "tokens": len(chunk_text) // 4,
                    "metadata": {
                        "source": filepath,
                        "language": lang,
                        "type": current_type,
                        "name": current_name,
                        **git_meta
                    }
                })
                chunk_idx += 1
                current_chunk = current_chunk[-5:] # overlap of 5 lines
                line_count = 5
                
                if class_match:
                    current_type = "class"
                    current_name = class_match.group(2)
                elif func_match:
                    current_type = "function"
                    current_name = func_match.group(2) or func_match.group(3) or "anonymous"

        # Add remaining text
        if current_chunk:
            chunk_text = "\n".join(current_chunk)
            chunks.append({
                "text": f"// File: {filepath} ({lang})\n" + chunk_text,
                "chunk_index": chunk_idx,
                "tokens": len(chunk_text) // 4,
                "metadata": {
                    "source": filepath,
                    "language": lang,
                    "type": "module",
                    "name": "footer",
                    **git_meta
                }
            })

        return chunks

    def build_import_graph(self, workspace_path: str) -> Dict[str, List[str]]:
        """Maps file-to-file import dependencies across the workspace."""
        graph = {}
        import_py = re.compile(r"^(?:from\s+(\w+)\s+)?import\s+([\w\s,]+)")
        import_js = re.compile(r"\bimport\s+.*\s+from\s+['\"]([^'\"]+)['\"]")

        for root, _, files in os.walk(workspace_path):
            for file in files:
                lang = self.extension_map.get(os.path.splitext(file)[1])
                if lang not in ["python", "javascript", "typescript"]:
                    continue

                fpath = os.path.join(root, file).replace("\\", "/")
                graph[fpath] = []
                
                try:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        for line in f:
                            line = line.strip()
                            if lang == "python":
                                py_m = import_py.match(line)
                                if py_m:
                                    module = py_m.group(1) or py_m.group(2)
                                    graph[fpath].append(module.split()[0])
                            else:
                                js_m = import_js.search(line)
                                if js_m:
                                    graph[fpath].append(js_m.group(1))
                except Exception:
                    pass

        return graph

    def get_git_metadata(self, filepath: str) -> Dict[str, Any]:
        """Runs Git command locally to get author, commit history, and size parameters."""
        metadata = {
            "git_author": "Unknown",
            "git_last_commit": "N/A",
            "git_modified_date": "N/A"
        }
        
        # Verify git repository exists
        file_dir = os.path.dirname(os.path.abspath(filepath))
        try:
            # Check if directory is in git repo
            in_git = subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                cwd=file_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=2
            )
            if in_git.returncode == 0 and "true" in in_git.stdout.lower():
                # Get last author & date
                log_cmd = subprocess.run(
                    ["git", "log", "-n", "1", "--pretty=format:%an|%s|%ad", "--", filepath],
                    cwd=file_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=2
                )
                if log_cmd.returncode == 0 and log_cmd.stdout.strip():
                    parts = log_cmd.stdout.strip().split("|")
                    if len(parts) >= 3:
                        metadata["git_author"] = parts[0]
                        metadata["git_last_commit"] = parts[1]
                        metadata["git_modified_date"] = parts[2]
        except Exception:
            pass # Git command not installed or timeout

        return metadata
