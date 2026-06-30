# Deployment & Production — MSA V5.0

This guide explains how to package, deploy, and scale MSA AI Agent V5.0 services in production.

---

## 1. Local Production Launch

To build the optimized static assets and launch the dual-server environment locally:

```bash
# Build React static assets
cd frontend-desktop
npm run build

# Start both Flask (port 5000) and FastAPI (port 8000) gateways
cd ..
set MSA_ENV=production
.venv\Scripts\python.exe main.py
```

---

## 2. Docker Deployment

To package the agent gateway inside a Docker container:

```bash
docker build -t msa-agent:v5 .
docker run -d -p 5000:5000 -p 8000:8000 --env-file .env msa-agent:v5
```
Ensure your environment file contains database connections and cloud provider model API keys.
