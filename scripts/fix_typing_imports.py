"""
scripts/fix_typing_imports.py
==============================
Windows-compatible standalone script that applies the Section 1 typing import
fixes across 25 files listed in the V6 blueprint.

Safe to re-run: purely additive — only ADDS missing typing names to existing
`from typing import ...` lines, never removes or overwrites any code.

Usage (from project root):
    python scripts/fix_typing_imports.py
"""
import re
import os
import sys

# Map: relative path → list of missing typing names to add
FIXES = {
    "agent/AgentExecutor.py":           ["Set"],
    "agent/AgentService.py":            ["Type"],
    "agent/Planner.py":                 ["Set"],
    "agent/ReasoningEngine.py":         ["Set"],
    "ai_core/llm_manager.py":           ["Type"],
    "backend/decision_engine.py":       ["Optional", "Type"],
    "backend/server.py":                ["Any", "List"],
    "coding/CodeGenerator.py":          ["Optional"],
    "coding/RefactorEngine.py":         ["List"],
    "config.py":                        ["Set"],
    "embeddings/reranker.py":           ["Set"],
    "knowledge/parser.py":              ["Tuple"],
    "language/language_manager.py":     ["List"],
    "memory/embedding_service.py":      ["Any"],
    "mobile_control/adb_controller.py": ["Set"],
    "scripts/project_auditor.py":       ["Type"],
    "scripts/system_control.py":        ["Set"],
    "shared/uuid_v7.py":               ["Sequence"],
    "tests/test_code_explainer.py":     ["List"],
    "tests/test_reasoning_engine.py":   ["Set"],
    "tests/test_refactor_engine.py":    ["List"],
    "tests/test_v5_cognitive.py":       ["List"],
    "tests/test_v5_swarm.py":          ["List"],
    "tools/tool_registry.py":           ["Set"],
    "voice/stt.py":                     ["Any"],
}

# Resolve project root = directory containing this script's parent
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

fixed = []
skipped = []
errors = []

for rel_path, missing_names in FIXES.items():
    filepath = os.path.join(PROJECT_ROOT, rel_path.replace("/", os.sep))

    if not os.path.exists(filepath):
        skipped.append(f"SKIP (not found): {rel_path}")
        continue

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            src = f.read()

        match = re.search(r"(from typing import )([^\n]+)", src)
        if match:
            # Existing typing import — merge names
            existing = [n.strip() for n in match.group(2).split(",")]
            merged = sorted(set(existing + missing_names))
            # Only rewrite if something actually changed
            if merged == sorted(existing):
                skipped.append(f"SKIP (already present): {rel_path}")
                continue
            new_line = "from typing import " + ", ".join(merged)
            src = src[:match.start()] + new_line + src[match.end():]
        else:
            # No existing typing import — insert after the last top-level import block
            lines = src.split("\n")
            insert_at = 0
            for i, line in enumerate(lines):
                if line.startswith("import ") or line.startswith("from "):
                    insert_at = i + 1
                elif line.strip() == "" and insert_at > 0:
                    break
            new_import = "from typing import " + ", ".join(sorted(missing_names))
            lines.insert(insert_at, new_import)
            src = "\n".join(lines)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(src)

        fixed.append(f"FIXED: {rel_path} -> added {missing_names}")

    except Exception as e:
        errors.append(f"ERROR: {rel_path} - {e}")

# ── Report ────────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("MSA Typing Import Fix Report")
print("=" * 60)

for msg in fixed:
    print(f"  OK  {msg}")

for msg in skipped:
    print(f"  --  {msg}")

for msg in errors:
    print(f"  !! {msg}")

print("=" * 60)
print(f"Fixed: {len(fixed)}  |  Skipped: {len(skipped)}  |  Errors: {len(errors)}")

if errors:
    sys.exit(1)
else:
    print("All typing fixes applied successfully.")
    sys.exit(0)
