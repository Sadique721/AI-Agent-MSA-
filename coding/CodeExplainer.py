"""
coding/CodeExplainer.py
======================
Explains source code blocks, providing line-by-line breakdowns
along with high-level architectural summaries.
"""

import logging
from typing import Dict, Any, List

logger = logging.getLogger("msa.coding.explainer")

class CodeExplainer:
    def __init__(self, llm: Any = None):
        self.llm = llm

    def explain(self, code: str) -> Dict[str, Any]:
        """
        Generates line-by-line descriptions of structural functionality.
        """
        if self.llm:
            try:
                return self._llm_explain(code)
            except Exception as e:
                logger.warning("LLM explain failed: %s. Falling back to rule-based.", e)

        lines = code.splitlines()
        line_exps = []
        summary = "Class or method detailing operations, configuration mappings, or REST controllers."

        # Detect high level context
        code_lower = code.lower()
        if "springbootapplication" in code_lower:
            summary = "Primary configuration launcher bootstrapping the Spring Boot Application context."
        elif "restcontroller" in code_lower:
            summary = "Spring MVC Controller exposing REST API routes to retrieve, delete, and post database assets."
        elif "service" in code_lower and ("class" in code_lower or "@service" in code_lower):
            summary = "Spring Service class implementing core business logic calculations."
        elif "def " in code_lower:
            summary = "Python script executing search algorithms or processing operational inputs."

        for i, line in enumerate(lines, 1):
            trimmed = line.strip()
            if not trimmed:
                continue
            
            explanation = "Defines structural logic sequence"
            
            if trimmed.startswith("package "):
                explanation = "Specifies namespace grouping module structure mapping."
            elif trimmed.startswith("import "):
                explanation = "References and loads external library structures."
            elif trimmed.startswith("@RestController"):
                explanation = "Spring stereotype designating controller routing."
            elif trimmed.startswith("@Autowired"):
                explanation = "Triggers automatic dependency injection of spring beans."
            elif trimmed.startswith("public class ") or trimmed.startswith("class "):
                explanation = "Declares active component class structure definition."
            elif trimmed.startswith("public interface ") or trimmed.startswith("interface "):
                explanation = "Declares contract repository structure."
            elif "@GetMapping" in trimmed:
                explanation = "Binds HTTP GET requests to mapping path handler."
            elif "@PostMapping" in trimmed:
                explanation = "Binds HTTP POST payload requests to handler."
            elif "def " in trimmed:
                explanation = "Defines callable python method sequence."
            elif trimmed.startswith("return "):
                explanation = "Returns output results from execution block."
            elif "assert" in trimmed:
                explanation = "Asserts expected test outcome conditions."

            line_exps.append({
                "line": i,
                "code": line,
                "explanation": explanation
            })

        return {
            "summary": summary,
            "line_explanations": line_exps
        }

    def _llm_explain(self, code: str) -> Dict[str, Any]:
        system_prompt = (
            "You are a Senior Software Educator. Explain the provided source code. "
            "Return a JSON response with keys 'summary' (overall view) and "
            "'line_explanations' (list of objects with 'line' (int), 'code' (str), and "
            "'explanation' (str)). Keep descriptions simple. Do not output markdown, "
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
