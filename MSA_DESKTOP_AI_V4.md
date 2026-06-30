# 🚀 MSA DESKTOP AI V4 — NATIVE WINDOWS CLIENT BUILDER SPECIFICATION

This master engineering prompt documents the exact packaging pipeline, scripts, and commands required to bundle the **MSA AI Agent Desktop Client** into a native Windows executable (`.exe` installer) using Electron and `electron-builder`.

---

## 📦 BUILD PIPELINE ARCHITECTURE

```
[React 19 Source Code]
        │
        ▼  (npm run build)
[Vite Frontend Bundle (dist/)]
        │
        ▼  (electron-builder)
[MSA Agent Desktop.exe Installer (dist-electron/)]
```

---

## 🛠️ STEP-BY-STEP PACKAGING INSTRUCTIONS

### Step 1: Install Node.js & Workspace Setup
Ensure you have Node.js (v18+) installed. Navigate to the desktop client directory:
```bash
cd "d:/My Self Details/Programs/AI/msa_agent/frontend-desktop"
```

### Step 2: Install Development Dependencies
Install all required UI engines, Electron, and packaging scripts:
```bash
npm install
```

### Step 3: Compile React Assets
Build and optimize React, Tailwind v4, and Zustand client states:
```bash
npm run build
```

### Step 4: Run Desktop App in Development Mode
Test the live transparent glassmorphic window client locally:
```bash
npm start
```

### Step 5: Packaging Standalone Windows Installer (.exe)
Package the entire application into a standalone Windows installer (`.exe`) file:
```bash
npm run dist
```
*   The compiled `.exe` file will be generated in:
    `d:/My Self Details/Programs/AI/msa_agent/frontend-desktop/dist-electron/`

---

## 💎 PREMIUM CORE FEATURES

1.  **Frameless Transparent Layout**: Uses Windows composition filters to create a floating overlay.
2.  **Global Command Palette**: Press `Ctrl+K` or `Cmd+K` anywhere on Windows to focus the assistant immediately.
3.  **Active Focus Context**: Reads the active window title dynamically to provide situational context.
4.  **Infinite Panning Canvas**: Pan and zoom around an infinite cosmic coordinate space.
5.  **Multi-Agent Health Indicators**: Displays active pulse rings showing tool status for Coder, Planner, and Researcher agents.
