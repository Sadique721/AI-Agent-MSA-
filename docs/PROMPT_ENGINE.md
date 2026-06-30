# Prompt Engine Specification — MSA V5.0

This document defines the template structure and compilation behaviors of the Prompt Engine in MSA V5.0.

---

## 1. Loader & Caching

The `PromptLoader` (`backend/shared/prompt_loader.py`) loads templates from `prompts/` and caches them in memory.
It watches for file modifications (re-reading files when cache keys are invalidated) to support hot-reloading during development.

---

## 2. Compilation Syntax

All prompt files support double-brace variable placeholders:
```markdown
You are the {{persona}} assistant.
RAG context:
{{rag_context}}
```

During execution, variables are replaced via `template.replace()`. Unresolved keys raise a debug logger warning.
```python
loader = get_prompt_loader()
compiled = loader.render("planner", persona="developer", rag_context="...")
```
 obituary
 obituary
