import os
import json
import pytest

def test_desktop_client_configuration():
    """Verify that Tauri and npm configs are correctly structured and exist."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    desktop_dir = os.path.join(base_dir, "frontend-desktop")
    
    # Check package.json
    package_json_path = os.path.join(desktop_dir, "package.json")
    assert os.path.exists(package_json_path) is True
    
    with open(package_json_path, "r", encoding="utf-8") as f:
        pkg = json.load(f)
        assert pkg["name"] == "msa-agent-desktop-client"
        assert "zustand" in pkg["dependencies"]
        assert "framer-motion" in pkg["dependencies"]

    # Check tauri.conf.json
    tauri_conf_path = os.path.join(desktop_dir, "tauri.conf.json")
    assert os.path.exists(tauri_conf_path) is True
    
    with open(tauri_conf_path, "r", encoding="utf-8") as f:
        tauri_conf = json.load(f)
        assert "app" in tauri_conf
        assert tauri_conf["bundle"]["identifier"] == "com.msa.agent.client"
        
        # Check window transparency is enabled for glassmorphism
        windows = tauri_conf["app"]["windows"]
        assert len(windows) > 0
        assert windows[0]["transparent"] is True

def test_desktop_src_layout():
    """Verify that React component and core state modules exist in the directory structure."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    src_dir = os.path.join(base_dir, "frontend-desktop", "src")
    
    required_files = [
        os.path.join(src_dir, "App.jsx"),
        os.path.join(src_dir, "main.jsx"),
        os.path.join(src_dir, "index.css"),
        os.path.join(src_dir, "core", "apiClient.js"),
        os.path.join(src_dir, "core", "stateStore.js"),
        os.path.join(src_dir, "core", "desktopApi.js"),
        os.path.join(src_dir, "components", "ui", "FloatingInputBar.jsx"),
        os.path.join(src_dir, "components", "ui", "SpatialCanvas.jsx"),
        os.path.join(src_dir, "components", "ui", "ChatCard.jsx"),
        os.path.join(src_dir, "components", "ui", "AgentConstellation.jsx"),
        os.path.join(src_dir, "components", "assets", "agent-avatars.js")
    ]
    
    for filepath in required_files:
        assert os.path.exists(filepath) is True, f"Missing file: {filepath}"
