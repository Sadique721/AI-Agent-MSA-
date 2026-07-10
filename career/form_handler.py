"""
career/form_handler.py
======================
Multi-step form field detection, classification, and auto-filling (V8).

Intelligently classifies page inputs and fills standard values, answers
multiple-choice or yes/no screeners, and handles file uploads.
"""
from __future__ import annotations

import logging
import os
import re
from typing import Dict, List, Optional

logger = logging.getLogger("msa.career.form_handler")

# Field identification mappings
_FIELD_CLASSES = {
    "name":      re.compile(r"\b(name|full\s*name|first\s*name|last\s*name)\b", re.I),
    "email":     re.compile(r"\b(email|e-mail|mail\s*address)\b", re.I),
    "phone":     re.compile(r"\b(phone|mobile|telephone|contact\s*num)\b", re.I),
    "resume":    re.compile(r"\b(resume|cv|curriculum\s*vitae)\b", re.I),
    "cover_letter": re.compile(r"\b(cover\s*letter|letter|message|notes?)\b", re.I),
    "website":   re.compile(r"\b(portfolio|website|github|linkedin|social)\b", re.I),
    "salary":    re.compile(r"\b(salary|compensation|expectation)\b", re.I),
}


class FormHandler:
    """
    Analyzes forms and interacts with inputs using Playwright.
    """

    def fill_standard_fields(self, page, data: Dict[str, str]) -> None:
        """Locates standard inputs and fills them using matching selectors."""
        inputs = page.locator("input, textarea").all()
        for field in inputs:
            try:
                if not field.is_visible():
                    continue

                # Fetch field identification clues
                attr_name = (field.get_attribute("name") or "").lower()
                attr_id = (field.get_attribute("id") or "").lower()
                placeholder = (field.get_attribute("placeholder") or "").lower()
                label = ""

                # Try finding associated label text
                if attr_id:
                    lbl = page.locator(f"label[for='{attr_id}']").first
                    if lbl.count() > 0:
                        label = lbl.inner_text().lower()

                clues = f"{attr_name} {attr_id} {placeholder} {label}"

                # Classify and fill
                filled = False
                for field_type, pattern in _FIELD_CLASSES.items():
                    if pattern.search(clues):
                        val = data.get(field_type)
                        if val:
                            field.fill(val)
                            logger.debug("[FormHandler] Filled %s field with: %s", field_type, val)
                            filled = True
                            break

                if not filled and "salary" in clues:
                    # Default salary expectation fallback
                    field.fill("As per industry standards / Negotiable")

            except Exception as exc:
                logger.debug("[FormHandler] Field processing failed: %s", exc)

    def upload_file(self, page, file_path: str, field_label: str = "resume") -> bool:
        """Finds file inputs (e.g., input[type=file]) and sets the file."""
        if not os.path.exists(file_path):
            logger.warning("[FormHandler] File path does not exist: %s", file_path)
            return False

        try:
            # Look for file inputs
            file_inputs = page.locator("input[type='file']").all()
            for file_in in file_inputs:
                clues = (
                    (file_in.get_attribute("name") or "")
                    + " " + (file_in.get_attribute("id") or "")
                ).lower()
                if field_label in clues or not file_inputs:
                    file_in.set_input_files(file_path)
                    logger.info("[FormHandler] Uploaded %s to field", file_path)
                    return True

            # If no name/id matches, try first file input
            if file_inputs:
                file_inputs[0].set_input_files(file_path)
                logger.info("[FormHandler] Uploaded %s to first file input", file_path)
                return True

            # Try file chooser fallback via page.click on file button
            try:
                with page.expect_file_chooser() as fc_info:
                    page.get_by_text("upload", exact=False).first.click(timeout=3000)
                file_chooser = fc_info.value
                file_chooser.set_files(file_path)
                logger.info("[FormHandler] Uploaded %s via file chooser click", file_path)
                return True
            except Exception:
                pass

        except Exception as exc:
            logger.warning("[FormHandler] File upload failed: %s", exc)
        return False

    def fill_text_area(self, page, term: str, text: str) -> bool:
        """Finds a textarea containing term and fills it."""
        try:
            textareas = page.locator("textarea").all()
            for area in textareas:
                clues = (
                    (area.get_attribute("name") or "")
                    + " " + (area.get_attribute("id") or "")
                    + " " + (area.get_attribute("placeholder") or "")
                ).lower()
                if term.lower() in clues:
                    area.fill(text)
                    return True

            if textareas:
                textareas[0].fill(text)
                return True
        except Exception as exc:
            logger.debug("[FormHandler] fill_text_area failed: %s", exc)
        return False
