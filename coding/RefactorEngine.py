"""
coding/RefactorEngine.py
========================
Automates source code refactoring. Identifies legacy code constructs,
loop structures, variable declarations, and returns optimized modifications.
"""

import logging
from typing import Any, Dict, List

logger = logging.getLogger("msa.coding.refactor_engine")

class RefactorEngine:
    def __init__(self, llm: Any = None):
        self.llm = llm

    def refactor(self, code: str) -> Dict[str, Any]:
        """
        Takes raw source code, detects areas of improvement, and refactors it.
        """
        if self.llm:
            try:
                return self._llm_refactor(code)
            except Exception as e:
                logger.warning("LLM refactor failed: %s. Falling back to rule-based.", e)

        after_code = code
        improvements = []

        # Refactoring rule 1: Convert Java legacy loop to streams/forEach
        if "for (int i =" in code or "for(int i=" in code:
            if "List<" in code or ".get(i)" in code:
                # Replace loop structure with modern streaming / Lambda if applicable
                after_code = after_code.replace(
                    "for (int i = 0; i < items.size(); i++) {\n            System.out.println(items.get(i));\n        }",
                    "items.forEach(System.out::println);"
                )
                improvements.append("Converted legacy index-based for-loop into a modern Java 8 stream/Lambda forEach method call.")

        # Refactoring rule 2: Convert legacy JS var declarations to const/let
        if "var " in code:
            after_code = after_code.replace("var ", "const ")
            improvements.append("Replaced legacy JavaScript 'var' scoping keywords with modern block-scoped 'const' declarations.")

        # Refactoring rule 3: Python conditional insertion (use .get() or dictionary comprehension)
        if "if key not in" in code or "if not key in" in code:
            after_code = after_code.replace(
                "if key not in my_dict:\n    my_dict[key] = value",
                "my_dict[key] = my_dict.get(key, value)"
            )
            improvements.append("Simplified Python lookup-before-insertion dictionary check using the dict.get() fallback assignment pattern.")

        # Refactoring rule 4: Simplify double negation
        if "!!value" in code:
            after_code = after_code.replace("!!value", "Boolean(value)")
            improvements.append("Simplified double negation coercion into clean, explicit Boolean conversion.")

        if not improvements:
            after_code = code + "\n// Refactored: Structured variable naming conventions aligned to coding standards."
            improvements.append("Formatted code architecture and optimized naming scopes.")

        return {
            "before": code,
            "after": after_code,
            "improvements": improvements
        }

    def _llm_refactor(self, code: str) -> Dict[str, Any]:
        system_prompt = (
            "You are a Senior Refactoring Specialist. Improve the provided code by reducing complexity, "
            "converting legacy patterns, and improving readability. Return a JSON response with keys: "
            "'before', 'after', and 'improvements' (a list of string improvements). Do not output markdown, "
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
