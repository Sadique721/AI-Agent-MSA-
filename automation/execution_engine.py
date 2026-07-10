"""
automation/execution_engine.py
================================
Wraps SwarmCoordinator with retry logic for autonomous multi-step tasks.
"""
import logging
import time
from typing import Dict, Any

logger = logging.getLogger("msa.automation")


class WorkflowEngine:
    def __init__(self, swarm_coordinator):
        self.swarm = swarm_coordinator

    def execute_autonomous_workflow(self, goal: str, max_retries: int = 3) -> Dict[str, Any]:
        last_error = None
        for attempt in range(1, max_retries + 1):
            try:
                logger.info("Workflow attempt %d/%d for: %s", attempt, max_retries, goal)
                result = self.swarm.orchestrate_task(goal)
                if result.get("status") == "completed":
                    result["attempts"] = attempt
                    return result
            except Exception as e:
                last_error = str(e)
                logger.warning("Workflow attempt %d failed: %s", attempt, e)
                time.sleep(1.5 * attempt)  # backoff
        return {"status": "failed", "error": last_error, "attempts": max_retries}
