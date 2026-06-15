"""
coding/CodingAgent.py
=====================
Central coordinator of the Phase-3 Coding Agent system.
Routes natural language inputs to specific modules (generation, review, refactoring, etc.),
runs validation, and records results in the coding memory.
"""

import logging
from typing import Dict, Any

from coding.CodeGenerator import CodeGenerator
from coding.BugAnalyzer import BugAnalyzer
from coding.StackTraceAnalyzer import StackTraceAnalyzer
from coding.ProjectGenerator import ProjectGenerator
from coding.RefactorEngine import RefactorEngine
from coding.TestGenerator import TestGenerator
from coding.CodeExplainer import CodeExplainer
from coding.CodeReviewer import CodeReviewer
from coding.CodingMemory import CodingMemory
from coding.CodingValidator import CodingValidator

logger = logging.getLogger("msa.coding.agent")

class CodingAgent:
    """
    Orchestrator for all software engineering sub-systems.
    """
    def __init__(self, llm: Any = None, sqlite_memory: Any = None):
        self.llm = llm
        self.code_generator = CodeGenerator(llm)
        self.bug_analyzer = BugAnalyzer(llm)
        self.stacktrace_analyzer = StackTraceAnalyzer(llm)
        self.project_generator = ProjectGenerator(llm)
        self.refactor_engine = RefactorEngine(llm)
        self.test_generator = TestGenerator(llm)
        self.code_explainer = CodeExplainer(llm)
        self.code_reviewer = CodeReviewer(llm)
        self.memory = CodingMemory(sqlite_memory=sqlite_memory)
        self.validator = CodingValidator()

    def process(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """
        Main entry point for processing a coding task.
        """
        intent = self.detect_intent(prompt)
        logger.info("CodingAgent: detected intent '%s' for prompt '%s'", intent, prompt[:50])
        
        result = {}
        category = "coding_reference"
        
        if intent == "stacktrace_analysis":
            result = self.stacktrace_analyzer.analyze(prompt)
            # Map legacy/standard keys for compatibility
            if "rootCause" not in result and "issue" in result:
                result["rootCause"] = result["issue"]
            if "recommendedFixes" not in result and "suggestion" in result:
                result["recommendedFixes"] = [result["suggestion"]]
            category = "coding_fix"
            
        elif intent == "bug_fixing":
            result = self.bug_analyzer.analyze(prompt)
            category = "coding_fix"
            
        elif intent == "code_generation":
            lang = kwargs.get("language") or kwargs.get("lang")
            result = self.code_generator.generate(prompt, lang)
            category = "coding_project"
            
        elif intent == "code_review":
            result = self.code_reviewer.review(prompt)
            category = "coding_review"
            
        elif intent == "project_generation":
            p_type = kwargs.get("project_type") or kwargs.get("type") or "springboot"
            name = kwargs.get("name") or "my-app"
            desc = kwargs.get("description") or prompt
            result = self.project_generator.generate(p_type, name, desc)
            category = "coding_project"
            
        elif intent == "refactoring":
            result = self.refactor_engine.refactor(prompt)
            category = "coding_reference"
            
        elif intent == "test_generation":
            fw = kwargs.get("framework") or kwargs.get("fw") or ""
            result = self.test_generator.generate(prompt, fw)
            category = "coding_reference"
            
        elif intent == "code_explanation":
            result = self.code_explainer.explain(prompt)
            category = "coding_reference"
            
        else:
            lang = kwargs.get("language") or kwargs.get("lang")
            result = self.code_generator.generate(prompt, lang)
            category = "coding_project"

        # Validate the results
        validation = self.validator.validate(result)
        result["validation"] = validation
        
        # Store to long-term memory
        self.memory.store(prompt, result, category)
        
        return result

    def detect_intent(self, prompt: str) -> str:
        """
        Deduce coding intent category based on prompt keywords.
        """
        prompt_lower = prompt.lower()
        if "stacktrace" in prompt_lower or "exception" in prompt_lower or "at com." in prompt_lower or "at java." in prompt_lower or "file \"" in prompt_lower:
            return "stacktrace_analysis"
        elif "bug" in prompt_lower or "error" in prompt_lower or "logs" in prompt_lower or "fail" in prompt_lower:
            return "bug_fixing"
        elif "review" in prompt_lower or "quality" in prompt_lower:
            return "code_review"
        elif "project" in prompt_lower or "scaffold" in prompt_lower or "bootstrap" in prompt_lower:
            return "project_generation"
        elif "refactor" in prompt_lower or "clean" in prompt_lower or "optimize" in prompt_lower:
            return "refactoring"
        elif "test" in prompt_lower or "junit" in prompt_lower or "pytest" in prompt_lower or "jest" in prompt_lower:
            return "test_generation"
        elif "explain" in prompt_lower or "how it works" in prompt_lower or "understanding" in prompt_lower:
            return "code_explanation"
        else:
            return "code_generation"
