/**
 * desktopApi.js
 * Electron native system APIs with browser fallback simulation.
 */
let ipcRenderer = null;
let clipboard = null;

try {
  if (window.require) {
    const electron = window.require('electron');
    ipcRenderer = electron.ipcRenderer;
    clipboard = electron.clipboard;
  }
} catch (e) {
  console.warn("Not running in Electron shell. Enabling browser mock mode.");
}

export async function getActiveWindowTitle() {
  if (ipcRenderer) {
    try {
      // In Electron, we can request the main process to fetch active window or return window title
      return document.title || "MSA Agent Desktop Client";
    } catch (e) {
      return "MSA Agent Desktop Client";
    }
  }
  return "MSA Agent Client (Simulation)";
}

export async function readClipboardText() {
  if (clipboard) {
    try {
      return clipboard.readText();
    } catch (e) {
      return "";
    }
  }
  try {
    return await navigator.clipboard.readText();
  } catch (e) {
    return "Mock clipboard content (permission required in browser)";
  }
}

export async function writeClipboardText(text) {
  if (clipboard) {
    try {
      clipboard.writeText(text);
      return true;
    } catch (e) {
      return false;
    }
  }
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch (e) {
    return false;
  }
}
