import time
import json
import logging
import threading
from typing import Dict, Any, Optional
from infrastructure.service_registry import BaseService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("msa.ai.runtime")

class AgentState:
    def __init__(self, agent_id: str, name: str):
        self.agent_id = agent_id
        self.name = name
        self.status = "idle"  # idle, running, hibernated, dead
        self.heartbeat = time.time()
        self.memory_snapshot = {}

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "status": self.status,
            "heartbeat": self.heartbeat,
            "memory_snapshot": self.memory_snapshot
        }

class CognitiveRuntime(BaseService):
    """
    Enterprise Cognitive Runtime Engine supervising multi-agent sessions,
    heartbeats, and checkpoint snapshots.
    """
    def __init__(self):
        super().__init__()
        self.active_agents: Dict[str, AgentState] = {}
        self._lock = threading.Lock()
        self._supervisor_thread: Optional[threading.Thread] = None
        self._running = False

    def register_agent(self, agent_id: str, name: str) -> None:
        with self._lock:
            self.active_agents[agent_id] = AgentState(agent_id, name)
            logger.info("Cognitive Runtime registered agent %s (%s)", name, agent_id)

    def record_heartbeat(self, agent_id: str) -> None:
        with self._lock:
            if agent_id in self.active_agents:
                self.active_agents[agent_id].heartbeat = time.time()
                self.active_agents[agent_id].status = "active"

    def create_checkpoint(self, agent_id: str, state_data: dict) -> bool:
        with self._lock:
            if agent_id not in self.active_agents:
                return False
            self.active_agents[agent_id].memory_snapshot = state_data
            logger.info("Saved runtime checkpoint for agent %s", agent_id)
            return True

    def load_checkpoint(self, agent_id: str) -> Optional[dict]:
        with self._lock:
            if agent_id in self.active_agents:
                return self.active_agents[agent_id].memory_snapshot
            return None

    def start(self) -> None:
        super().start()
        self._running = True
        self._supervisor_thread = threading.Thread(target=self._supervise, daemon=True)
        self._supervisor_thread.start()
        logger.info("Cognitive Runtime Engine started.")

    def stop(self) -> None:
        super().stop()
        self._running = False
        if self._supervisor_thread:
            self._supervisor_thread.join(timeout=1.0)
        logger.info("Cognitive Runtime Engine stopped.")

    def _supervise(self) -> None:
        """Background thread supervising agent heartbeats and flags timeouts."""
        while self._running:
            now = time.time()
            with self._lock:
                for agent_id, state in list(self.active_agents.items()):
                    # If no heartbeat for > 5 seconds, mark as dead/dormant
                    if now - state.heartbeat > 5.0 and state.status == "active":
                        state.status = "dead"
                        logger.warning("Agent %s (%s) heartbeat timeout detected.", state.name, agent_id)
            time.sleep(1.0)
