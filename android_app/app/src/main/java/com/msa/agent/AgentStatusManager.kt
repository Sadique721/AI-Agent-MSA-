package com.msa.agent

import android.webkit.JavascriptInterface
import android.webkit.WebView
import org.json.JSONObject
import java.util.concurrent.atomic.AtomicInteger

/**
 * AgentStatusManager.kt
 * =====================
 * Phase-2: Singleton that holds the current MSA Agent execution state
 * and exposes it to the WebView UI via a JavaScript bridge interface.
 *
 * States (in order):
 *   idle → reasoning → planning → executing → validating → complete | failed
 *
 * The WebView UI reads this via `window.MsaStatus.getStatus()` and
 * updates its Reasoning Status panel accordingly.
 */
object AgentStatusManager {

    // ── Agent state machine ────────────────────────────────────────────────────
    enum class AgentState {
        IDLE, REASONING, PLANNING, EXECUTING, VALIDATING, COMPLETE, FAILED, PENDING_APPROVAL
    }

    @Volatile var currentState:    AgentState = AgentState.IDLE
    @Volatile var currentGoal:     String     = ""
    @Volatile var currentStep:     Int        = 0
    @Volatile var totalSteps:      Int        = 0
    @Volatile var validationResult:String     = ""
    @Volatile var lastError:       String     = ""
    @Volatile var replanAttempt:   Int        = 0

    val taskProgress = AtomicInteger(0)   // 0–100

    // Attached WebView reference (weak-ish — cleared on destroy)
    private var webView: WebView? = null

    fun attachWebView(wv: WebView) { webView = wv }
    fun detachWebView()            { webView = null }

    // ── State transitions ──────────────────────────────────────────────────────

    fun setReasoning(goal: String) {
        currentState = AgentState.REASONING
        currentGoal  = goal
        currentStep  = 0
        taskProgress.set(10)
        notifyUI()
    }

    fun setPlanning(stepCount: Int) {
        currentState = AgentState.PLANNING
        totalSteps   = stepCount
        currentStep  = 0
        taskProgress.set(25)
        notifyUI()
    }

    fun setExecuting(stepIndex: Int, toolName: String) {
        currentState = AgentState.EXECUTING
        currentStep  = stepIndex
        val progress = if (totalSteps > 0) 25 + (stepIndex * 50 / totalSteps) else 50
        taskProgress.set(progress)
        notifyUI()
    }

    fun setValidating() {
        currentState = AgentState.VALIDATING
        taskProgress.set(85)
        notifyUI()
    }

    fun setComplete(validationSummary: String = "") {
        currentState     = AgentState.COMPLETE
        validationResult = validationSummary
        taskProgress.set(100)
        notifyUI()
        // Auto-reset to idle after 3s
        android.os.Handler(android.os.Looper.getMainLooper()).postDelayed({
            if (currentState == AgentState.COMPLETE) setIdle()
        }, 3000)
    }

    fun setFailed(error: String, attempt: Int = 0) {
        currentState   = AgentState.FAILED
        lastError      = error
        replanAttempt  = attempt
        taskProgress.set(0)
        notifyUI()
    }

    fun setPendingApproval(goal: String) {
        currentState = AgentState.PENDING_APPROVAL
        currentGoal  = goal
        taskProgress.set(0)
        notifyUI()
    }

    fun setIdle() {
        currentState     = AgentState.IDLE
        currentGoal      = ""
        currentStep      = 0
        totalSteps       = 0
        validationResult = ""
        lastError        = ""
        replanAttempt    = 0
        taskProgress.set(0)
        notifyUI()
    }

    // ── Status payload ────────────────────────────────────────────────────────

    fun getStatusJson(): JSONObject {
        return JSONObject().apply {
            put("state",             currentState.name)
            put("goal",              currentGoal)
            put("current_step",      currentStep)
            put("total_steps",       totalSteps)
            put("progress",          taskProgress.get())
            put("validation_result", validationResult)
            put("last_error",        lastError)
            put("replan_attempt",    replanAttempt)
        }
    }

    // ── JavaScript interface injected into WebView ────────────────────────────

    class MsaStatusBridge {

        @JavascriptInterface
        fun getStatus(): String = getStatusJson().toString()

        @JavascriptInterface
        fun getState(): String = currentState.name

        @JavascriptInterface
        fun getGoal(): String = currentGoal

        @JavascriptInterface
        fun getProgress(): Int = taskProgress.get()

        @JavascriptInterface
        fun isIdle(): Boolean = currentState == AgentState.IDLE
    }

    fun createJsBridge() = MsaStatusBridge()

    // ── Push status to WebView UI ─────────────────────────────────────────────

    private fun notifyUI() {
        val wv = webView ?: return
        val json = getStatusJson().toString()
            .replace("\\", "\\\\")
            .replace("'", "\\'")

        wv.post {
            wv.evaluateJavascript(
                "if(window.onMsaStatusUpdate) window.onMsaStatusUpdate('$json');",
                null
            )
        }
    }
}
