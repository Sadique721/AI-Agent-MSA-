package com.msa.agent

import android.content.Context
import android.os.Handler
import android.os.Looper
import android.util.Log
import android.webkit.JavascriptInterface
import android.webkit.WebView
import org.json.JSONObject
import java.io.BufferedReader
import java.io.InputStreamReader
import java.io.OutputStreamWriter
import java.net.HttpURLConnection
import java.net.URL
import java.util.concurrent.Executors

/**
 * ReasoningClient.kt
 * ==================
 * Phase-2: HTTP client that bridges the Android APK with the MSA backend
 * ReasoningEngine. Uses built-in HttpURLConnection (no OkHttp dependency).
 *
 * Responsibilities:
 *   1. POST /mobile/capabilities — send device context on startup
 *   2. Poll GET /api/status every 30s → update AgentStatusManager
 *   3. POST /api/reason — send reasoning requests from JS bridge
 *   4. POST /mobile/status — periodic heartbeat
 *   5. GET /api/reasoning-status — check Phase-2 subsystems health
 */
class ReasoningClient(
    private val context: Context,
    private val serverUrl: String,
) {

    companion object {
        private const val TAG               = "MSA.ReasoningClient"
        private const val POLL_INTERVAL_MS  = 30_000L   // 30 seconds
        private const val CONNECT_TIMEOUT   = 8_000
        private const val READ_TIMEOUT      = 10_000
    }

    private val executor    = Executors.newFixedThreadPool(3)
    private val mainHandler = Handler(Looper.getMainLooper())
    private val dcm         = DeviceCapabilityManager(context)

    @Volatile private var pollingActive = false
    @Volatile private var webView: WebView? = null

    // ── Lifecycle ─────────────────────────────────────────────────────────────

    fun attachWebView(wv: WebView) { webView = wv }

    fun detachWebView()            { webView = null }

    fun start() {
        Log.i(TAG, "ReasoningClient starting — server: $serverUrl")
        // Send capabilities immediately
        executor.submit { sendCapabilities() }
        // Start status polling
        startPolling()
    }

    fun stop() {
        pollingActive = false
        executor.shutdown()
        Log.i(TAG, "ReasoningClient stopped.")
    }

    // ── 1. Send device capabilities ───────────────────────────────────────────

    fun sendCapabilities() {
        try {
            val payload = dcm.getCapabilities()
            val response = post("$serverUrl/mobile/capabilities", payload)
            Log.i(TAG, "Capabilities sent. Server: ${response?.optString("summary", "ok")}")
        } catch (e: Exception) {
            Log.e(TAG, "sendCapabilities failed: ${e.message}")
        }
    }

    // ── 2. Heartbeat + status polling ─────────────────────────────────────────

    private fun startPolling() {
        pollingActive = true
        executor.submit {
            while (pollingActive) {
                try {
                    pollAgentStatus()
                    sendHeartbeat()
                } catch (e: Exception) {
                    Log.w(TAG, "Poll error: ${e.message}")
                }
                Thread.sleep(POLL_INTERVAL_MS)
            }
        }
    }

    private fun pollAgentStatus() {
        try {
            val response = get("$serverUrl/api/reasoning-status") ?: return
            val phase2   = response.optJSONObject("phase2_subsystems") ?: return

            // Optionally push status to WebView
            val wv = webView ?: return
            val json = response.toString().replace("'", "\\'")
            mainHandler.post {
                wv.evaluateJavascript(
                    "if(window.onMsaServerStatus) window.onMsaServerStatus('$json');",
                    null
                )
            }
        } catch (e: Exception) {
            Log.w(TAG, "pollAgentStatus error: ${e.message}")
        }
    }

    private fun sendHeartbeat() {
        try {
            val payload = JSONObject().apply {
                put("event",    "heartbeat")
                put("battery",  dcm.getBatteryLevel())
                put("wifi",     dcm.isWifiConnected())
                put("charging", dcm.isCharging())
                put("device_id",dcm.getDeviceId())
            }
            post("$serverUrl/mobile/status", payload)
        } catch (e: Exception) {
            Log.w(TAG, "heartbeat failed: ${e.message}")
        }
    }

    // ── 3. Reason API call ─────────────────────────────────────────────────────

    fun reason(task: String, callback: (JSONObject?) -> Unit) {
        executor.submit {
            try {
                AgentStatusManager.setReasoning(task)
                val payload  = JSONObject().apply { put("task", task) }
                val response = post("$serverUrl/api/reason", payload)
                mainHandler.post { callback(response) }
            } catch (e: Exception) {
                Log.e(TAG, "reason() failed: ${e.message}")
                mainHandler.post { callback(null) }
            }
        }
    }

    // ── 4. Full Reason-Execute pipeline ───────────────────────────────────────

    fun reasonExecute(command: String, callback: (JSONObject?) -> Unit) {
        executor.submit {
            try {
                AgentStatusManager.setReasoning(command)
                val payload  = JSONObject().apply { put("command", command) }
                val response = post("$serverUrl/api/reason-execute", payload)

                if (response != null) {
                    val reasoning = response.optJSONObject("reasoning")
                    val goal = reasoning?.optString("goal", command) ?: command
                    AgentStatusManager.setComplete(response.optString("response", "Done"))
                }

                mainHandler.post { callback(response) }
            } catch (e: Exception) {
                Log.e(TAG, "reasonExecute() failed: ${e.message}")
                AgentStatusManager.setFailed(e.message ?: "unknown error")
                mainHandler.post { callback(null) }
            }
        }
    }

    // ── 5. Report task result ─────────────────────────────────────────────────

    fun reportTaskResult(taskId: String, result: String, success: Boolean) {
        executor.submit {
            try {
                val payload = JSONObject().apply {
                    put("task_id",   taskId)
                    put("result",    result)
                    put("success",   success)
                    put("device_id", dcm.getDeviceId())
                }
                post("$serverUrl/mobile/task-result", payload)
            } catch (e: Exception) {
                Log.e(TAG, "reportTaskResult failed: ${e.message}")
            }
        }
    }

    // ── JavaScript Interface (exposed to WebView) ─────────────────────────────

    inner class MsaJsBridge {

        @JavascriptInterface
        fun getServerUrl(): String = serverUrl

        @JavascriptInterface
        fun getDeviceStatus(): String {
            return JSONObject().apply {
                put("battery",          dcm.getBatteryLevel())
                put("wifi",             dcm.isWifiConnected())
                put("location_enabled", dcm.isLocationEnabled())
                put("agent_state",      AgentStatusManager.currentState.name)
                put("agent_goal",       AgentStatusManager.currentGoal)
                put("agent_progress",   AgentStatusManager.taskProgress.get())
            }.toString()
        }

        @JavascriptInterface
        fun sendCapabilities() {
            executor.submit { this@ReasoningClient.sendCapabilities() }
        }

        @JavascriptInterface
        fun notifyActionComplete(action: String, detail: String, taskId: String) {
            executor.submit {
                val vs = ValidationService(context, serverUrl)
                vs.validateAndReport(action, detail, taskId)
            }
        }

        @JavascriptInterface
        fun approveAction(confirmed: Boolean, goal: String) {
            Log.i(TAG, "User approval: $confirmed for goal: $goal")
            if (confirmed) {
                AgentStatusManager.setIdle()
            }
            // Notify WebView
            val wv = webView ?: return
            mainHandler.post {
                wv.evaluateJavascript(
                    "if(window.onApprovalResult) window.onApprovalResult($confirmed, '$goal');",
                    null
                )
            }
        }
    }

    fun createJsBridge() = MsaJsBridge()

    // ── HTTP helpers ──────────────────────────────────────────────────────────

    private fun post(endpoint: String, payload: JSONObject): JSONObject? {
        val url  = URL(endpoint)
        val conn = url.openConnection() as HttpURLConnection
        return try {
            conn.requestMethod = "POST"
            conn.doOutput      = true
            conn.connectTimeout = CONNECT_TIMEOUT
            conn.readTimeout    = READ_TIMEOUT
            conn.setRequestProperty("Content-Type", "application/json")
            conn.setRequestProperty("Accept", "application/json")

            OutputStreamWriter(conn.outputStream, Charsets.UTF_8).use {
                it.write(payload.toString())
            }

            val responseCode = conn.responseCode
            if (responseCode in 200..299) {
                val body = BufferedReader(InputStreamReader(conn.inputStream, Charsets.UTF_8))
                    .use { it.readText() }
                JSONObject(body)
            } else {
                Log.w(TAG, "POST $endpoint returned $responseCode")
                null
            }
        } catch (e: Exception) {
            Log.e(TAG, "POST $endpoint error: ${e.message}")
            null
        } finally {
            conn.disconnect()
        }
    }

    private fun get(endpoint: String): JSONObject? {
        val url  = URL(endpoint)
        val conn = url.openConnection() as HttpURLConnection
        return try {
            conn.requestMethod  = "GET"
            conn.connectTimeout = CONNECT_TIMEOUT
            conn.readTimeout    = READ_TIMEOUT
            conn.setRequestProperty("Accept", "application/json")

            val responseCode = conn.responseCode
            if (responseCode in 200..299) {
                val body = BufferedReader(InputStreamReader(conn.inputStream, Charsets.UTF_8))
                    .use { it.readText() }
                JSONObject(body)
            } else {
                null
            }
        } catch (e: Exception) {
            Log.w(TAG, "GET $endpoint error: ${e.message}")
            null
        } finally {
            conn.disconnect()
        }
    }
}
