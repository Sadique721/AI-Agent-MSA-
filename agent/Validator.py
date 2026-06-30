"""
agent/Validator.py
==================
Phase-2: Post-execution Validator for MSA Agent.

Validates whether each plan step succeeded and produces actionable
feedback for the auto-replan loop. Three validation levels:

  LOW    — result is non-empty and non-None
  MEDIUM — result has no error keywords and contains meaningful data
  HIGH   — result passes domain-specific checks (count > 0, fields present)

Auto-replan is triggered when validate_result() returns valid=False
and the retry counter is below MAX_REPLAN_RETRIES.
"""

import logging
import re
import numpy as np
from typing import Any, Dict, List, Optional

logger = logging.getLogger("msa.agent.validator")

# ── Error signal patterns ─────────────────────────────────────────────────────
_ERROR_PATTERNS = [
    r"\bfailed\b", r"\berror\b", r"\bexception\b", r"\btimeout\b",
    r"\bnot found\b", r"\bunavailable\b", r"\bno handler\b",
    r"\bdisabled\b", r"\bpermission denied\b", r"\bcould not\b",
    r"\bunable to\b", r"\bnot initialised\b", r"\bnone\b",
]
_ERROR_RE = re.compile("|".join(_ERROR_PATTERNS), re.IGNORECASE)

# ── Validation level constants ────────────────────────────────────────────────
LEVEL_LOW    = "LOW"
LEVEL_MEDIUM = "MEDIUM"
LEVEL_HIGH   = "HIGH"


class Validator:
    """
    MSA Phase-2 Validator.

    Used by AgentService inside the auto-replan loop:

        results = execute_steps(steps)
        validation = validator.validate_result(results, reasoning)
        if not validation["valid"]:
            → trigger replan
    """

    def __init__(self):
        logger.info("Validator initialised.")

    # ── Step-level validation ─────────────────────────────────────────────────

    def validate_step(
        self,
        step: Dict[str, Any],
        result: str,
        reasoning: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Validate a single plan step execution result.

        Args:
            step:      The plan step dict {step, tool, action, params}.
            result:    String result returned by the tool handler.
            reasoning: Reasoning packet from ReasoningEngine (optional).

        Returns:
            {
              "valid":      bool,
              "level":      str,   # LOW | MEDIUM | HIGH
              "score":      float, # 0.0 – 1.0
              "reason":     str,
              "tool":       str,
              "step_index": int,
            }
        """
        tool_name = step.get("tool", "unknown")
        step_idx  = step.get("step", 0)

        # ── Level 1: LOW — is result non-empty? ────────────────────────────
        if not result or not str(result).strip() or str(result).strip().lower() in ("none", "null", ""):
            return self._fail(tool_name, step_idx, LEVEL_LOW, "Result is empty or None", score=0.0)

        result_str = str(result).strip()

        # ── Level 2: MEDIUM — does result contain error signals? ───────────
        if _ERROR_RE.search(result_str):
            # Check if it's a recoverable soft error
            soft_errors = ["not found", "no results", "unavailable"]
            is_soft = any(s in result_str.lower() for s in soft_errors)
            return self._fail(
                tool_name, step_idx, LEVEL_MEDIUM,
                f"Result contains error signal: {result_str[:120]}",
                score=0.1 if is_soft else 0.0,
            )

        # ── Level 3: HIGH — domain-specific validation ─────────────────────
        high_check = self._high_level_check(tool_name, result_str, reasoning)
        if not high_check["valid"]:
            return self._fail(
                tool_name, step_idx, LEVEL_HIGH,
                high_check["reason"],
                score=high_check.get("score", 0.3),
            )

        # ── All levels passed ─────────────────────────────────────────────
        score = self._compute_score(result_str)
        logger.debug("validate_step: step=%d tool=%s → PASS (score=%.2f)", step_idx, tool_name, score)
        return {
            "valid":      True,
            "level":      LEVEL_HIGH,
            "score":      score,
            "reason":     "All validation checks passed.",
            "tool":       tool_name,
            "step_index": step_idx,
        }

    # ── Result-level validation ───────────────────────────────────────────────

    def validate_result(
        self,
        results: List[Dict[str, Any]],
        reasoning: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Validate the full set of plan step results.

        Args:
            results:   List of {step, tool, result} dicts from execution.
            reasoning: Reasoning packet (for context-aware checking).

        Returns:
            {
              "valid":        bool,
              "passed":       int,
              "total":        int,
              "score":        float,  # average step score
              "failed_steps": list,
              "reason":       str,
            }
        """
        if not results:
            return {
                "valid":        False,
                "passed":       0,
                "total":        0,
                "score":        0.0,
                "failed_steps": [],
                "reason":       "No execution results to validate.",
            }

        step_validations = []
        failed = []
        total_score = 0.0

        for item in results:
            step = {
                "step":   item.get("step", 0),
                "tool":   item.get("tool", "unknown"),
                "action": item.get("action", ""),
                "params": item.get("params", {}),
            }
            raw_result = item.get("result", "")
            validation = self.validate_step(step, raw_result, reasoning)
            step_validations.append(validation)
            total_score += validation.get("score", 0.0)
            if not validation["valid"]:
                failed.append({
                    "tool":   step["tool"],
                    "step":   step["step"],
                    "reason": validation["reason"],
                })

        avg_score = total_score / len(results) if results else 0.0
        passed    = len(results) - len(failed)
        is_valid  = len(failed) == 0

        if failed:
            reason = f"{len(failed)} step(s) failed: " + ", ".join(
                f"step {f['step']} ({f['tool']})" for f in failed
            )
        else:
            reason = f"All {passed} step(s) passed successfully."

        logger.info(
            "validate_result: %d/%d passed | score=%.2f | valid=%s",
            passed, len(results), avg_score, is_valid,
        )
        return {
            "valid":        is_valid,
            "passed":       passed,
            "total":        len(results),
            "score":        round(avg_score, 3),
            "failed_steps": failed,
            "reason":       reason,
        }

    # ── Final output validation ───────────────────────────────────────────────

    def validate_final_output(
        self,
        results: List[Dict[str, Any]],
        goal: str,
        retrieved_context_chunks: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Final holistic validation of the overall task output, including hallucination checks.
        """
        if not results:
            return {
                "valid":    False,
                "score":    0.0,
                "grade":    "F",
                "feedback": "No results produced.",
                "summary":  "Task produced no output.",
            }

        base = self.validate_result(results)
        score = base["score"]

        # Bonus: does any result contain the goal keywords?
        goal_words = set(re.findall(r"\w+", goal.lower()))
        content_words = set()
        for item in results:
            content_words.update(re.findall(r"\w+", str(item.get("result", "")).lower()))
        overlap = len(goal_words & content_words)
        if goal_words:
            relevance_bonus = min(overlap / len(goal_words), 0.3)
            score = min(score + relevance_bonus, 1.0)

        # Hallucination Check
        hallucination_result = None
        citation_result = None
        if retrieved_context_chunks:
            combined_result_text = "\n".join(str(item.get("result", "")) for item in results)
            
            # A. Check for Hallucinations
            hallucination_result = self.validate_hallucinations(combined_result_text, retrieved_context_chunks)
            if not hallucination_result["valid"]:
                penalty = 0.25 * len(hallucination_result["hallucinated_sentences"])
                score = max(0.0, score - penalty)

            # B. Check for Citation Quality
            citation_result = self.validate_citations(combined_result_text, retrieved_context_chunks)
            if not citation_result["valid"]:
                penalty = 0.1 * len(citation_result["invalid_citations"])
                score = max(0.0, score - penalty)

        # Grade
        if score >= 0.85:
            grade, feedback = "A", "Excellent — task completed successfully."
        elif score >= 0.65:
            grade, feedback = "B", "Good — most steps succeeded with minor issues."
        elif score >= 0.40:
            grade, feedback = "C", "Partial success — some steps failed, results may be incomplete."
        else:
            grade, feedback = "F", "Task failed — most steps did not complete successfully."

        if hallucination_result and not hallucination_result["valid"]:
            feedback += f" WARNING: Detected potential hallucinations: {hallucination_result['reason']}"
        if citation_result and not citation_result["valid"]:
            feedback += f" WARNING: Citation mismatch: {citation_result['reason']}"

        summary_parts = [
            f"Goal: {goal[:80]}",
            f"Steps: {base['passed']}/{base['total']} passed",
            f"Score: {score:.0%}",
            f"Grade: {grade}",
        ]
        if base["failed_steps"]:
            summary_parts.append(
                "Failed: " + ", ".join(s["tool"] for s in base["failed_steps"])
            )

        logger.info("validate_final_output: goal='%s' grade=%s score=%.2f", goal[:60], grade, score)
        return {
            "valid":    score >= 0.40,
            "score":    round(score, 3),
            "grade":    grade,
            "feedback": feedback,
            "summary":  " | ".join(summary_parts),
            "hallucinations": hallucination_result,
            "citations": citation_result
        }

    def validate_citations(
        self,
        response_text: str,
        retrieved_context_chunks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Validates citation quality and calculates citation confidence score.
        Checks if cited filenames in text actually exist in retrieved contexts.
        """
        import os
        if not response_text or not retrieved_context_chunks:
            return {"valid": True, "score": 1.0, "invalid_citations": [], "reason": "No context or response to check."}

        # Find cited files in text
        potential_citations = set(re.findall(r"\b[\w\-]+\.(?:py|txt|pdf|docx|js|ts|json|md|go|rs|html)\b", response_text))
        if not potential_citations:
            return {"valid": True, "score": 1.0, "invalid_citations": [], "reason": "No explicit file citations detected."}

        valid_sources = set()
        for chunk in retrieved_context_chunks:
            fpath = chunk.get("file_path", chunk.get("metadata", {}).get("source", ""))
            if fpath:
                valid_sources.add(os.path.basename(fpath).lower())

        invalid_citations = []
        valid_count = 0
        for cite in potential_citations:
            if cite.lower() in valid_sources:
                valid_count += 1
            else:
                invalid_citations.append(cite)

        total_citations = len(potential_citations)
        citation_score = valid_count / total_citations if total_citations > 0 else 1.0
        is_valid = len(invalid_citations) == 0

        return {
            "valid": is_valid,
            "score": round(citation_score, 4),
            "invalid_citations": invalid_citations,
            "total_citations": total_citations,
            "reason": f"Validated {valid_count}/{total_citations} cited files."
        }

    def validate_hallucinations(
        self,
        response_text: str,
        retrieved_context_chunks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Validate whether the response text contains hallucinations against retrieved context chunks.
        Splits response into sentences, embeds them, and checks if each sentence has a matching support
        chunk (similarity >= 0.25).
        """
        if not response_text or not retrieved_context_chunks:
            return {
                "valid": True,
                "score": 1.0,
                "hallucinated_sentences": [],
                "reason": "No context or response to check."
            }

        # Lazy load embedder to compute similarity
        try:
            from embeddings.embedder import Embedder
            embedder = Embedder()
        except Exception as e:
            logger.warning("Validator: failed to load embedder for hallucination check (%s)", e)
            return {
                "valid": True,
                "score": 1.0,
                "hallucinated_sentences": [],
                "reason": "Embedder unavailable."
            }

        # Split response into sentences
        sentence_end = re.compile(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|\!)\s+')
        sentences = [s.strip() for s in sentence_end.split(response_text) if len(s.strip()) > 10]
        if not sentences:
            return {
                "valid": True,
                "score": 1.0,
                "hallucinated_sentences": [],
                "reason": "No significant sentences to check."
            }

        context_texts = [c.get("text", c.get("content", "")) for c in retrieved_context_chunks]
        if not context_texts:
            return {
                "valid": True,
                "score": 1.0,
                "hallucinated_sentences": [],
                "reason": "Empty context chunks."
            }

        # Embed sentences and context
        s_vecs = embedder.embed_batch(sentences)
        c_vecs = embedder.embed_batch(context_texts)

        hallucinated = []
        scores = []

        for i, s_vec in enumerate(s_vecs):
            # Compute cosine similarity with all context chunks (dot product for normalized vectors)
            sims = [float(np.dot(s_vec, c_vec)) for c_vec in c_vecs]
            max_sim = max(sims) if sims else 0.0
            scores.append(max_sim)
            
            # If similarity with ALL chunks is very low (< 0.25), consider it a potential hallucination
            if max_sim < 0.25:
                hallucinated.append({
                    "sentence": sentences[i],
                    "max_similarity": round(max_sim, 4)
                })

        avg_support_score = sum(scores) / len(scores) if scores else 1.0
        is_valid = len(hallucinated) == 0

        reason = "All claims supported by retrieved context." if is_valid else f"Detected {len(hallucinated)} unsupported/hallucinated claim(s)."
        
        return {
            "valid": is_valid,
            "score": round(avg_support_score, 4),
            "hallucinated_sentences": hallucinated,
            "reason": reason
        }

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _high_level_check(
        self, tool_name: str, result: str, reasoning: Optional[Dict]
    ) -> Dict[str, Any]:
        """Domain-specific high-level checks per tool category."""

        # Coding tools validation
        if tool_name in ("generate_code", "debug_code", "analyze_stacktrace", "generate_project", "refactor_code", "generate_tests", "explain_code", "review_code") or tool_name.startswith("coding"):
            return self._validate_coding_result(tool_name, result)

        # Browser tools: result must mention URLs or titles or have content
        if tool_name.startswith("browser_"):
            if len(result) < 20:
                return {"valid": False, "reason": "Browser result too short — possible navigation failure.", "score": 0.2}
            if tool_name == "browser_linkedin":
                # Expect job-like keywords
                job_signals = ["developer", "engineer", "manager", "analyst", "java",
                               "spring", "job", "position", "hiring", "experience"]
                if not any(sig in result.lower() for sig in job_signals):
                    return {"valid": False, "reason": "LinkedIn result missing job-related content.", "score": 0.3}
            return {"valid": True, "reason": "Browser result looks valid.", "score": 0.8}

        # Memory tools: confirm store/recall succeeded
        if tool_name == "memory_remember":
            if "saved" in result.lower() or "stored" in result.lower() or "ok" in result.lower() or len(result) > 5:
                return {"valid": True, "reason": "Memory store confirmed.", "score": 0.9}
            return {"valid": False, "reason": "Memory store did not confirm success.", "score": 0.2}

        if tool_name == "memory_search":
            if "no results" in result.lower() or len(result) < 10:
                return {"valid": False, "reason": "Memory search returned no results.", "score": 0.3}
            return {"valid": True, "reason": "Memory search returned results.", "score": 0.8}

        # Search tools: must have some content
        if tool_name in ("internet_search", "browser_search"):
            if len(result) < 30:
                return {"valid": False, "reason": "Search returned insufficient content.", "score": 0.2}
            return {"valid": True, "reason": "Search returned content.", "score": 0.8}

        # Mobile tools: check action confirmation
        if tool_name in ("mobile_call", "mobile_alarm", "mobile_control"):
            if any(w in result.lower() for w in ["success", "ok", "done", "sent", "called", "alarm set"]):
                return {"valid": True, "reason": "Mobile action confirmed.", "score": 1.0}
            if len(result) > 10:
                return {"valid": True, "reason": "Mobile action produced output.", "score": 0.7}
            return {"valid": False, "reason": "Mobile action did not confirm completion.", "score": 0.2}

        # System tools: any non-empty output is acceptable
        if tool_name in ("get_time", "get_profile", "open_app", "automation", "system_control"):
            if len(result) > 3:
                return {"valid": True, "reason": "System tool returned output.", "score": 0.9}
            return {"valid": False, "reason": "System tool returned empty output.", "score": 0.1}

        # Default: pass if result is non-trivial
        return {"valid": True, "reason": "Default validation passed.", "score": 0.7}

    def _validate_coding_result(self, tool_name: str, result: str) -> Dict[str, Any]:
        """Validate coding tool outputs."""
        lower = result.lower()

        # Is result empty?
        if len(result.strip()) < 10:
            return {"valid": False, "reason": "Coding result too short.", "score": 0.1}

        # Check for error signals
        if "failed" in lower or "syntax error" in lower or "invalid syntax" in lower:
            return {"valid": False, "reason": "Coding result contains error indicators.", "score": 0.2}

        # Validate Code generation / refactoring / tests
        if tool_name in ("generate_code", "refactor_code", "generate_tests"):
            # 1. compilation check: balanced braces/parentheses
            braces = result.count("{") - result.count("}")
            parentheses = result.count("(") - result.count(")")
            brackets = result.count("[") - result.count("]")
            if braces != 0 or parentheses != 0 or brackets != 0:
                return {"valid": False, "reason": f"Code has unbalanced syntax symbols: braces={braces}, parentheses={parentheses}, brackets={brackets}", "score": 0.4}

            # 2. missing imports check (heuristic: using List/Map or RestController without import)
            code_lines = result.splitlines()
            has_rest_controller = any("@RestController" in line for line in code_lines)
            has_rest_import = any("import org.springframework.web.bind.annotation" in line for line in code_lines)
            if has_rest_controller and not has_rest_import:
                return {"valid": False, "reason": "Code uses @RestController but lacks corresponding Spring annotation imports.", "score": 0.5}

            has_list = any("List<" in line for line in code_lines)
            has_list_import = any("import java.util.List" in line or "import java.util.*" in line for line in code_lines)
            if has_list and not has_list_import:
                return {"valid": False, "reason": "Code uses Java List type but lacks java.util.List import.", "score": 0.5}

            # If it passes, give high score
            return {"valid": True, "reason": "Code compilation, syntax balance, and dependency imports look valid.", "score": 0.95}

        # Validate Stack Trace or Debug results
        if tool_name in ("debug_code", "analyze_stacktrace"):
            # Result should suggest a fix or locate coordinate (file/line)
            if "fix" in lower or "cause" in lower or "file" in lower or "line" in lower or "suggestion" in lower or "root_cause" in lower or "issue" in lower:
                return {"valid": True, "reason": "Crash trace or debug analysis succeeded.", "score": 0.9}
            return {"valid": False, "reason": "Debug analysis does not contain root cause or recommendations.", "score": 0.3}

        # Validate Project generator
        if tool_name == "generate_project":
            if "pom.xml" in lower or "package.json" in lower or "structure" in lower or "dockerfile" in lower or "blueprint" in lower or "app.js" in lower or "app.component" in lower:
                return {"valid": True, "reason": "Project structural blueprint validated successfully.", "score": 0.95}
            return {"valid": False, "reason": "Project blueprint is missing essential configurations (pom.xml/package.json).", "score": 0.3}

        # Explain / Review checks
        if tool_name in ("explain_code", "review_code"):
            if "summary" in lower or "explanation" in lower or "score" in lower or "grade" in lower or "comment" in lower or "lines" in lower or "explain" in lower:
                return {"valid": True, "reason": "Explanation or code review completed.", "score": 0.9}
            return {"valid": False, "reason": "Explanation/Review did not provide summary or comments.", "score": 0.3}

        return {"valid": True, "reason": "Coding validation passed.", "score": 0.8}

    def _compute_score(self, result: str) -> float:
        """Heuristic quality score based on result richness."""
        length = len(result)
        if length > 500:  return 1.0
        if length > 200:  return 0.9
        if length > 100:  return 0.8
        if length > 50:   return 0.7
        if length > 20:   return 0.6
        return 0.5

    def _fail(
        self,
        tool: str,
        step_idx: int,
        level: str,
        reason: str,
        score: float = 0.0,
    ) -> Dict[str, Any]:
        logger.warning("validate_step FAIL: step=%d tool=%s level=%s → %s", step_idx, tool, level, reason[:80])
        return {
            "valid":      False,
            "level":      level,
            "score":      score,
            "reason":     reason,
            "tool":       tool,
            "step_index": step_idx,
        }
