# Memory Engine — MSA AI Agent V4.5

Details the memory hierarchy, SQLite integration, and cryptographic protection policies.

## Storage Hierarchy

- **Working Memory**: In-memory dict stores volatile active variables (GPS, active tool states).
- **Short-Term Memory**: Decrypted conversation history.
- **Long-Term Memory**: Encrypted SQLite tables containing full historically-indexed queries.
- **Task Memory**: Plan logs and validator ratings.
