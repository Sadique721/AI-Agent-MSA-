# Prompt Builder Specification — MSA AI Agent V4.5

Details the strict system prompt structures and dialogue-turn formatting logic.

## Section Templates

- **SYSTEM**: Establishes behavior policies and conversational constraints.
- **CONTEXT**: Injects owner profile parameters.
- **KNOWLEDGE**: Appends RAG vectors, SQLite sparse chunks, and graph context.
- **HISTORY**: Formats conversational turns cleanly:
  ```plaintext
  User: <command>
  Assistant: <response>
  ```
- **QUERY**: User's latest input.
- **RESPONSE**: Output anchor.
