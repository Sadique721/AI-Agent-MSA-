"""
coding/__init__.py
==================
Phase-3 Coding Agent package. Exposes all the autonomous software engineering helpers.
"""

from coding.CodeGenerator import CodeGenerator
from coding.BugAnalyzer import BugAnalyzer
from coding.StackTraceAnalyzer import StackTraceAnalyzer
from coding.ProjectGenerator import ProjectGenerator
from coding.RefactorEngine import RefactorEngine
from coding.TestGenerator import TestGenerator
from coding.CodeExplainer import CodeExplainer
from coding.CodeReviewer import CodeReviewer
from coding.CodingAgent import CodingAgent
from coding.CodingMemory import CodingMemory
from coding.CodingValidator import CodingValidator

__all__ = [
    "CodeGenerator",
    "BugAnalyzer",
    "StackTraceAnalyzer",
    "ProjectGenerator",
    "RefactorEngine",
    "TestGenerator",
    "CodeExplainer",
    "CodeReviewer",
    "CodingAgent",
    "CodingMemory",
    "CodingValidator",
]
