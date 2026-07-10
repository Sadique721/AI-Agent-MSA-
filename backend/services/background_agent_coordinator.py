"""
backend/services/background_agent_coordinator.py
==================================================
Coordinating loop managing all 9 background agents in lightweight threads:
  1. IndexerAgent
  2. WatcherAgent
  3. SyncAgent
  4. SchedulerAgent
  5. UpdateCheckerAgent
  6. MemoryCleanerAgent
  7. KnowledgeUpdaterAgent
  8. AnalyticsAgent
  9. BackupAgent
"""
from __future__ import annotations

import asyncio
import logging
import threading
import time
from typing import Dict, List, Optional
from backend.shared.config_loader import ConfigLoader

logger = logging.getLogger("msa.background.coordinator")


class BackgroundAgentCoordinator:
    """Manages periodic execution of background intelligence agents."""

    def __init__(self) -> None:
        self._cfg = ConfigLoader.get_instance()
        self._running = False
        self._threads: List[threading.Thread] = []

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        logger.info("Initializing 9 background agents...")

        # Setup daemon threads for periodic tasks
        agents = [
            ("IndexerAgent", self._run_indexer, 300),          # Scan FS every 5 mins
            ("WatcherAgent", self._run_watcher, 1),             # Fast fs events watcher
            ("SyncAgent", self._run_sync, 600),                 # Sync external RAG sources
            ("SchedulerAgent", self._run_scheduler, 10),        # Scheduled crons
            ("UpdateCheckerAgent", self._run_update_checker, 86400), # Once a day
            ("MemoryCleanerAgent", self._run_memory_cleaner, 3600),  # Every hour
            ("KnowledgeUpdaterAgent", self._run_knowledge_updater, 120), # Every 2 mins
            ("AnalyticsAgent", self._run_analytics, 60),        # Export telemetry
            ("BackupAgent", self._run_backup, 43200),           # Backups every 12 hours
            ("SummarizerAgent", self._run_summarizer, 300),     # Summarize conversation every 5 mins
            
            # V7-V9: Career intelligence background agents
            ("JobDiscoveryAgent", self._run_job_discovery, 3600), # Scan job portals hourly
            ("OutreachFollowupAgent", self._run_outreach_followups, 14400), # Recruiter followups every 4 hours
            ("CareerAnalyticsAgent", self._run_career_analytics, 86400), # Generate metrics summary daily
        ]

        for name, target, interval in agents:
            t = threading.Thread(
                target=self._agent_loop,
                args=(name, target, interval),
                name=f"msa-bg-{name.lower()}",
                daemon=True,
            )
            t.start()
            self._threads.append(t)

        logger.info("All background agents started.")

    def stop(self) -> None:
        self._running = False
        logger.info("Stopping background agents...")

    def _agent_loop(self, name: str, task_fn: callable, interval: int) -> None:
        logger.debug("Background agent %s loop started.", name)
        while self._running:
            try:
                task_fn()
            except Exception as e:
                logger.error("Background agent %s error: %s", name, e)
            
            # Sleep in small increments to check for shutdown
            elapsed = 0
            while elapsed < interval and self._running:
                time.sleep(1)
                elapsed += 1

    # ── Background Agent Core Implementations ─────────────────────────────────
    def _run_indexer(self) -> None:
        logger.debug("[IndexerAgent] Scanning workspace files...")
        # Placeholder for directory indexing

    def _run_watcher(self) -> None:
        # Debounced watcher logic
        pass

    def _run_sync(self) -> None:
        logger.debug("[SyncAgent] Syncing external knowledge base...")

    def _run_scheduler(self) -> None:
        # Check task schedule queue
        pass

    def _run_update_checker(self) -> None:
        logger.info("[UpdateCheckerAgent] Checking for updates...")
        try:
            from backend.auto_update.update_service import get_update_service
            service = get_update_service()
            info = service.check_for_updates()
            if info["has_update"]:
                logger.info("A new update is available: %s", info["latest_version"])
        except Exception as e:
            logger.debug("Update checker run failed: %s", e)

    def _run_memory_cleaner(self) -> None:
        logger.debug("[MemoryCleanerAgent] Pruning expired conversations...")

    def _run_knowledge_updater(self) -> None:
        logger.debug("[KnowledgeUpdaterAgent] Optimizing entity connections...")

    def _run_analytics(self) -> None:
        logger.debug("[AnalyticsAgent] Processing system metrics...")

    def _run_backup(self) -> None:
        logger.info("[BackupAgent] Creating scheduled ZIP backup...")
        try:
            from backend.backup.backup_service import get_backup_service
            service = get_backup_service()
            service.create_backup()
        except Exception as e:
            logger.error("Periodic backup failed: %s", e)

    def _run_summarizer(self) -> None:
        logger.debug("[SummarizerAgent] Running periodic conversation summarizer...")
        try:
            from ai_core.llm_manager import LLMManager
            from memory.rag_memory import RAGMemory
            from memory.conversation_summarizer import ConversationSummarizer
            
            rag = RAGMemory(sqlite_memory=None)
            llm = LLMManager()
            
            if rag.sqlite:
                context = rag.sqlite.get_recent_context(limit=30)
                if len(context) >= 20:
                    history = []
                    for turn in context:
                        history.append({"role": "user", "content": turn.get("user", "")})
                        history.append({"role": "assistant", "content": turn.get("assistant", "")})
                        
                    summarizer = ConversationSummarizer(llm, rag)
                    summarizer.maybe_summarize(conversation_id="default_main_session", history=history)
        except Exception as e:
            logger.error("SummarizerAgent execution failed: %s", e)

    def _run_job_discovery(self) -> None:
        """Periodic background job discovery scan."""
        logger.info("[JobDiscoveryAgent] Scanning job portals...")
        try:
            from career.job_discovery import JobDiscoveryEngine
            from config import JOB_SEARCH_DEFAULT_QUERY
            discovery = JobDiscoveryEngine()
            # Perform a default background scrape
            jobs = discovery.aggregate(JOB_SEARCH_DEFAULT_QUERY, max_per_source=5)
            logger.info("[JobDiscoveryAgent] Found and cached %d job opportunities", len(jobs))
        except Exception as e:
            logger.error("[JobDiscoveryAgent] Scrape failed: %s", e)

    def _run_outreach_followups(self) -> None:
        """Check CRM for follow-up reminders."""
        logger.debug("[OutreachFollowupAgent] Checking follow-up queue...")
        try:
            from career.recruiter_crm import RecruiterCRM
            crm = RecruiterCRM()
            followups = crm.get_pending_followups()
            if followups:
                logger.info("[OutreachFollowupAgent] %d pending recruiter follow-ups found!", len(followups))
                # Emit socket notification to desktop client
                from backend.server import socketio
                socketio.emit("outreach_followup_reminder", {"count": len(followups), "list": followups})
        except Exception as e:
            logger.debug("OutreachFollowupAgent run failed: %s", e)

    def _run_career_analytics(self) -> None:
        """Compile and save daily metrics report."""
        logger.info("[CareerAnalyticsAgent] Compiling metrics reports...")
        try:
            from career.analytics import CareerAnalytics
            analytics = CareerAnalytics()
            report_path = analytics.save_report_to_disk(days=7)
            logger.info("[CareerAnalyticsAgent] Report saved successfully: %s", report_path)
        except Exception as e:
            logger.error("CareerAnalyticsAgent failed: %s", e)


# ── SingletonAccessor ─────────────────────────────────────────────────────────
_coordinator: Optional[BackgroundAgentCoordinator] = None

def get_background_coordinator() -> BackgroundAgentCoordinator:
    global _coordinator
    if _coordinator is None:
        _coordinator = BackgroundAgentCoordinator()
    return _coordinator
