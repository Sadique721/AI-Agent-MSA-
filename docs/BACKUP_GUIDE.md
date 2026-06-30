# Backup & Restore Guide — MSA V5.0

This guide explains how to manage periodic automated backups and perform system restores in MSA AI Agent V5.0.

---

## 1. Automated Backups

The `BackupAgent` is one of the 9 background threads scheduled to run every 12 hours. It archives:
- Conversation history databases (`data/memory/`)
- User configuration files (`config/`)
- Agent prompt templates (`prompts/`)

ZIP archives are stored under `data/backups/`.

---

## 2. CLI Restore Operations

To restore your agent configurations or chat databases:

```bash
# Retrieve a list of saved backup ZIP files
curl -X GET http://localhost:8000/api/v5/backups

# Trigger restore of a specific archive
curl -X POST http://localhost:8000/api/v5/restore -H "Content-Type: application/json" -d '{"filename": "msa_backup_20260630_120000.zip"}'
```
> [!CAUTION]
> Restoring a backup replaces your active database and settings files immediately. Create a manual copy before running.
