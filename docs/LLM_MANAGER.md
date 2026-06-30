# LLM Manager Specification — MSA V5.0

This document defines the LiteLLM integration, model selection routing rules, and fallback mechanisms in MSA V5.0.

---

## 1. Unified Interface

The `LLMAgent` provides a single unified entry point for generating completions, calling Ollama runtimes locally, or routing requests to Google Gemini, OpenAI, or Anthropic.

---

## 2. Model Routing Rules

Tasks route dynamically according to complexity:
- **CODING**: Routes to `ollama/deepseek-coder-v2:16b`.
- **RESEARCH**: Routes to `ollama/llama3.1:8b` (hybrid dense search context).
- **SUMMARIZATION**: Routes to `ollama/llama3.2:1b` (high-speed fallback).

---

## 3. High Availability Failover

If local Ollama connection fails, the engine falls back to other endpoints configured in `config/models.yaml` or generates simulated local responses immediately to prevent app blocking.
 obituary
