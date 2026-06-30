# Memory Engine Specification — MSA V5.0

This document describes the design of the conversation memory engine in MSA V5.0.

---

## 1. Storage & Encryption

All user and assistant conversation turns are serialized and persisted in a thread-safe SQLite database (`data/memory/msa.db`).
When encryption is enabled in `config/security.yaml`, text payloads are automatically encrypted using AES-256-GCM before database write.

---

## 2. Memory Recall & Context Assembly

During the `memory_recall` step in the agent workflow:
1. The engine retrieves the last `N` (context window size, default: 10) conversation turns.
2. If the total tokens of the retrieved turns exceed 4096, older turns are summarized to fit the context budget.
3. The formatted memory block is injected into the prompt templates dynamically.
