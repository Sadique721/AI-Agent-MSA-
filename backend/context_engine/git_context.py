"""
backend/context_engine/git_context.py
======================================
Retrieves git context (branch, changes count) for the active workspace.
"""
from __future__ import annotations

import logging
import subprocess
import os

logger = logging.getLogger("msa.context.git")


class GitContext:
    """Extracts repository state dynamically."""

    def __init__(self) -> None:
        pass

    def get_context(self, path: str = ".") -> str:
        """Get git repository branch and status summary."""
        if not os.path.exists(os.path.join(path, ".git")):
            return ""
        try:
            # Branch name
            branch_res = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True, text=True, timeout=2, cwd=path
            )
            branch = branch_res.stdout.strip()
            
            # Short status
            status_res = subprocess.run(
                ["git", "status", "--short"],
                capture_output=True, text=True, timeout=2, cwd=path
            )
            status_lines = [line.strip() for line in status_res.stdout.splitlines() if line.strip()]
            
            if not branch:
                return ""
            
            summary = [f"Git Branch: {branch}"]
            if status_lines:
                summary.append(f"Uncommitted Changes ({len(status_lines)} files):")
                summary.extend([f"  {line}" for line in status_lines[:5]])
                if len(status_lines) > 5:
                    summary.append(f"  ... and {len(status_lines) - 5} more files")
            else:
                summary.append("Working tree clean")
            return "\n".join(summary)
        except Exception as e:
            logger.debug("Failed to read git context: %s", e)
            return ""
