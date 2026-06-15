"""
coding/CodeReviewer.py
======================
Analyzes security, performance, readability, SOLID principles, and
architecture. Scores code from Grade A to F with suggestions.
"""

import logging
from typing import Dict, Any, List

logger = logging.getLogger("msa.coding.reviewer")

class CodeReviewer:
    def __init__(self, llm: Any = None):
        self.llm = llm

    def review(self, code: str) -> Dict[str, Any]:
        """
        Analyzes source code quality and produces a comprehensive review grade.
        """
        if self.llm:
            try:
                return self._llm_review(code)
            except Exception as e:
                logger.warning("LLM review failed: %s. Falling back to rule-based.", e)

        comments = []
        score = 100
        code_lower = code.lower()

        # 1. Security Check: Hardcoded API keys / passwords
        if "api_key" in code_lower or "password" in code_lower or "secret" in code_lower:
            if "env" not in code_lower and "properties" not in code_lower:
                comments.append("[Security] Hardcoded sensitive key or password variable detected. Move secrets to environment config files.")
                score -= 20

        # 2. Security Check: SQL Injection vulnerability (string concat inside SQL)
        if "select " in code_lower and " + " in code_lower and ("where" in code_lower or "like" in code_lower):
            comments.append("[Security] SQL query string concatenation detected. Prone to SQL Injection. Use PreparedStatement or parameter binding.")
            score -= 25

        # 3. Performance Check: Double nested loop
        if code.count("for") >= 2 and ("while" in code_lower or "for " in code_lower):
            # Simple check for nested loops
            if "for (int i" in code and "for (int j" in code:
                comments.append("[Performance] Nested loops detected (O(N^2) complexity). Consider mapping elements to a HashMap or reducing complexity.")
                score -= 15

        # 4. SOLID: Fat class/methods
        lines = code.splitlines()
        if len(lines) > 150:
            comments.append("[Architecture] Large class block detected (over 150 lines). Split concerns to adhere to the Single Responsibility Principle.")
            score -= 10

        # 5. Readability / Maintainability
        if len(comments) == 0:
            comments.append("[Readability] Code structure is modular and cleanly formatted.")

        # Grade resolution
        if score >= 90:
            grade = "A"
        elif score >= 80:
            grade = "B"
        elif score >= 70:
            grade = "C"
        elif score >= 50:
            grade = "D"
        else:
            grade = "F"

        return {
            "score": score / 100.0,
            "grade": grade,
            "comments": comments,
            "valid": True if score >= 70 else False
        }

    def _llm_review(self, code: str) -> Dict[str, Any]:
        system_prompt = (
            "You are a Principal Software Architect. Review the provided code for security, "
            "performance, readability, maintainability, and SOLID principles. Return a JSON "
            "response with keys: 'score' (float 0.0 to 1.0), 'grade' (A/B/C/D/F), and "
            "'comments' (list of detailed string comments). Do not output markdown, "
            "return ONLY valid raw JSON."
        )
        response = self.llm.create_chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": code}
            ],
            temperature=0.1
        )
        raw_text = response['choices'][0]['message']['content'].strip()
        if raw_text.startswith("```json"):
            raw_text = raw_text[7:]
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3]
        import json
        return json.loads(raw_text.strip())
