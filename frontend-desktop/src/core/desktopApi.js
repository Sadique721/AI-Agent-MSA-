/**
 * desktopApi.js
 * Tauri v2 native system APIs with automatic browser fallback simulation.
 */
let tauriApi = null;

try {
  if (window.__TAURI_INTERNALS__) {
    tauriApi = import('@tauri-apps/api');
  }
} catch (e) {
  console.warn("Not running in Tauri shell. Enabling browser mock mode.");
}

export async function getActiveWindowTitle() {
  if (tauriApi) {
    try {
      const { invoke } = await tauriApi;
      return await invoke("get_active_window_title");
    } catch (e) {
      return "Tauri Host App Window";
    }
  }
  return "Google Chrome (Simulation)";
}

export async function readClipboardText() {
  if (tauriApi) {
    try {
      const { clipboard } = await tauriApi;
      return await clipboard.readText();
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
  if (tauriApi) {
    try {
      const { clipboard } = await tauriApi;
      await clipboard.writeText(text);
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
