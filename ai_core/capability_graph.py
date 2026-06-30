import logging
from typing import Dict, List, Tuple

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("msa.ai.capabilities")

class CapabilityGraph:
    """Competency mapper selecting the best matching agents based on task classifications."""
    def __init__(self):
        # Maps agent_name -> competency -> score (0.0 to 1.0)
        self.agent_capabilities: Dict[str, Dict[str, float]] = {}

    def register_agent_capabilities(self, agent_name: str, capabilities: Dict[str, float]) -> None:
        self.agent_capabilities[agent_name] = capabilities
        logger.info("Capability Graph registered capabilities for %s", agent_name)

    def route_task(self, required_competency: str) -> List[Tuple[str, float]]:
        """
        Finds and ranks all agents having the required competency.
        Returns a sorted list of (agent_name, score).
        """
        matches = []
        for agent_name, caps in self.agent_capabilities.items():
            if required_competency in caps:
                matches.append((agent_name, caps[required_competency]))
        
        # Sort by capability score descending
        matches.sort(key=lambda x: x[1], reverse=True)
        return matches
