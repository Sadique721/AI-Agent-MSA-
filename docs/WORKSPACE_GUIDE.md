# Workspace & Project Guide — MSA V5.0

Workspaces isolate documents, vector spaces, and preferences per project.

---

## 1. Directory Namespaces

Every workspace has an isolated:
- Local database file namespace.
- RAG FAISS index subdirectory.
- Git repository watcher target folder.
- List of active Claude-style artifacts.

---

## 2. Command Line Workspace Operations

You can switch workspaces instantly using slash commands:
- `/workspace`: lists active and available workspaces.
- `/workspace frontend_app`: switches namespace to the frontend app.

---

## 3. Creating Workspaces Programmatically

You can instantiate a workspace using the `WorkspaceService`:

```python
from backend.workspace_manager.workspace_service import get_workspace_service

service = get_workspace_service()
# Automatically generates slug test_project
new_ws = service.create_workspace("Test Project", "/paths/to/project")
```
