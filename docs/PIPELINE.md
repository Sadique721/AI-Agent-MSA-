# LangGraph Execution Pipeline — MSA V5.0

This document describes the compilation and execution characteristics of the LangGraph StateGraph pipeline.

---

## 1. Graph State Definition

The execution state is tracked within `AgentState` typed dictionaries:
```python
class AgentState(TypedDict):
    user_input: str
    intent: str
    memory_context: str
    rag_context: str
    tool_summary: str
    llm_response: str
    response: str
```

---

## 2. Dynamic Routing Nodes

Nodes are executed sequentially within a directed acyclic graph compiled by the workflow loader:
```python
graph.add_node("intent_detection", node_intent_detection)
graph.add_node("memory_recall", node_memory_recall)
...
graph.add_edge("intent_detection", "memory_recall")
```

If any step raises an unhandled exception, it is caught at the coordinator level, saving the exception to the state `error` field and terminating the flow gracefully.
