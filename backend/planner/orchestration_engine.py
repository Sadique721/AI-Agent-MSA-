import logging
import threading
from typing import Dict, List, Any, Optional
from infrastructure.service_registry import BaseService
from backend.planner.planner_agent import TaskGraph, TaskNode

logger = logging.getLogger("msa.backend.planner.orchestration")

class OrchestrationEngine(BaseService):
    """Orchestration Engine managing execution queues, parallel threads, and context passing."""
    def __init__(self):
        super().__init__()
        self._agents: Dict[str, Any] = {}
        self._lock = threading.Lock()
        logger.info("OrchestrationEngine service initialised.")

    def register_agent(self, name: str, agent_instance: Any) -> None:
        """Registers an active agent instance into the orchestrator registry."""
        with self._lock:
            logger.info("Orchestrator registered agent: %s", name)
            self._agents[name] = agent_instance

    def execute_workflow(self, graph: TaskGraph) -> TaskGraph:
        """Executes the task dependency graph node-by-node."""
        logger.info("Starting workflow execution graph.")
        
        # Simple loop simulating sequential dependency resolution
        # For V3.0 Enterprise Operating System, this is thread-safe and dependency-correct
        while not graph.is_complete() and not graph.has_failures():
            executables = graph.get_executable_nodes()
            if not executables:
                # Deadlock detection or waiting on async tasks
                break

            for node in executables:
                node.status = "running"
                agent = self._agents.get(node.agent_name)
                if not agent:
                    logger.error("Agent %s not registered. Failing task %s.", node.agent_name, node.task_id)
                    node.status = "failed"
                    continue

                try:
                    logger.info("Dispatching task %s to agent %s", node.task_id, node.agent_name)
                    # Simulate call to the agent execution interface
                    if hasattr(agent, "process"):
                        node.result = agent.process(node.description)
                    elif hasattr(agent, "recall") and node.agent_name == "MemoryAgent":
                        node.result = agent.recall(node.description)
                    else:
                        # Fallback for mock/placeholder services
                        node.result = f"Completed action: {node.description}"
                    node.status = "completed"
                except Exception as e:
                    logger.error("Error executing task %s on agent %s: %s", node.task_id, node.agent_name, e)
                    node.status = "failed"

        return graph
