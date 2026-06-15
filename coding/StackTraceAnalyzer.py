"""
coding/StackTraceAnalyzer.py
============================
Parses stack traces, identifying the offending class file, method name,
line number, probable root cause, and recommendations.
"""

import re
import logging
from typing import Dict, Any

logger = logging.getLogger("msa.coding.stacktrace_analyzer")

class StackTraceAnalyzer:
    def __init__(self, llm: Any = None):
        self.llm = llm

    def analyze(self, stacktrace: str) -> Dict[str, Any]:
        """
        Parses exception traces and returns structured source coordinates and fixes.
        """
        if self.llm:
            try:
                return self._llm_analyze(stacktrace)
            except Exception as e:
                logger.warning("LLM stacktrace parse failed: %s. Falling back to regex.", e)

        # Regex models for parsing
        # 1. Java: at com.example.CustomerService.findCustomer(CustomerService.java:55)
        # 2. Python: File "customer.py", line 15, in search_customer
        # 3. JavaScript: at findCustomer (CustomerService.js:55:12) or at CustomerService.js:55:12

        # Let's try matching Java format first
        java_match = re.search(r'at\s+([\w\.\$]+)\.([\w\<]+)\(([^:]+):(\d+)\)', stacktrace)
        if java_match:
            full_class = java_match.group(1)
            method = java_match.group(2)
            filename = java_match.group(3)
            line_no = int(java_match.group(4))

            issue = "java exception"
            suggestion = "Review logic near stack offset"
            if "nullpointerexception" in stacktrace.lower():
                issue = "null object access"
                suggestion = f"Add null validation for fields accessed inside {method}() at line {line_no}."
            elif "classnotfound" in stacktrace.lower():
                issue = "missing class compilation"
                suggestion = f"Add dependency library containing {full_class} to the classpath."

            return {
                "file": filename,
                "line": line_no,
                "issue": issue,
                "suggestion": suggestion,
                "class": full_class,
                "method": method
            }

        # Python format match
        py_match = re.search(r'File\s+"([^"]+)",\s+line\s+(\d+),\s+in\s+(\w+)', stacktrace)
        if py_match:
            filename = py_match.group(1)
            line_no = int(py_match.group(2))
            method = py_match.group(3)

            issue = "python exception"
            suggestion = f"Review function parameters and object state inside {method}()"
            if "keyerror" in stacktrace.lower():
                issue = "dictionary key lookup failure"
                suggestion = f"Use .get() method or add key existence checks inside {method}() at line {line_no}."
            elif "indexerror" in stacktrace.lower():
                issue = "sequence index out of range"
                suggestion = f"Check length of list before accessing index at line {line_no}."

            return {
                "file": filename,
                "line": line_no,
                "issue": issue,
                "suggestion": suggestion,
                "method": method
            }

        # JavaScript format match
        js_match = re.search(r'at\s+(?:([\w\.]+)\s+)?\(?([^:\s\)]+):(\d+):(?:\d+)\)?', stacktrace)
        if js_match:
            method = js_match.group(1) or "anonymous"
            filename = js_match.group(2)
            line_no = int(js_match.group(3))

            issue = "javascript exception"
            suggestion = "Review code structure surrounding JS runtime exception location"
            if "typeerror" in stacktrace.lower():
                issue = "type check mismatch / property invocation error"
                suggestion = f"Ensure object is fully defined before invoking fields inside {method}() at line {line_no}."

            return {
                "file": filename,
                "line": line_no,
                "issue": issue,
                "suggestion": suggestion,
                "method": method
            }

        # Fallback if no matching regex patterns
        # Look for line number anywhere in text
        line_num = 1
        line_search = re.search(r'(?:line\s*:\s*|line\s+|:)\s*(\d+)', stacktrace, re.IGNORECASE)
        if line_search:
            line_num = int(line_search.group(1))

        return {
            "file": "UnknownSource.java",
            "line": line_num,
            "issue": "unparsed runtime exception",
            "suggestion": "Verify variable initialization and trace stack log outputs."
        }

    def _llm_analyze(self, stacktrace: str) -> Dict[str, Any]:
        system_prompt = (
            "You are an expert compiler engineer. Parse the stack trace and return a JSON output "
            "with keys 'file' (str), 'line' (int), 'issue' (str description of problem), "
            "and 'suggestion' (str description of fix). Do not output markdown, return ONLY valid raw JSON."
        )
        response = self.llm.create_chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": stacktrace}
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
