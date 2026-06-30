"""
backend/shared/event_bus.py
============================
Lightweight Event Bus for MSA AI Agent V5.0.
Integrates Kafka (confluent-kafka) when enable_kafka is True in features.yaml.
Falls back transparently to an in-process asyncio.Queue queue when offline.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional
from backend.shared.config_loader import ConfigLoader

logger = logging.getLogger("msa.event_bus")


class EventBus:
    """Decoupled asynchronous event broker."""

    def __init__(self) -> None:
        self._cfg = ConfigLoader.get_instance()
        self._enable_kafka = self._cfg.feature("enable_kafka")
        self._kafka_producer = None
        self._subscribers: Dict[str, List[Callable]] = {}
        self._local_queue: Optional[asyncio.Queue] = None

        if self._enable_kafka:
            self._init_kafka()
        else:
            self._local_queue = asyncio.Queue()
            logger.info("Kafka event bus is disabled — falling back to local queue")

    def _init_kafka(self) -> None:
        try:
            from confluent_kafka import Producer  # type: ignore
            bootstrap = self._cfg.get("kafka.bootstrap_servers", "localhost:9092")
            self._kafka_producer = Producer({"bootstrap.servers": bootstrap})
            logger.info("Kafka producer initialized: %s", bootstrap)
        except ImportError:
            logger.warning("confluent-kafka not installed — falling back to local queue")
            self._enable_kafka = False
            self._local_queue = asyncio.Queue()
        except Exception as e:
            logger.warning("Kafka initialization failed (%s) — falling back to local queue", e)
            self._enable_kafka = False
            self._local_queue = asyncio.Queue()

    async def publish(self, topic: str, event: Dict[str, Any]) -> None:
        """Publish an event to a topic (asynchronously)."""
        logger.debug("Publishing to %s: %s", topic, list(event.keys()))

        if self._enable_kafka and self._kafka_producer:
            import json
            try:
                self._kafka_producer.produce(
                    topic,
                    json.dumps(event).encode("utf-8"),
                    callback=lambda err, msg: logger.debug("Kafka delivered: %s", msg) if err is None else logger.warning("Kafka delivery failed: %s", err)
                )
                self._kafka_producer.poll(0)
            except Exception as e:
                logger.warning("Failed to publish to Kafka: %s", e)
        
        # Always trigger local listeners
        if topic in self._subscribers:
            for cb in self._subscribers[topic]:
                try:
                    if asyncio.iscoroutinefunction(cb):
                        asyncio.create_task(cb(event))
                    else:
                        cb(event)
                except Exception as e:
                    logger.warning("Subscriber callback failed for topic %s: %s", topic, e)

        # Enqueue locally
        if self._local_queue:
            await self._local_queue.put({"topic": topic, "event": event})

    def subscribe(self, topic: str, callback: Callable) -> None:
        """Subscribe a handler to a topic."""
        self._subscribers.setdefault(topic, []).append(callback)
        logger.debug("Subscribed listener to topic: %s", topic)

    def unsubscribe(self, topic: str, callback: Callable) -> None:
        if topic in self._subscribers and callback in self._subscribers[topic]:
            self._subscribers[topic].remove(callback)
            logger.debug("Unsubscribed listener from topic: %s", topic)


# ── SingletonAccessor ─────────────────────────────────────────────────────────
_event_bus: Optional[EventBus] = None

def get_event_bus() -> EventBus:
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus
