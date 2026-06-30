# Event Bus Architecture — MSA V5.0

This document outlines the design and configuration of the Event Bus in MSA AI Agent V5.0.

---

## 1. Overview

The Event Bus acts as a decoupled message pass-through between LangGraph workflow nodes, background Celery/threading workers, and the desktop websocket client.

```
[Agent Node] ──► (Publish Event) ──► [Event Bus] ──► (Trigger Subscribed Callback) ──► [Worker]
```

---

## 2. Dynamic Backends

To support both enterprise production scale and zero-dependency local developer environments, the Event Bus supports a feature-flagged backend architecture:

1. **Kafka Backend (`confluent-kafka`):** Enabled when `enable_kafka: true` in `config/features.yaml`. Used for durable, scale-out message queues.
2. **Local Asyncio Queue Backend:** Default fallback when Kafka is offline or disabled. Messages are routed in-memory within the Python process.

---

## 3. Usage Example

### Publishing Events
```python
import asyncio
from backend.shared.event_bus import get_event_bus

async def publish_status():
    eb = get_event_bus()
    await eb.publish("agent-events", {
        "node": "intent_detection",
        "status": "completed",
        "payload": {"intent": "CODING"}
    })
```

### Subscribing to Topics
```python
from backend.shared.event_bus import get_event_bus

def handle_agent_event(event):
    print(f"Agent finished node {event['node']} with status {event['status']}")

eb = get_event_bus()
eb.subscribe("agent-events", handle_agent_event)
```
 obituary
