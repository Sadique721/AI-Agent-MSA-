# Security Policy & Guardrails — MSA V5.0

This document outlines the security architecture and Zero-Trust tool execution safeguards built into MSA AI Agent V5.0.

---

## 1. Zero-Trust Tool Model

Every tool call (e.g. terminal command, filesystem edit, git push) is validated by the `PermissionGuard` against rules defined in `config/security.yaml`.

### Safeguard Levels:
1. **Safe Mode:** Completely disables terminal commands and write access, allowing only read-only query operations.
2. **Directory Whitelist:** Filesystem tools are restricted to workspace data, plugin, and prompt paths, protecting OS-critical directories.
3. **Command Blacklist:** Destructive patterns such as `rm -rf`, `format`, `del /f` are blocked immediately at the API gate.

---

## 2. JWT Authentication

Endpoints on the FastAPI port 8000 require JWT bearer tokens when `enable_jwt_auth: true` is configured. This prevents unauthorized applications from invoking agent workflows or executing local commands.
