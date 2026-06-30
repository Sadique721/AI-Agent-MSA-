# Electron Desktop Overlay Specification — MSA V5.0

This document defines the spatial client configuration and key listeners in MSA V5.0.

---

## 1. Window Transparency & Frame

The Electron client shell is configured to support an overlay window:
```javascript
mainWindow = new BrowserWindow({
  width: 1200,
  height: 800,
  transparent: true,
  frame: false,
  webPreferences: {
    nodeIntegration: true,
    contextIsolation: false
  }
});
```

---

## 2. Global hotkeys & System Tray

- **Global toggle:** The global hotkey `Ctrl+K` toggles window visibility instantly.
- **Close Action:** Clicking the window close button hides the window to the System Tray instead of quitting the application.
- **IPC Clipboard Bridges:** Exposes clipboard read and write calls to the React frontend.
