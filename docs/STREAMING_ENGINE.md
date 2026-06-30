# Streaming Engine — MSA AI Agent V4.5

Details token streaming, state payloads, and cursor animations.

## WebSocket Streaming Schema

- **Status Events**:
  ```json
  {"state": "thinking", "message": "Analyzing intent..."}
  ```
- **Token Events**:
  ```json
  {"token": "Hello"}
  ```
- **Completion Events**:
  ```json
  {"state": "completed"}
  ```
- **Cursor UI**: A pulsing vertical indigo block indicates active streaming.
