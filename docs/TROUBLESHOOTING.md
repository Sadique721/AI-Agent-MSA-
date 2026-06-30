# Troubleshooting — MSA V5.0

This guide lists common issues, diagnosis strategies, and resolution steps for MSA AI Agent V5.0.

---

## 1. LLM Generation Failures (Ollama connection error)

* **Symptom:** AI returns default offline simulation responses. Gateway logs show: `Connection refused on localhost:11434`.
* **Fix:** 
  1. Open a terminal and run `ollama serve`.
  2. Pull the default V5 model: `ollama pull llama3.2:3b`.
  3. Verify availability by visiting `http://localhost:11434` in your browser.

---

## 2. Port Collisions (Port 5000 or 8000 already in use)

* **Symptom:** FastAPI or Flask startup crashes with `OSError: [Errno 98] Address already in use`.
* **Fix:** 
  - To locate conflicting processes on Windows:
    ```cmd
    netstat -ano | findstr 8000
    taskkill /F /PID <PID>
    ```
  - Or modify default ports inside `config/development.yaml`.
