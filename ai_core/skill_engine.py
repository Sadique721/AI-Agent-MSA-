import logging
from typing import Dict, Callable, Any, Set

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("msa.ai.skills")

class Skill:
    def __init__(self, name: str, description: str, handler: Callable[..., Any], required_params: Set[str]):
        self.name = name
        self.description = description
        self.handler = handler
        self.required_params = required_params

class SkillEngine:
    """Reusable skill registry for composing dynamic agent capabilities."""
    def __init__(self):
        self._registry: Dict[str, Skill] = {}

    def register_skill(self, name: str, description: str, handler: Callable[..., Any], required_params: Set[str]) -> None:
        self._registry[name] = Skill(name, description, handler, required_params)
        logger.info("Skill Registry registered: %s", name)

    def execute_skill(self, skill_name: str, **kwargs) -> Any:
        skill = self._registry.get(skill_name)
        if not skill:
            raise ValueError(f"Skill '{skill_name}' not found in registry.")

        # Validate parameters
        missing = skill.required_params - set(kwargs.keys())
        if missing:
            raise ValueError(f"Skill '{skill_name}' missing required parameters: {missing}")

        try:
            logger.info("Executing skill %s with params %s", skill_name, kwargs)
            return skill.handler(**kwargs)
        except Exception as e:
            logger.error("Failed to execute skill %s: %s", skill_name, e)
            raise e

    def list_skills(self) -> Dict[str, str]:
        return {name: skill.description for name, skill in self._registry.items()}
