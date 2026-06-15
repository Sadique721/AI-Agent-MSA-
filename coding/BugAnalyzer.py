"""
coding/BugAnalyzer.py
=====================
Analyzes runtime exceptions, application logs, and system error statements,
mapping issues to concrete root causes, severities, and suggested code fixes.
"""

import logging
from typing import Dict, Any

logger = logging.getLogger("msa.coding.bug_analyzer")

class BugAnalyzer:
    def __init__(self, llm: Any = None):
        self.llm = llm

    def analyze(self, error_message: str) -> Dict[str, Any]:
        """
        Analyze a log message or stack trace to extract root cause, severity, and fixes.
        """
        if self.llm:
            try:
                return self._llm_analyze(error_message)
            except Exception as e:
                logger.warning("LLM analyze failed: %s. Falling back to rule-based.", e)

        err_lower = error_message.lower()

        # 1. NullPointerException
        if "nullpointerexception" in err_lower or "npe" in err_lower or "cannot read properties of null" in err_lower or "object is null" in err_lower:
            return {
                "root_cause": "Attempted to access a method or field on an object reference that evaluates to null.",
                "severity": "HIGH",
                "fix": "Add a null validation guard (e.g., 'if (obj != null) { ... }') or initialize the target object before referencing its properties."
            }

        # 2. ClassNotFoundException
        elif "classnotfoundexception" in err_lower or "noclassdeffounderror" in err_lower:
            return {
                "root_cause": "Java virtual machine (JVM) or classloader cannot locate the requested compiled class at runtime.",
                "severity": "HIGH",
                "fix": "Add the missing library/dependency containing the class to your pom.xml (Maven) or build.gradle. Ensure compilation is complete and the classpath contains the library."
            }

        # 3. BeanCreationException
        elif "beancreationexception" in err_lower or "unsatisfieddependencyexception" in err_lower or "could not autowire" in err_lower:
            return {
                "root_cause": "Spring Framework's ApplicationContext encountered a configuration or autowire injection failure while trying to instantiate a bean component.",
                "severity": "CRITICAL",
                "fix": "Verify that the dependency class is annotated with proper component annotations (e.g., '@Service', '@Component', '@Repository'). Ensure proper package scanning or constructor argument resolution is defined."
            }

        # 4. HibernateException
        elif "hibernateexception" in err_lower or "psqlexception" in err_lower or "mysqlserverexception" in err_lower or "sqlstate" in err_lower:
            return {
                "root_cause": "Database connection or ORM mapping exception. Likely caused by invalid table column mappings, SQL syntax issues, or DB credentials failure.",
                "severity": "HIGH",
                "fix": "Verify JpaEntity properties and naming annotations match the active database schema. Ensure connection url, database username, and password properties are correct in application.properties or application.yml."
            }

        # 5. Angular dependency injection / module error
        elif "injectorerror" in err_lower or "angular dependency" in err_lower or "no provider for" in err_lower:
            return {
                "root_cause": "Angular Dependency Injection failure. The module or component requires a provider dependency that has not been imported or declared.",
                "severity": "MEDIUM",
                "fix": "Declare the requested Service provider in your Angular Module's 'providers' array, or add the corresponding dependency module (e.g., HttpClientModule) to the 'imports' configuration."
            }

        # 6. JavaScript runtime ReferenceError / TypeError
        elif "typeerror:" in err_lower or "referenceerror:" in err_lower or "is not defined" in err_lower or "is not a function" in err_lower:
            return {
                "root_cause": "JavaScript runtime type violation or variable reference scoping mismatch. Invoking undefined object properties or functions.",
                "severity": "MEDIUM",
                "fix": "Confirm variable declarations are scoped correctly using let/const. Add defensive checks (e.g. optional chaining: 'obj?.func()') before calling callbacks or methods."
            }

        # Generic fallback
        return {
            "root_cause": "Generic runtime execution error detected in standard logs.",
            "severity": "MEDIUM",
            "fix": "Inspect class references, ensure all external dependencies are correctly loaded, check logic parameters, and verify network connectivity if APIs are being requested."
        }

    def _llm_analyze(self, error_message: str) -> Dict[str, Any]:
        system_prompt = (
            "You are a Senior Debugging Specialist. Analyze the provided error log/exception trace. "
            "Return a JSON response with keys 'root_cause', 'severity' (LOW/MEDIUM/HIGH/CRITICAL), "
            "and 'fix' (with clean step-by-step suggestions). Do not format output as markdown code block, return raw JSON."
        )
        response = self.llm.create_chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": error_message}
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
