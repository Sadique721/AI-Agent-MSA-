import logging
import time
from typing import Dict, Any, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("msa.ai.world")

class Entity:
    def __init__(self, entity_id: str, label: str, properties: Dict[str, Any] = None):
        self.entity_id = entity_id
        self.label = label
        self.properties = properties or {}
        self.updated_at = time.time()

class WorldModel:
    """Enterprise world representation mapping systems state changes."""
    def __init__(self):
        self.entities: Dict[str, Entity] = {}
        # List of tuples: (source_id, relation, target_id)
        self.relations: List[tuple] = []

    def set_entity(self, entity_id: str, label: str, properties: Dict[str, Any] = None) -> None:
        self.entities[entity_id] = Entity(entity_id, label, properties)
        logger.info("World Model set entity %s (%s)", label, entity_id)

    def add_relation(self, source_id: str, relation: str, target_id: str) -> None:
        self.relations.append((source_id, relation, target_id))
        logger.info("World Model link: %s --[%s]--> %s", source_id, relation, target_id)

    def get_entity_relations(self, entity_id: str) -> List[tuple]:
        return [r for r in self.relations if r[0] == entity_id or r[2] == entity_id]
