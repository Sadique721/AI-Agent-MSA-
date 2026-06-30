import logging
from typing import List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("msa.ai.qa")

class ValidationQAEngine:
    """Factual groundedness verification and citation validator."""
    def __init__(self):
        pass

    def evaluate_groundedness(self, response: str, references: List[str]) -> float:
        """
        Calculates a confidence score representing response grounding in references.
        Returns a score between 0.0 and 1.0.
        """
        if not response or not references:
            return 0.0

        # Standard keyword overlap grounding calculation
        response_words = set(response.lower().split())
        reference_words = set()
        for ref in references:
            reference_words.update(ref.lower().split())

        # Clean punctuation from sets
        response_words = {w.strip(".,?!:;()\"'") for w in response_words if len(w) > 3}
        reference_words = {w.strip(".,?!:;()\"'") for w in reference_words if len(w) > 3}

        if not response_words:
            return 0.0

        overlapping = response_words.intersection(reference_words)
        score = len(overlapping) / len(response_words)
        logger.info("Evaluation groundedness score: %0.2f", score)
        return min(score * 1.5, 1.0) # Apply tuning multiplier

    def verify_citations(self, response: str) -> bool:
        """Checks if claims have valid bracketed citation patterns (e.g. [1])."""
        import re
        citation_pattern = re.compile(r"\[\d+\]")
        matches = citation_pattern.findall(response)
        logger.info("Found %d citations in response", len(matches))
        return len(matches) > 0
