"""
career/resume_matcher.py
=========================
Resume-to-Job matching and ATS scoring engine (V7).

ATS Score formula (three components):
  40% — keyword density match   (required terms from job desc found in resume)
  30% — section presence score  (summary, experience, skills, education detected)
  30% — semantic cosine similarity via sentence-transformers

Usage:
    from career.resume_matcher import ResumeMatcher
    matcher = ResumeMatcher()
    result = matcher.score(job_listing, resume_text)
    print(result.ats_score, result.gaps)
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import List, Optional

logger = logging.getLogger("msa.career.matcher")

# ── Result Dataclass ──────────────────────────────────────────────────────────

@dataclass
class MatchResult:
    ats_score: float            # 0.0 - 1.0
    match_score: float          # 0.0 - 1.0 semantic similarity
    keyword_score: float        # 0.0 - 1.0 keyword density
    section_score: float        # 0.0 - 1.0 section presence
    gaps: List[str] = field(default_factory=list)           # missing keywords
    suggestions: List[str] = field(default_factory=list)    # improvement hints
    matched_keywords: List[str] = field(default_factory=list)


# ── Section markers ───────────────────────────────────────────────────────────

_SECTION_PATTERNS = {
    "summary":    re.compile(r"\b(summary|objective|profile|about me)\b", re.I),
    "experience": re.compile(r"\b(experience|work history|employment|projects?)\b", re.I),
    "skills":     re.compile(r"\b(skills?|technologies|tech stack|competencies)\b", re.I),
    "education":  re.compile(r"\b(education|degree|university|college|diploma)\b", re.I),
}

# High-value keywords that strongly predict ATS filtering
_BOILERPLATE = {
    "the", "and", "for", "with", "that", "this", "are", "have",
    "will", "can", "all", "from", "not", "but", "was",
    # Common job-description verbs that add no signal
    "looking", "seeking", "experienced", "must", "should", "may",
    "able", "work", "use", "using", "include", "including",
    "strong", "good", "well", "also", "both", "within", "across",
    "join", "help", "build", "create", "develop", "deliver",
    "excellent", "plus", "our", "you", "your", "team", "role",
}


class ResumeMatcher:
    """
    Computes ATS score, semantic match score, gap analysis, and
    improvement suggestions for a (resume, job_listing) pair.

    Lazy-loads sentence-transformers on first use to avoid startup cost.
    Falls back to keyword-only scoring if the model is unavailable.
    """

    def __init__(self) -> None:
        self._model = None   # loaded lazily

    # ── Public API ────────────────────────────────────────────────────────────

    def score(self, job_description: str, resume_text: str) -> MatchResult:
        """
        Full scoring pipeline:
          1. Keyword density score
          2. Section presence score
          3. Semantic cosine similarity (lazy loaded)
          4. Weighted composite ATS score
          5. Gap analysis
        """
        kw_score, matched, gaps = self._keyword_score(job_description, resume_text)
        sec_score = self._section_score(resume_text)
        sem_score = self._semantic_score(job_description, resume_text)

        ats = round(0.40 * kw_score + 0.30 * sec_score + 0.30 * sem_score, 4)

        suggestions = self._generate_suggestions(gaps, sec_score)

        return MatchResult(
            ats_score=ats,
            match_score=sem_score,
            keyword_score=kw_score,
            section_score=sec_score,
            gaps=gaps,
            suggestions=suggestions,
            matched_keywords=matched,
        )

    def identify_gaps(self, job_description: str, resume_text: str) -> List[str]:
        """Return only the list of missing important keywords."""
        _, _, gaps = self._keyword_score(job_description, resume_text)
        return gaps

    def suggest_improvements(
        self, gaps: List[str], llm_manager=None
    ) -> List[str]:
        """
        Use LLM to generate targeted resume improvement suggestions.
        Falls back to template suggestions if no LLM available.
        """
        if not gaps:
            return ["Your resume already covers the key requirements."]

        if llm_manager is None:
            return [
                f"Add '{g}' to your skills section or work experience." for g in gaps[:5]
            ]

        prompt = (
            "The following keywords are missing from a candidate's resume for a job application:\n"
            f"{', '.join(gaps[:10])}\n\n"
            "Give 3-5 specific, actionable resume improvement suggestions. "
            "Be concise, practical, and professional."
        )
        try:
            response = llm_manager.generate(prompt, max_tokens=300)
            lines = [l.strip() for l in response.splitlines() if l.strip()]
            return [l for l in lines if len(l) > 10][:6]
        except Exception as exc:
            logger.warning("[ResumeMatcher] LLM suggestion failed: %s", exc)
            return [f"Add '{g}' to your resume." for g in gaps[:5]]

    # ── Keyword scoring ───────────────────────────────────────────────────────

    def _keyword_score(
        self, job_desc: str, resume: str
    ) -> tuple[float, List[str], List[str]]:
        """
        Extract important keywords from job description and check resume coverage.
        Returns (score 0-1, matched_keywords, gap_keywords).
        """
        job_tokens = self._extract_keywords(job_desc)
        resume_lower = resume.lower()

        matched = [t for t in job_tokens if t in resume_lower]
        gaps = [t for t in job_tokens if t not in resume_lower]

        score = len(matched) / max(len(job_tokens), 1)
        return round(score, 4), matched, gaps

    @staticmethod
    def _extract_keywords(text: str) -> List[str]:
        """Extract meaningful keywords from job description (deduplicated, filtered)."""
        tokens = re.findall(r"\b[a-zA-Z][a-zA-Z0-9+#.]{2,}\b", text)
        seen = set()
        keywords = []
        for t in tokens:
            tl = t.lower()
            if tl not in _BOILERPLATE and tl not in seen:
                seen.add(tl)
                keywords.append(tl)
        return keywords[:60]  # cap at 60 most-prominent keywords

    # ── Section scoring ───────────────────────────────────────────────────────

    @staticmethod
    def _section_score(resume: str) -> float:
        """Check presence of key resume sections. Returns 0.0-1.0."""
        found = sum(
            1 for pattern in _SECTION_PATTERNS.values()
            if pattern.search(resume)
        )
        return round(found / len(_SECTION_PATTERNS), 4)

    # ── Semantic similarity ───────────────────────────────────────────────────

    def _semantic_score(self, job_desc: str, resume: str) -> float:
        """
        Cosine similarity via sentence-transformers.
        Falls back to 0.5 (neutral) if model unavailable.
        """
        try:
            model = self._get_model()
            if model is None:
                return 0.5
            import numpy as np
            job_emb = model.encode([job_desc[:1000]], convert_to_numpy=True)[0]
            res_emb = model.encode([resume[:1000]], convert_to_numpy=True)[0]
            cos = float(
                np.dot(job_emb, res_emb)
                / (np.linalg.norm(job_emb) * np.linalg.norm(res_emb) + 1e-9)
            )
            return round(max(0.0, min(1.0, cos)), 4)
        except Exception as exc:
            logger.debug("[ResumeMatcher] Semantic score fallback: %s", exc)
            return 0.5

    def _get_model(self):
        """Lazy-load the embedding model once."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                from config import EMBEDDING_MODEL
                logger.info("[ResumeMatcher] Loading embedding model: %s", EMBEDDING_MODEL)
                self._model = SentenceTransformer(EMBEDDING_MODEL)
            except Exception as exc:
                logger.warning("[ResumeMatcher] Could not load embedding model: %s", exc)
                self._model = False  # sentinel: don't retry
        return self._model if self._model is not False else None

    # ── Suggestions ───────────────────────────────────────────────────────────

    @staticmethod
    def _generate_suggestions(gaps: List[str], section_score: float) -> List[str]:
        """Template-based suggestions (no LLM required)."""
        suggestions = []
        if gaps:
            top_gaps = gaps[:5]
            suggestions.append(
                f"Add these missing keywords to your resume: {', '.join(top_gaps)}"
            )
        if section_score < 0.75:
            missing_sections = [
                name for name, pat in _SECTION_PATTERNS.items()
                if name not in ("summary",)  # already checked
            ]
            suggestions.append(
                f"Ensure your resume has clearly labeled sections: {', '.join(missing_sections)}"
            )
        if not suggestions:
            suggestions.append("Resume looks well-aligned with this job description.")
        return suggestions
