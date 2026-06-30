import queue
import logging
import threading
from typing import Dict, List, Callable, Any, Optional

logger = logging.getLogger("msa.infrastructure.event_bus")

class Event:
    """Base class for all system-wide telemetry and multi-agent events."""
    def __init__(self, topic: str, data: Any):
        self.topic = topic
        self.data = data

class EventBus:
    """Centralized high-performance async Event Bus."""
    _instance: Optional['EventBus'] = None

    def __new__(cls) -> 'EventBus':
        if cls._instance is None:
            cls._instance = super(EventBus, cls).__new__(cls)
            cls._instance._subscribers = {}
            cls._instance._queue = queue.Queue()
            cls._instance._running = False
            cls._instance._thread = None
        return cls._instance

    def subscribe(self, topic: str, callback: Callable[[Event], None]) -> None:
        """Subscribes a callback function to an event topic."""
        if topic not in self._subscribers:
            self._subscribers[topic] = []
        self._subscribers[topic].append(callback)
        logger.debug("Subscribed callback to topic: %s", topic)

    def unsubscribe(self, topic: str, callback: Callable[[Event], None]) -> None:
        """Unsubscribes a callback function from an event topic."""
        if topic in self._subscribers:
            try:
                self._subscribers[topic].remove(callback)
                logger.debug("Unsubscribed callback from topic: %s", topic)
            except ValueError:
                pass

    def publish(self, topic: str, data: Any) -> None:
        """Publishes an event to the queue for asynchronous dispatch."""
        event = Event(topic, data)
        self._queue.put(event)

    def start(self) -> None:
        """Starts the background event processing thread."""
        if not self._running:
            self._running = True
            self._thread = threading.Thread(target=self._process_queue, daemon=True)
            self._thread.start()
            logger.info("Asynchronous EventBus started.")

    def stop(self) -> None:
        """Stops the background event processing thread."""
        if self._running:
            self._running = False
            self._queue.put(None)  # Wake up queue join
            if self._thread:
                self._thread.join(timeout=2.0)
            logger.info("Asynchronous EventBus stopped.")

    def _process_queue(self) -> None:
        """Background worker loop dispatching events from queue."""
        while self._running:
            try:
                event = self._queue.get(timeout=0.5)
                if event is None:
                    break
                
                # Dispatch event to topic subscribers
                callbacks = self._subscribers.get(event.topic, [])
                # Also dispatch to wildcard '*' subscribers
                callbacks_wildcard = self._subscribers.get("*", [])
                
                for cb in callbacks + callbacks_wildcard:
                    try:
                        cb(event)
                    except Exception as e:
                        logger.error("Error executing callback on event topic %s: %s", event.topic, e)
                
                self._queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logger.error("EventBus loop error: %s", e)
