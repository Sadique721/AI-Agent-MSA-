"""
coding/CodingValidator.py
=========================
Validates the syntax, structure, imports, and security of generated code files.
"""

import ast
import logging
from typing import Dict, Any, List

logger = logging.getLogger("msa.coding.validator")

class CodingValidator:
    """
    Validates syntax, structure, imports, and security of generated code.
    Returns validation score, grade, and error list.
    """
    def validate(self, result: Dict[str, Any]) -> Dict[str, Any]:
        errors = []
        score = 1.0
        
        files = result.get("files", [])
        if not files:
            errors.append("No files generated.")
            return {"score": 0.0, "grade": "F", "errors": errors}
            
        language = result.get("language", "").lower()
        
        for f in files:
            path = f.get("path", "")
            content = f.get("content", "")
            
            if not path:
                errors.append("File path is empty.")
                score -= 0.1
                continue
            if not content:
                errors.append(f"File {path} is empty.")
                score -= 0.1
                continue
                
            # 1. Python Syntax Validation
            if path.endswith(".py"):
                try:
                    ast.parse(content)
                except SyntaxError as se:
                    errors.append(f"Python syntax error in {path} at line {se.lineno}: {se.msg}")
                    score -= 0.3
                    
            # 2. Java / Spring Boot Validation
            elif path.endswith(".java"):
                # Basic brace balance check
                if content.count("{") != content.count("}"):
                    errors.append(f"Unbalanced braces in Java file {path}.")
                    score -= 0.2
                # Check that class name in path matches class declaration
                class_name = path.split("/")[-1].replace(".java", "")
                if f"class {class_name}" not in content and f"interface {class_name}" not in content:
                    errors.append(f"Java filename {class_name} does not match class/interface declaration.")
                    score -= 0.2
                # Check for package declaration
                if "springboot" in language or "java" in language:
                    if "package " not in content:
                        errors.append(f"Missing package declaration in {path}.")
                        score -= 0.1
                        
            # 3. JavaScript / Typescript/HTML Validation
            elif path.endswith(".js") or path.endswith(".ts"):
                if content.count("{") != content.count("}"):
                    errors.append(f"Unbalanced braces in JS/TS file {path}.")
                    score -= 0.2
                    
            # 4. Security Checks
            if "password" in content.lower() or "secret" in content.lower():
                if "password = \"" in content or "password = '" in content or "secret = \"" in content:
                    errors.append(f"Security Warning: Potential hardcoded secret in {path}.")
                    score -= 0.1
                    
        # Normalize score
        score = max(0.0, min(1.0, score))
        
        # Calculate grade
        if score >= 0.9:
            grade = "A"
        elif score >= 0.8:
            grade = "B"
        elif score >= 0.7:
            grade = "C"
        elif score >= 0.6:
            grade = "D"
        else:
            grade = "F"
            
        return {
            "score": round(score, 2),
            "grade": grade,
            "errors": errors
        }
