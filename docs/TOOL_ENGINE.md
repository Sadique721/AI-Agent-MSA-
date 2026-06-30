# Tool Engine & Sandboxing Specification — MSA V5.0

This document defines the tool execution architecture and subprocess sandboxing guidelines in MSA V5.0.

---

## 1. Tool Registry

Built-in tools are registered under `ToolRegistry` in `agent/tool_agent.py`:
- **filesystem_read / filesystem_write / filesystem_list**: safe read/write operations.
- **terminal**: executes shell commands in a sandboxed subprocess.
- **web_search**: fetches external query results.
- **git_status / git_diff**: retrieves repository diffs.

---

## 2. Sandbox Subprocesses

When `sandbox_enabled: true` is set in `config/agents.yaml`:
1. Subprocesses are initialized with restricted user groups and environment scopes.
2. Direct terminal calls timeout automatically after 30 seconds to prevent resource exhaustion.
3. Access to root folders, Windows registries, or sensitive system files is blocked at the permission gate.
