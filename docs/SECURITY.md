# Security Architecture — MSA V5.0

This document describes the security boundaries and Zero-Trust architecture in MSA V5.0.

---

## 1. Gateway Isolation

FastAPI servers run in isolated python processes and bind only to localhost (`127.0.0.1`) in production.
JWT bearer tokens are validated for all requests, preventing unauthorized cross-origin requests from the browser or secondary desktop apps.

---

## 2. subprocess Sandboxing

When tools are invoked:
- Executable paths are validated against allowed targets in `config/security.yaml`.
- Shell execution runs in a sandboxed, low-privilege environment.
- Subprocess CPU limits are checked periodically.
- Hardcoded command block lists protect root directories.
