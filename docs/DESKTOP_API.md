# Electron Desktop IPC API Reference — MSA V5.0

The Electron desktop frontend communicates with local Windows OS APIs via preload IPC bridges.

---

## 1. IPC Channels

The preload script exposes context bridge functions under `window.electronAPI`:

### `window.electronAPI.readClipboard()`
- **Description:** Returns current Windows OS clipboard text safely.
- **Implementation:** Handles string and multi-line buffer transfers.

### `window.electronAPI.writeClipboard(text)`
- **Description:** Replaces Windows OS clipboard contents with the provided text.

---

## 2. Global Shortcuts

- **Ctrl+K (Command+K on macOS):** Global shortcut to toggle the spatial overlay window.
  - Hides the application window to the Windows System Tray on close.
  - Automatically restores focus and triggers the text field input on toggle.
