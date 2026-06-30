"""
services/watcher.py
===================
FileSystem Auto Re-indexing Monitor.
Spawns background watchers to monitor local directories, triggering incremental indexing
on file changes, creations, and deletions using watchdog or native polling fallbacks.
"""

import os
import time
import threading
import logging
from typing import List, Callable, Optional, Dict

logger = logging.getLogger("msa.services.watcher")

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False


class WatcherService:
    """
    Background directory watcher service. Triggers callback on file modifications, creations, and deletions.
    """
    def __init__(self, watch_paths: List[str], change_callback: Callable[[str, str], None]):
        self.watch_paths = [os.path.abspath(p) for p in watch_paths]
        self.callback = change_callback
        self.is_running = False
        self._thread = None
        self._observer = None

    def start(self) -> None:
        """Starts background file monitor."""
        if self.is_running:
            return
        self.is_running = True
        logger.info("Starting WatcherService on paths: %s", self.watch_paths)
        
        if WATCHDOG_AVAILABLE:
            self._start_watchdog()
        else:
            self._start_polling()

    def stop(self) -> None:
        """Stops background file monitor."""
        self.is_running = False
        if self._observer:
            try:
                self._observer.stop()
                self._observer.join()
            except Exception:
                pass
        logger.info("WatcherService stopped.")

    def _start_watchdog(self) -> None:
        """Starts monitoring using watchdog library."""
        class _RAGHandler(FileSystemEventHandler):
            def __init__(self, callback: Callable[[str, str], None]):
                self.cb = callback

            def on_created(self, event):
                if not event.is_directory:
                    self.cb(event.src_path, "created")

            def on_modified(self, event):
                if not event.is_directory:
                    self.cb(event.src_path, "modified")

            def on_deleted(self, event):
                if not event.is_directory:
                    self.cb(event.src_path, "deleted")

        self._observer = Observer()
        handler = _RAGHandler(self.callback)
        for path in self.watch_paths:
            if os.path.exists(path):
                self._observer.schedule(handler, path, recursive=True)
        self._observer.start()

    def _start_polling(self) -> None:
        """Fallback polling thread that tracks files by checking modification timestamps."""
        self._thread = threading.Thread(target=self._polling_loop, daemon=True)
        self._thread.start()

    def _polling_loop(self) -> None:
        """Scans directories periodically to find added, modified, or deleted files."""
        # Map: filepath -> mtime
        file_state: Dict[str, float] = {}

        # Initial scan
        for path in self.watch_paths:
            if os.path.exists(path):
                if os.path.isfile(path):
                    file_state[path] = os.path.getmtime(path)
                else:
                    for root, _, files in os.walk(path):
                        for f in files:
                            fpath = os.path.join(root, f)
                            try:
                                file_state[fpath] = os.path.getmtime(fpath)
                            except Exception:
                                pass

        logger.info("Native File Poller initialized with %d files.", len(file_state))

        while self.is_running:
            time.sleep(10)  # Check every 10 seconds
            
            current_state: Dict[str, float] = {}
            # Re-scan paths
            for path in self.watch_paths:
                if os.path.exists(path):
                    if os.path.isfile(path):
                        try:
                            current_state[path] = os.path.getmtime(path)
                        except Exception:
                            pass
                    else:
                        for root, _, files in os.walk(path):
                            for f in files:
                                fpath = os.path.join(root, f)
                                try:
                                    current_state[fpath] = os.path.getmtime(fpath)
                                except Exception:
                                    pass

            # Detect modifications and creations
            for fpath, mtime in current_state.items():
                if fpath not in file_state:
                    logger.info("Watcher Poller: File created '%s'", fpath)
                    file_state[fpath] = mtime
                    self._trigger_callback_safe(fpath, "created")
                elif mtime > file_state[fpath]:
                    logger.info("Watcher Poller: File modified '%s'", fpath)
                    file_state[fpath] = mtime
                    self._trigger_callback_safe(fpath, "modified")

            # Detect deletions
            deleted_files = []
            for fpath in file_state:
                if fpath not in current_state:
                    logger.info("Watcher Poller: File deleted '%s'", fpath)
                    deleted_files.append(fpath)
                    self._trigger_callback_safe(fpath, "deleted")

            for fpath in deleted_files:
                file_state.pop(fpath, None)

    def _trigger_callback_safe(self, filepath: str, action: str) -> None:
        """Helper to invoke callback safely in a try-except block."""
        try:
            self.callback(filepath, action)
        except Exception as e:
            logger.error("Error invoking file watcher callback for '%s' (%s): %s", filepath, action, e)
