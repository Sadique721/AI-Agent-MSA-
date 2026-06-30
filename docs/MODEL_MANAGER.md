# Model Routing & LiteLLM Manager — MSA V5.0

MSA V5.0 routes task inputs dynamically to different LLM chains using `config/models.yaml` rules.

---

## 1. Routing Model Strategy

The router selects models according to task complexity and context:
- **CODING**: Routes to `ollama/deepseek-coder-v2:16b` (fallback: `codellama:7b`).
- **MATH / DEEP_THINKING**: Routes to `ollama/deepseek-r1:7b` with chain-of-thought enabled.
- **GENERAL_QA / CHAT**: Routes to `ollama/llama3.2:3b`.
- **SUMMARIZATION**: Routes to lightweight models like `ollama/llama3.2:1b` for speed.

---

## 2. LiteLLM Gateway Integration

The `LLMAgent` interfaces directly with LiteLLM if available:
- Direct support for local Ollama runtimes.
- Transparent API keys fallbacks (OpenAI, Anthropic, Gemini).
- Built-in caching layer (TTL: 5 minutes) minimizing repeat calls.

---

## 3. High Availability Failover

If a model call fails, the routing engine attempts recovery in order:
```
Primary Local Model ──► Fallback Local Model ──► Cloud API (if configured) ──► Cached/Simulation Response
```
This guarantees the desktop application stays fully functional even when local AI models are restarting.
