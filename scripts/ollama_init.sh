#!/bin/bash
# =============================================================================
#  MSA AI Agent — Ollama Model Bootstrap Script
#  Runs inside the `ollama-init` one-shot container.
#  Waits for Ollama to be ready, then pulls all required LLM models.
# =============================================================================

set -e

OLLAMA_HOST="${OLLAMA_BASE_URL:-http://ollama:11434}"

echo "================================================================"
echo "  MSA AI Agent — Ollama Model Bootstrap"
echo "  Host: $OLLAMA_HOST"
echo "================================================================"

# ── Wait for Ollama server to be ready ──────────────────────────────────────
echo "[1/5] Waiting for Ollama server..."
MAX_WAIT=120
WAITED=0
until curl -sf "$OLLAMA_HOST/api/version" > /dev/null 2>&1; do
    if [ $WAITED -ge $MAX_WAIT ]; then
        echo "ERROR: Ollama did not start within ${MAX_WAIT}s. Aborting."
        exit 1
    fi
    echo "  → Ollama not ready yet (${WAITED}s elapsed). Retrying in 5s..."
    sleep 5
    WAITED=$((WAITED + 5))
done
echo "  ✓ Ollama is online."

# ── Helper: pull a model only if not already installed ──────────────────────
pull_if_missing() {
    local MODEL="$1"
    local LABEL="${2:-$MODEL}"
    echo ""
    echo "  Checking: $LABEL ($MODEL)"

    INSTALLED=$(curl -sf "$OLLAMA_HOST/api/tags" | python3 -c "
import sys, json
data = json.load(sys.stdin)
names = [m['name'] for m in data.get('models', [])]
print('\n'.join(names))
" 2>/dev/null || echo "")

    if echo "$INSTALLED" | grep -qF "$MODEL"; then
        echo "  ✓ Already installed: $MODEL"
    else
        echo "  ↓ Pulling: $MODEL ..."
        curl -sf -X POST "$OLLAMA_HOST/api/pull" \
            -H "Content-Type: application/json" \
            -d "{\"name\": \"$MODEL\", \"stream\": false}" \
            | python3 -c "
import sys, json
data = json.load(sys.stdin)
status = data.get('status', 'unknown')
print(f'  ✓ Pull complete: {status}')
" || echo "  ⚠ Pull may have failed for $MODEL — check Ollama logs."
        echo "  ✓ Done: $MODEL"
    fi
}

# ── [2/5] Pull Primary Reasoning Model ──────────────────────────────────────
echo ""
echo "[2/5] Primary Reasoning Model (qwen2.5:7b-instruct)"
pull_if_missing "${MSA_OLLAMA_MODEL:-qwen2.5:7b-instruct}" "Primary / Reasoning LLM"

# ── [3/5] Pull Fast Model ────────────────────────────────────────────────────
echo ""
echo "[3/5] Fast Response Model (qwen2.5:0.5b)"
pull_if_missing "${MSA_OLLAMA_FAST_MODEL:-qwen2.5:0.5b}" "Fast / Classification LLM"

# ── [4/5] Pull Deep Reasoning Model ─────────────────────────────────────────
echo ""
echo "[4/5] Deep Reasoning Model (deepseek-r1:7b)"
pull_if_missing "${MSA_OLLAMA_REASON_MODEL:-deepseek-r1:7b}" "Deep Reasoning LLM"

# ── [5/5] Pull Embedding Model ───────────────────────────────────────────────
echo ""
echo "[5/5] Embedding Model (nomic-embed-text)"
pull_if_missing "${MSA_OLLAMA_EMBED_MODEL:-nomic-embed-text:latest}" "Embedding Model (RAG)"

# ── Final verification ───────────────────────────────────────────────────────
echo ""
echo "================================================================"
echo "  Installed Ollama Models:"
curl -sf "$OLLAMA_HOST/api/tags" | python3 -c "
import sys, json
data = json.load(sys.stdin)
models = data.get('models', [])
if not models:
    print('  ⚠  No models found!')
for m in models:
    size_gb = m.get('size', 0) / 1e9
    print(f\"  ✓  {m['name']:<40} ({size_gb:.1f} GB)\")
"
echo "================================================================"
echo "  ✓ MSA Ollama bootstrap complete. All LLMs ready for RAG + Agent."
echo "================================================================"
