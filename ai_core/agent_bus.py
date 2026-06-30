import queue
import logging
import threading
from typing import Dict, List, Any, Callable

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("msa.ai.bus")

class BlackboardMessage:
    def __init__(self, sender: str, key: str, value: Any):
        self.sender = sender
        self.key = key
        self.value = value

class AgentCommunicationBus:
    """Distributed Agent Communication Bus mapping events, Pub/Sub, and Blackboard memory."""
    def __init__(self):
        self.subscribers: Dict[str, List[Callable]] = {}
        self.blackboard: Dict[str, BlackboardMessage] = {}
        self._lock = threading.Lock()
        self._queue = queue.Queue()
        self._running = False
        self._worker_thread = None

    def start(self) -> None:
        self._running = True
        self._worker_thread = threading.Thread(target=self._process_queue, daemon=True)
        self._worker_thread.start()
        logger.info("Agent Communication Bus started.")

    def stop(self) -> None:
        self._running = False
        self._queue.put(None)
        if self._worker_thread:
            self._worker_thread.join(timeout=1.0)
        logger.info("Agent Communication Bus stopped.")

    def subscribe(self, topic: str, handler: Callable[[Any], None]) -> None:
        with self._lock:
            if topic not in self.subscribers:
                self.subscribers[topic] = []
            self.subscribers[topic].append(handler)

    def publish(self, topic: str, data: Any) -> None:
        self._queue.put((topic, data))

    def write_blackboard(self, sender: str, key: str, value: Any) -> None:
        """Writes a piece of shared state to the central blackboard memory."""
        with self._lock:
            self.blackboard[key] = BlackboardMessage(sender, key, value)
            logger.info("Blackboard updated: [%s] -> %s (by %s)", key, str(value), sender)

    def read_blackboard(self, key: str) -> Any:
        """Reads from shared blackboard memory."""
        with self._lock:
            msg = self.blackboard.get(key)
            return msg.value if msg else None

    def _process_queue(self) -> None:
        while self._running:
            item = self._queue.get()
            if item is None:
                break
            topic, data = item
            
            # Retrieve handlers
            handlers = []
            with self._lock:
                if topic in self.subscribers:
                    handlers = list(self.subscribers[topic])
                if "*" in self.subscribers:
                    handlers.extend(self.subscribers["*"])
                    
            for handler in handlers:
                try:
                    handler(data)
                except Exception as e:
                    logger.error("Handler error on topic %s: %s", topic, e)
