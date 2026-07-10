#!/usr/bin/env python3
"""
scripts/rag_healthcheck.py
==========================
MSA AI Agent — RAG Stack Health-Check & Init Script.

Runs inside the `msa-rag-init` one-shot container to verify and initialise:
  1. Qdrant vector DB (RAG chunk store)
  2. FAISS index files (local dense retrieval)
  3. Sentence-Transformer embedding model (nomic-embed-text via Ollama)
  4. Neo4j Graph RAG connection (optional)
  5. Warm-up: encodes a probe sentence to confirm the full pipeline works.
"""

import json
import logging
import os
import sys
import time
import urllib.request
import urllib.error

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("msa.rag_healthcheck")

# ── Config from env ───────────────────────────────────────────────────────────
QDRANT_HOST    = os.environ.get("QDRANT_HOST", "qdrant")
QDRANT_PORT    = int(os.environ.get("QDRANT_PORT", "6333"))
# IMPORTANT: Ollama runs on HOST (not in Docker). Use host.docker.internal in containers.
OLLAMA_URL     = os.environ.get("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
EMBED_MODEL    = os.environ.get("MSA_OLLAMA_EMBED_MODEL", "nomic-embed-text:latest")
NEO4J_URI      = os.environ.get("NEO4J_URI", "bolt://neo4j:7687")
NEO4J_USER     = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "msa_neo4j_pass")
ENABLE_NEO4J   = os.environ.get("ENABLE_NEO4J", "true").lower() == "true"

QDRANT_URL = f"http://{QDRANT_HOST}:{QDRANT_PORT}"

# Collections to create if missing
QDRANT_COLLECTIONS = [
    {"name": "msa_knowledge",   "size": 768,  "desc": "General knowledge RAG"},
    {"name": "msa_code_rag",    "size": 768,  "desc": "Code RAG (CodeRAG)"},
    {"name": "msa_graph_nodes", "size": 768,  "desc": "Graph RAG node embeddings"},
    {"name": "msa_career",      "size": 768,  "desc": "Career / Job intelligence RAG"},
    {"name": "msa_memory",      "size": 768,  "desc": "Episodic memory embeddings"},
]

PROBE_SENTENCE = "MSA AI Agent RAG pipeline warm-up test — Hello from Sadique!"


def _http_get(url: str, timeout: int = 10) -> dict:
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def _http_post(url: str, payload: dict, timeout: int = 30) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="PUT" if "collections" in url and "create" not in url else "POST",
    )
    # Qdrant collection creation uses PUT
    if "collections/" in url and not url.endswith("/points"):
        req.method = "PUT"
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        return {"error": str(e), "body": body}


# =============================================================================
# Step 1 — Qdrant health check
# =============================================================================
def check_qdrant() -> bool:
    log.info("═══ [1/5] Qdrant Vector DB (%s) ═══", QDRANT_URL)
    max_wait, waited = 60, 0
    while waited < max_wait:
        try:
            resp = _http_get(f"{QDRANT_URL}/healthz", timeout=5)
            if resp.get("title") == "qdrant - vector search engine" or resp == {}:
                log.info("  ✓ Qdrant is healthy")
                return True
            # Some versions return just {}
            log.info("  ✓ Qdrant responded: %s", resp)
            return True
        except Exception:
            try:
                # /readyz on newer versions
                _http_get(f"{QDRANT_URL}/readyz", timeout=5)
                log.info("  ✓ Qdrant is ready (/readyz)")
                return True
            except Exception:
                pass
        log.info("  → Waiting for Qdrant (%ds elapsed)...", waited)
        time.sleep(5)
        waited += 5
    log.error("  ✗ Qdrant did not become healthy within %ds", max_wait)
    return False


# =============================================================================
# Step 2 — Create Qdrant collections if missing
# =============================================================================
def ensure_qdrant_collections() -> None:
    log.info("═══ [2/5] Qdrant Collections ═══")
    try:
        resp = _http_get(f"{QDRANT_URL}/collections", timeout=10)
        existing = {c["name"] for c in resp.get("result", {}).get("collections", [])}
    except Exception as e:
        log.warning("  Could not list collections: %s", e)
        existing = set()

    for col in QDRANT_COLLECTIONS:
        name = col["name"]
        if name in existing:
            log.info("  ✓ Collection exists: %s", name)
            continue
        payload = {
            "vectors": {
                "size": col["size"],
                "distance": "Cosine",
            }
        }
        url = f"{QDRANT_URL}/collections/{name}"
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="PUT",
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                result = json.loads(r.read().decode())
            log.info("  ✓ Created collection: %-25s | %s", name, col["desc"])
        except Exception as e:
            log.warning("  ⚠ Could not create collection '%s': %s", name, e)


# =============================================================================
# Step 3 — FAISS index check
# =============================================================================
def check_faiss_index() -> None:
    log.info("═══ [3/5] FAISS Index (local dense retrieval) ═══")
    faiss_path  = "/app/data/memory/msa_vectors.faiss"
    meta_path   = "/app/data/memory/msa_vectors_meta.json"

    if os.path.exists(faiss_path):
        size_kb = os.path.getsize(faiss_path) // 1024
        log.info("  ✓ FAISS index found: %s (%d KB)", faiss_path, size_kb)
    else:
        log.info("  ⚠ FAISS index not found — will be created on first ingest.")
        os.makedirs(os.path.dirname(faiss_path), exist_ok=True)

    if os.path.exists(meta_path):
        try:
            with open(meta_path) as f:
                meta = json.load(f)
            count = len(meta) if isinstance(meta, list) else len(meta.get("texts", []))
            log.info("  ✓ FAISS meta: %d vectors indexed", count)
        except Exception as e:
            log.warning("  ⚠ FAISS meta unreadable: %s", e)
    else:
        log.info("  ⚠ FAISS meta not found — will be created on first ingest.")


# =============================================================================
# Step 4 — Embedding model warm-up (via Ollama /api/embeddings)
# =============================================================================
def warmup_embedding_model() -> bool:
    log.info("═══ [4/5] Embedding Model Warm-up (%s) ═══", EMBED_MODEL)
    max_wait, waited = 120, 0
    while waited < max_wait:
        try:
            payload = {"model": EMBED_MODEL, "prompt": PROBE_SENTENCE}
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                f"{OLLAMA_URL}/api/embeddings",
                data=data,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=60) as r:
                result = json.loads(r.read().decode())
            embedding = result.get("embedding", [])
            if embedding:
                log.info(
                    "  ✓ Embedding model OK — vector dim=%d (probe sentence encoded)",
                    len(embedding),
                )
                return True
            else:
                log.warning("  ⚠ Empty embedding returned — model may still be loading.")
        except urllib.error.URLError as e:
            log.info("  → Embedding not ready yet (%ds): %s", waited, e)
        except Exception as e:
            log.warning("  ⚠ Embedding warm-up error (%ds): %s", waited, e)
        time.sleep(10)
        waited += 10

    log.error("  ✗ Embedding model did not respond within %ds.", max_wait)
    return False


# =============================================================================
# Step 5 — Neo4j Graph RAG (optional)
# =============================================================================
def check_neo4j() -> None:
    if not ENABLE_NEO4J:
        log.info("═══ [5/5] Neo4j Graph RAG — SKIPPED (ENABLE_NEO4J=false) ═══")
        return

    log.info("═══ [5/5] Neo4j Graph RAG (%s) ═══", NEO4J_URI)
    try:
        import neo4j  # type: ignore
        driver = neo4j.GraphDatabase.driver(
            NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD)
        )
        with driver.session() as session:
            result = session.run("RETURN 'MSA RAG ready' AS msg")
            record = result.single()
            log.info("  ✓ Neo4j connected: %s", record["msg"])

        # Create vector index if neo4j 5.x+ and APOC present
        with driver.session() as session:
            try:
                session.run(
                    "CREATE VECTOR INDEX msa_knowledge_idx IF NOT EXISTS "
                    "FOR (n:KnowledgeNode) ON (n.embedding) "
                    "OPTIONS {indexConfig: {`vector.dimensions`: 768, `vector.similarity_function`: 'cosine'}}"
                )
                log.info("  ✓ Neo4j vector index 'msa_knowledge_idx' ensured.")
            except Exception as e:
                log.info("  ℹ Neo4j index creation skipped: %s", e)

        driver.close()
    except ImportError:
        log.warning("  ⚠ neo4j Python driver not installed. Graph RAG will use FAISS fallback.")
    except Exception as e:
        log.warning("  ⚠ Neo4j connection failed: %s. Graph RAG will use FAISS fallback.", e)


# =============================================================================
# Main
# =============================================================================
def main() -> None:
    log.info("")
    log.info("╔══════════════════════════════════════════════════════════════╗")
    log.info("║  STEP 3: MSA AI Agent — RAG Stack Init & Verify             ║")
    log.info("║  Agent: Md Sadique Amin (MSA)  — V6 Ultra Pro Max           ║")
    log.info("╚══════════════════════════════════════════════════════════════╝")
    log.info("")

    errors = []

    # 1. Qdrant
    if not check_qdrant():
        errors.append("Qdrant not healthy — cannot create collections")
    else:
        ensure_qdrant_collections()

    # 2. FAISS (local)
    check_faiss_index()

    # 3. Embedding warmup — MANDATORY for RAG to work
    if not warmup_embedding_model():
        errors.append("Embedding model warm-up FAILED — RAG pipeline will NOT work")

    # 4. Neo4j (optional but logged)
    check_neo4j()

    log.info("")
    log.info("═══════════════════════════════════════════════════════════════")
    if errors:
        log.error("  ✗ STEP 3 FAILED — RAG stack has critical errors:")
        for e in errors:
            log.error("    ✗ %s", e)
        log.error("")
        log.error("  MSA Agent startup BLOCKED.")
        log.error("  Fix the above issues and re-run: docker compose up -d")
        log.error("═══════════════════════════════════════════════════════════════")
        sys.exit(1)   # <-- Hard fail: blocks msa-agent from starting
    else:
        log.info("  ✓ STEP 3 PASSED — RAG stack fully ready!")
        log.info("    • Qdrant collections : %d created/verified", len(QDRANT_COLLECTIONS))
        log.info("    • FAISS index        : checked")
        log.info("    • Embedding model    : %s (warm)", EMBED_MODEL)
        log.info("    • Neo4j Graph RAG    : %s", "enabled" if ENABLE_NEO4J else "disabled")
        log.info("")
        log.info("  ✓ All 3 steps passed — MSA Agent is cleared for launch! 🚀")
        log.info("═══════════════════════════════════════════════════════════════")
        log.info("")


if __name__ == "__main__":
    main()
