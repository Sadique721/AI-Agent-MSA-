import logging
from typing import Dict, List, Any, Optional
from infrastructure.service_registry import BaseService

logger = logging.getLogger("msa.backend.planner.agent")

class TaskNode:
    """Represents a single step or task execution unit in the Planner's graph."""
    def __init__(self, task_id: str, agent_name: str, description: str, dependencies: Optional[List[str]] = None):
        self.task_id = task_id
        self.agent_name = agent_name
        self.description = description
        self.dependencies = dependencies or []
        self.status = "pending"  # pending, running, completed, failed
        self.result = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "agent_name": self.agent_name,
            "description": self.description,
            "dependencies": self.dependencies,
            "status": self.status
        }

class TaskGraph:
    """Directed Acyclic Graph (DAG) for multi-task multi-agent executions."""
    def __init__(self):
        self.nodes: Dict[str, TaskNode] = {}

    def add_node(self, node: TaskNode) -> None:
        self.nodes[node.task_id] = node

    def get_executable_nodes(self) -> List[TaskNode]:
        """Returns nodes that have no unmet dependencies and are pending execution."""
        executable = []
        for node in self.nodes.values():
            if node.status != "pending":
                continue
            # Check if all dependency nodes are completed
            unmet = False
            for dep_id in node.dependencies:
                dep_node = self.nodes.get(dep_id)
                if not dep_node or dep_node.status != "completed":
                    unmet = True
                    break
            if not unmet:
                executable.append(node)
        return executable

    def is_complete(self) -> bool:
        """Returns True if all nodes in the DAG have successfully completed."""
        return all(node.status == "completed" for node in self.nodes.values())

    def has_failures(self) -> bool:
        """Returns True if any nodes failed."""
        return any(node.status == "failed" for node in self.nodes.values())

class PlannerAgent(BaseService):
    """Planner Agent responsible for understanding goal, decomposition, and routing."""
    def __init__(self):
        super().__init__()
        logger.info("PlannerAgent service initialised.")

    def decompose(self, query: str) -> TaskGraph:
        """Decomposes a query into a structured TaskGraph based on heuristics."""
        logger.info("Decomposing user request: '%s'", query)
        graph = TaskGraph()
        lower = query.lower().strip()

        # Simple classification heuristics for multi-agent workflows
        if any(kw in lower for kw in ("news", "latest", "weather", "google", "search")):
            # Web research workflow
            graph.add_node(TaskNode("t1", "ResearchAgent", "Execute DuckDuckGo/Playwright search query"))
            graph.add_node(TaskNode("t2", "MemoryAgent", "Verify recent conversation context", dependencies=["t1"]))
            graph.add_node(TaskNode("t3", "ValidatorAgent", "Assess facts and format references", dependencies=["t2"]))
        elif any(kw in lower for kw in ("code", "debug", "fix", "refactor", "test")):
            # Coding intelligence workflow
            graph.add_node(TaskNode("t1", "CodingAgent", "Analyze AST and generate solution"))
            graph.add_node(TaskNode("t2", "ValidatorAgent", "Validate generated script formatting", dependencies=["t1"]))
        else:
            # Standard conversational or local knowledge query
            graph.add_node(TaskNode("t1", "MemoryAgent", "Retrieve semantic facts from local RAG store"))
            graph.add_node(TaskNode("t2", "ValidatorAgent", "Generate friendly verified response", dependencies=["t1"]))

        return graph
