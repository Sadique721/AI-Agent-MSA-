<!--
███╗   ███╗███████╗ █████╗ 
████╗ ████║██╔════╝██╔══██╗
██╔████╔██║███████╗███████║
██║╚██╔╝██║╚════██║██╔══██║
██║ ╚═╝ ██║███████║██║  ██║
╚═╝     ╚═╝╚══════╝╚═╝  ╚═╝
-->

# 🚀✨ MSA – Ultimate Offline AI Agent ✨🚀

> **⚡ Your Personal AI — Fully Offline, Private, Powerful, Autonomous**

[![Offline First](https://img.shields.io/badge/🌍-Offline%20First-brightgreen?style=for-the-badge)](https://github.com/Sadique721/AI-Agent-MSA-)
[![Privacy Guaranteed](https://img.shields.io/badge/🔒-Privacy%20Guaranteed-blue?style=for-the-badge)](https://github.com/Sadique721/AI-Agent-MSA-)
[![Python 3.14+](https://img.shields.io/badge/Python-3.14%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Kotlin Android](https://img.shields.io/badge/Kotlin-Android-007ACC?style=for-the-badge&logo=kotlin&logoColor=white)](https://kotlinlang.org)

<p align="center">
  <i>No cloud. No API. No tracking. 👉 Just pure private AI power.</i><br>
  <b>Say "Hey MSA" 🎤 …and your intelligent assistant comes alive 🔥</b>
</p>

---

## 📖 Table of Contents

1. [🌟 What is MSA?](#-what-is-msa)
2. [🔥 Core Features](#-core-features)
3. [🧠 Technology Stack](#-technology-stack)
4. [📁 Project Structure](#-project-structure)
5. [⚙️ Installation Guide](#️-installation-guide)
6. [🔐 Voice Training](#-voice-training)
7. [💻 Coding Agent (Phase 3 Upgrade)](#-coding-agent-phase-3-upgrade)
8. [🚀 Running MSA](#-running-msa)
9. [🧪 Unit Testing & Validation](#-unit-testing--validation)
10. [📱 Android APK & Emulator Connection](#-android-apk--emulator-connection)
11. [🌈 Why MSA is Special](#-why-msa-is-special)

---

## 🌟 What is MSA?

**MSA** is a next‑generation **offline AI assistant and Software Engineering Agent** that runs locally on your machine and seamlessly controls your mobile device over Wi‑Fi.

> [!IMPORTANT]
> **100% local execution**: Vosk/Whisper.cpp, Llama-2 (GGUF), FAISS vector indexing, and OpenCV vision models run locally on your CPU/GPU. No data ever leaves your computer.

---

## 🔥 Core Features

| Category | Feature | Description |
|----------|---------|-------------|
| 🎙️ **Voice Intelligence** | Offline Speech Recognition | Vosk / Whisper.cpp – speech‑to‑text without internet |
| | Speaker Verification | Custom embeddings + Siamese network: only **your** voice activates MSA |
| | Bilingual Support | Naturally handles Hindi & Hinglish commands |
| 🧠 **Local Memory** | RAG Memory System | FAISS vector database + SQLite storage for long‑term facts and context |
| | Conversation logs | Encrypted local chat history database |
| 📱 **Mobile Control** | Android ADB Integration | Control Android over Wi‑Fi: open apps, capture input, take screenshots |
| | Unified control plane | Synchronized backend state between computer and Android client |
| 👁️ **Computer Vision** | Object Detection | OpenCV + real‑time screen parsing and camera automation |
| 💻 **Coding Agent** | Autonomous Coding Engine | Generates production code, reviews logic, explains algorithms, and refactors legacy structures |
| | Stack Trace Analyzer | Pinpoints root causes and lists ranked fixes for Java, Node, Python exceptions |
| | Project Scaffolder | Generates complete Angular, React, Node, Spring Boot project templates |

---

## 🧠 Technology Stack

* **Backend core**: Python 3.14+ (Flask, Flask-SocketIO, gevent-websocket)
* **Local LLM**: Llama 2 / TinyLlama (GGUF via `llama-cpp-python`)
* **Vector Database**: FAISS (Facebook AI Similarity Search) + SQLite
* **Text Embeddings**: `sentence-transformers/all-MiniLM-L6-v2`
* **Voice recognition**: Vosk speech API / Whisper.cpp
* **Audio Capture**: PyAudio / PortAudio
* **Computer Vision**: OpenCV
* **Mobile Connection**: Android Debug Bridge (ADB) over TCP/IP
* **Android Client**: Native Kotlin App, Socket.IO Client, AppCompat, Retrofit

---

## 📁 Project Structure

```bash
msa_agent/
├── 📁 agent/                  # AI reasoning & planning agents
│   ├── ReasoningEngine.py     # Main logical coordinator
│   └── Planner.py             # Complex task decomposition engine
├── 📁 android_app/            # Android Kotlin native app codebase
│   └── 📁 app/src/main/
│       ├── 📁 java/com/msa/agent/   # Activities: MainActivity, CodeReviewActivity, etc.
│       └── 📁 res/layout/           # Dark-themed UI layouts
├── 📁 backend/                # Server core logic
│   └── server.py              # Flask-SocketIO REST & WS router (port 5000)
├── 📁 browser_agent/          # Browser automation and selenium controllers
├── 📁 coding/                 # 💻 Phase-3 Coding Agent System
│   ├── CodingAgent.py         # Main router and controller
│   ├── CodeGenerator.py       # REST API / Entity / Component boilerplate creator
│   ├── StackTraceAnalyzer.py  # Regex and LLM parser for exception traces
│   ├── BugAnalyzer.py         # Runtime logs & configurations verification
│   ├── CodeReviewer.py        # SOLID, DRY, naming, and architectural grader
│   ├── ProjectGenerator.py    # Multi-file scaffolding for Maven / React / Angular
│   ├── RefactorEngine.py      # Duplicate code remover & optimizer
│   ├── CodeExplainer.py       # Algorithmic flow explainer
│   ├── CodingMemory.py        # FAISS database gateway (remembering projects/fixes)
│   └── CodingValidator.py     # Compile check and import sanity validator
├── 📁 data/                   # Encrypted logs, conversation history, SQLite DB
├── 📁 memory/                 # Core RAG long‑term memory management
│   └── rag_memory.py          # SQLite + FAISS wrapper class
├── 📁 models/                 # AI model assets (GGUF, Vosk voice models)
├── 📁 tests/                  # 🧪 pytest comprehensive unit test suite
│   ├── test_coding_memory.py
│   ├── test_coding_validator.py
│   ├── test_stacktrace_analyzer.py
│   └── ... (19 total test suites)
├── 📄 main.py                 # Main backend orchestrator script
├── 📄 requirements.txt        # Backend dependencies
└── 📄 README.md               # User manual
```

---

## ⚙️ Installation Guide

### Prerequisites
1. **Python 3.14+** (make sure it's on your environment PATH)
2. **Android SDK & platform-tools** (requires `adb.exe` to run Android tasks)
3. **Gradle 9.1.0+** (included in the wrapper) and JDK 17+ (to compile the Android app)

### Step 1: Install Python Dependencies
```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### Step 2: Configure Local Models
Create a `models/` directory and place your local offline models inside:
- **Speech recognition**: Extract a Vosk model to `models/vosk/`
- **Large Language Model**: Put a `.gguf` file in `models/llm/` and verify the path matches in `config.py`.

---

## 🔐 Voice Training

To train the Speaker Verification Siamese network to identify your voice:
1. Run the enrollment script:
   ```bash
   python scripts/voice_enrollment.py
   ```
2. Speak the wakeword `"Hey MSA"` clearly.
3. The Siamese network generates and saves your unique voice embedding profile locally to verify and protect device commands.

---

## 💻 Coding Agent (Phase 3 Upgrade)

The Phase 3 upgrade introduces a fully local software engineering pipeline. The assistant automatically intercepts programming requests and routes them to dedicated subsystems.

### Core Endpoints

* **`POST /api/code/generate`**: Generates production-ready REST APIs, microservices, repositories, and controllers.
* **`POST /api/code/review`**: Analyzes code against SOLID, DRY, and security rules. Returns scores and comments.
* **`POST /api/code/project`**: Generates project structures for Angular, Spring Boot, React, and Node.js.
* **`POST /api/code/stacktrace`**: Parses Exception traces (Java, Python, JS) to find files, line numbers, and rank bugfixes.
* **`GET /api/code/history`**: Lists history logs of all projects, fixes, and reviews stored in the RAG memory database.

---

## 🚀 Running MSA

### 1. Launch the Backend Server
```bash
python main.py
```
*The server will start on `http://localhost:5000`.*

### 2. Boot up the Android Emulator
Make sure your emulator AVD matches your settings (e.g. `medium_phone`) and launch it with SwiftShader software rendering to bypass OpenGL issues:
```bash
"C:\Users\MD SADIQUE AMIN\AppData\Local\Android\Sdk\emulator\emulator.exe" -avd medium_phone -no-audio -no-boot-anim -gpu swiftshader_indirect
```

### 3. Install and Launch the Android App
```bash
# Compile the updated project and native activities
cd android_app
.\gradlew.bat assembleDebug

# Install on the active emulator
cd ..
adb install -r android_app\app\build\outputs\apk\debug\app-debug.apk

# Start the application launcher activity
adb shell am start -n com.msa.agent/.MainActivity
```

---

## 🧪 Unit Testing & Validation

Run the pytest suite to verify all logic systems are performing correctly:
```bash
python -m pytest
```

> [!TIP]
> This suite includes **419 automated test cases** checking the AST parser, coding validator compiler checks, refactor engines, RAG database storage, and LLM retry logics. Ensure you maintain 100% pass rates on modification.

---

## 📱 Android APK & Emulator Connection

The native Android app uses Retrofit and WebSocket libraries to establish a bidirectional sync socket connection with the host backend server.

> [!WARNING]
> Android Emulators route host server requests to the local IP loopback address **`10.0.2.2:5000`** instead of `127.0.0.1:5000`. This mapping is already configured in the Retrofit connections inside `CodeAgentClient.kt`.

### Built-in Native Activities
The Android application defines four native developer-focused activities that can be launched directly or accessed from the agent console:
* **`CodeReviewActivity`**: Paste your scripts and retrieve immediate structural feedback.
* **`StackTraceActivity`**: Paste error traces to get pinpointed line number locations and debug recommendations.
* **`ProjectGeneratorActivity`**: Configure project name and boilerplate languages (React, Node, Angular) to output complete workspace scaffolding.
* **`CodingHistoryActivity`**: Query the local SQLite database to display lists of all recently compiled scripts.

---

## 🌈 Why MSA is Special

1. **Zero-Latency Privacy**: No cloud processing. Even the voice models and sentence embeddings are loaded directly from local weights.
2. **Dynamic UI/UX**: Android activities use harmonized dark modes, crisp status badges, and animated layouts built for readability.
3. **Closed-Loop Engineering**: Generated code is automatically processed through `CodingValidator` compiling steps and import-scans before being served to the user interface.
