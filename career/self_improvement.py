"""
career/self_improvement.py
===========================
Self-Improvement loop analyzing rejections and updating resume strategies (V9).

Uses LLM to diagnose rejection notices, extracts key skill gaps, and suggests
how to adjust resume keywords or application filtering rules.
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional

logger = logging.getLogger("msa.career.improvement")


class SelfImprovementEngine:
    """
    Core engine for parsing failure events and optimizing candidate profile alignment.
    """

    def __init__(self, llm_manager=None) -> None:
        self._llm = llm_manager

    def analyze_rejection(
        self,
        job_title: str,
        job_desc: str,
        feedback_text: str,
        llm_manager=None,
    ) -> Dict[str, Any]:
        """
        Analyzes a rejection letter or manager feedback to deduce skill gaps.
        Returns a dict containing identified gaps, adjustments, and action steps.
        """
        llm = llm_manager or self._llm
        result = {
            "gaps": [],
            "resume_adjustments": [],
            "suggested_actions": [],
        }

        if not feedback_text:
            return result

        if llm is None:
            # Simple heuristic matcher fallback
            gaps = []
            for word in ["java", "python", "aws", "docker", "kubernetes", "system design", "microservices"]:
                if word in job_desc.lower() and word not in feedback_text.lower():
                    gaps.append(word.upper())
            result["gaps"] = gaps[:3]
            result["suggested_actions"] = [
                f"Highlight {g} skills more prominently in your profile." for g in gaps[:3]
            ]
            return result

        prompt = (
            f"You are a career consultant. Analyze the following rejection feedback "
            f"received for a job application:\n\n"
            f"JOB TITLE: {job_title}\n"
            f"JOB DESCRIPTION:\n{job_desc[:800]}\n\n"
            f"REJECTION FEEDBACK:\n{feedback_text[:1000]}\n\n"
            f"Determine:\n"
            f"  1. Probable skill or experience gaps (list 2-3 maximum)\n"
            f"  2. Specific bullet-point updates for the resume to address this\n"
            f"  3. Actions candidate can take (e.g., certification, projects)\n"
            f"Respond ONLY with a valid JSON object matching this structure:\n"
            f'{{"gaps": ["...", "..."], "resume_adjustments": ["...", "..."], "suggested_actions": ["...", "..."]}}'
        )

        try:
            import json
            import re
            response = llm.generate(prompt, max_tokens=400)
            match = re.search(r"\{.*\}", response, re.DOTALL)
            if match:
                data = json.loads(match.group())
                result["gaps"] = data.get("gaps", [])
                result["resume_adjustments"] = data.get("resume_adjustments", [])
                result["suggested_actions"] = data.get("suggested_actions", [])
                logger.info("[SelfImprovement] Successfully parsed rejection feedback gaps: %s", result["gaps"])
        except Exception as exc:
            logger.warning("[SelfImprovement] Analysis failed: %s", exc)

        return result

    def tune_search_thresholds(
        self,
        funnel_stats: Dict[str, int],
        current_ats_threshold: float,
    ) -> float:
        """
        Dynamically adjusts the ATS filtering threshold based on application volume.
        If rejection rate is extremely high, raises threshold to filter for better matches.
        """
        rejections = funnel_stats.get("rejected", 0)
        total = sum(funnel_stats.values())

        if total > 10:
            rejection_rate = rejections / total
            if rejection_rate > 0.80:
                # Too many rejections; raise threshold by 0.05
                new_threshold = min(0.85, current_ats_threshold + 0.05)
                logger.info("[SelfImprovement] Raising ATS score threshold from %.2f to %.2f due to high rejection rate (%.1f%%)",
                            current_ats_threshold, new_threshold, rejection_rate * 100)
                return new_threshold
            elif rejection_rate < 0.20:
                # Safe to relax filters slightly to discover more opportunities
                new_threshold = max(0.50, current_ats_threshold - 0.05)
                logger.info("[SelfImprovement] Lowering ATS score threshold from %.2f to %.2f to expand funnel",
                            current_ats_threshold, new_threshold)
                return new_threshold

        return current_ats_threshold
