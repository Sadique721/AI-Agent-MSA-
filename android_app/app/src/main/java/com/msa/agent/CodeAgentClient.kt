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
 * CodeAgentClient.kt
 * ==================
 * Phase-3: HTTP client that bridges the Android APK with the MSA backend
 * Coding Agent. Uses built-in HttpURLConnection (no OkHttp dependency).
 *
 * Responsibilities:
 *   1. submitCode     — POST /api/code/generate  (generate code from prompt)
 *   2. uploadLogs     — POST /api/code/debug      (analyze errors/logs)
 *   3. receiveFixes   — POST /api/code/refactor    (refactor source code)
 *   4. viewReviewReports — POST /api/code/review   (code quality review)
 *   5. generateProjects  — POST /api/code/project  (scaffold new projects)
 *   6. analyzeStackTraces — POST /api/code/stacktrace (parse stack traces)
 *   7. explainCode    — POST /api/code/explain     (line-by-line explanation)
 *   8. generateTests  — POST /api/code/test        (generate unit tests)
 *   9. getCodeHistory — GET  /api/code/history      (coding memory recall)
 */
class CodeAgentClient(
    private val context: Context,
    private val serverUrl: String,
) {

    companion object {
        private const val TAG             = "MSA.CodeAgentClient"
        private const val CONNECT_TIMEOUT = 10_000
        private const val READ_TIMEOUT    = 30_000
    }

    private val executor    = Executors.newFixedThreadPool(3)
    private val mainHandler = Handler(Looper.getMainLooper())

    @Volatile private var webView: WebView? = null

    // ── Lifecycle ─────────────────────────────────────────────────────────────

    fun attachWebView(wv: WebView) { webView = wv }

    fun detachWebView()            { webView = null }

    fun shutdown() {
        executor.shutdown()
        Log.i(TAG, "CodeAgentClient shut down.")
    }

    // ── 1. Submit Code (Generate) ─────────────────────────────────────────────

    /**
     * Generate source code from a natural language prompt.
     * Calls POST /api/code/generate with { "prompt": ..., "language": ... }.
     */
    fun submitCode(prompt: String, language: String? = null, callback: (JSONObject?) -> Unit) {
        executor.submit {
            try {
                val payload = JSONObject().apply {
                    put("prompt", prompt)
                    if (language != null) put("language", language)
                }
                val response = post("$serverUrl/api/code/generate", payload)
                Log.i(TAG, "submitCode response: ${response?.optString("status")}")
                mainHandler.post { callback(response) }
            } catch (e: Exception) {
                Log.e(TAG, "submitCode failed: ${e.message}")
                mainHandler.post { callback(null) }
            }
        }
    }

    // ── 2. Upload Logs (Debug) ────────────────────────────────────────────────

    /**
     * Send error logs or exception messages for analysis.
     * Calls POST /api/code/debug with { "logs": ... }.
     */
    fun uploadLogs(logs: String, callback: (JSONObject?) -> Unit) {
        executor.submit {
            try {
                val payload = JSONObject().apply {
                    put("logs", logs)
                }
                val response = post("$serverUrl/api/code/debug", payload)
                Log.i(TAG, "uploadLogs response: ${response?.optString("status")}")
                mainHandler.post { callback(response) }
            } catch (e: Exception) {
                Log.e(TAG, "uploadLogs failed: ${e.message}")
                mainHandler.post { callback(null) }
            }
        }
    }

    // ── 3. Receive Fixes (Refactor) ───────────────────────────────────────────

    /**
     * Submit source code for refactoring improvements.
     * Calls POST /api/code/refactor with { "code": ... }.
     */
    fun receiveFixes(code: String, callback: (JSONObject?) -> Unit) {
        executor.submit {
            try {
                val payload = JSONObject().apply {
                    put("code", code)
                }
                val response = post("$serverUrl/api/code/refactor", payload)
                Log.i(TAG, "receiveFixes response: ${response?.optString("status")}")
                mainHandler.post { callback(response) }
            } catch (e: Exception) {
                Log.e(TAG, "receiveFixes failed: ${e.message}")
                mainHandler.post { callback(null) }
            }
        }
    }

    // ── 4. View Review Reports ────────────────────────────────────────────────

    /**
     * Submit source code for quality review (security, SOLID, performance).
     * Calls POST /api/code/review with { "code": ... }.
     */
    fun viewReviewReports(code: String, callback: (JSONObject?) -> Unit) {
        executor.submit {
            try {
                val payload = JSONObject().apply {
                    put("code", code)
                }
                val response = post("$serverUrl/api/code/review", payload)
                Log.i(TAG, "viewReviewReports response: ${response?.optString("status")}")
                mainHandler.post { callback(response) }
            } catch (e: Exception) {
                Log.e(TAG, "viewReviewReports failed: ${e.message}")
                mainHandler.post { callback(null) }
            }
        }
    }

    // ── 5. Generate Projects ──────────────────────────────────────────────────

    /**
     * Generate boilerplate project structures.
     * Calls POST /api/code/project with { "project_type": ..., "name": ..., "description": ... }.
     */
    fun generateProjects(
        projectType: String,
        name: String,
        description: String = "",
        callback: (JSONObject?) -> Unit,
    ) {
        executor.submit {
            try {
                val payload = JSONObject().apply {
                    put("project_type", projectType)
                    put("name", name)
                    put("description", description)
                }
                val response = post("$serverUrl/api/code/project", payload)
                Log.i(TAG, "generateProjects response: ${response?.optString("status")}")
                mainHandler.post { callback(response) }
            } catch (e: Exception) {
                Log.e(TAG, "generateProjects failed: ${e.message}")
                mainHandler.post { callback(null) }
            }
        }
    }

    // ── 6. Analyze Stack Traces ───────────────────────────────────────────────

    /**
     * Parse and analyze stack traces to identify root cause.
     * Calls POST /api/code/stacktrace with { "trace": ... }.
     */
    fun analyzeStackTraces(trace: String, callback: (JSONObject?) -> Unit) {
        executor.submit {
            try {
                val payload = JSONObject().apply {
                    put("trace", trace)
                }
                val response = post("$serverUrl/api/code/stacktrace", payload)
                Log.i(TAG, "analyzeStackTraces response: ${response?.optString("status")}")
                mainHandler.post { callback(response) }
            } catch (e: Exception) {
                Log.e(TAG, "analyzeStackTraces failed: ${e.message}")
                mainHandler.post { callback(null) }
            }
        }
    }

    // ── 7. Explain Code ───────────────────────────────────────────────────────

    /**
     * Generate line-by-line explanations for source code.
     * Calls POST /api/code/explain with { "code": ... }.
     */
    fun explainCode(code: String, callback: (JSONObject?) -> Unit) {
        executor.submit {
            try {
                val payload = JSONObject().apply {
                    put("code", code)
                }
                val response = post("$serverUrl/api/code/explain", payload)
                Log.i(TAG, "explainCode response: ${response?.optString("status")}")
                mainHandler.post { callback(response) }
            } catch (e: Exception) {
                Log.e(TAG, "explainCode failed: ${e.message}")
                mainHandler.post { callback(null) }
            }
        }
    }

    // ── 8. Generate Tests ─────────────────────────────────────────────────────

    /**
     * Generate unit test suites for given source code.
     * Calls POST /api/code/test with { "code": ..., "framework": ... }.
     */
    fun generateTests(code: String, framework: String = "", callback: (JSONObject?) -> Unit) {
        executor.submit {
            try {
                val payload = JSONObject().apply {
                    put("code", code)
                    put("framework", framework)
                }
                val response = post("$serverUrl/api/code/test", payload)
                Log.i(TAG, "generateTests response: ${response?.optString("status")}")
                mainHandler.post { callback(response) }
            } catch (e: Exception) {
                Log.e(TAG, "generateTests failed: ${e.message}")
                mainHandler.post { callback(null) }
            }
        }
    }

    // ── 9. Get Code History ───────────────────────────────────────────────────

    /**
     * Retrieve coding-related memory events.
     * Calls GET /api/code/history?limit=...
     */
    fun getCodeHistory(limit: Int = 20, callback: (JSONObject?) -> Unit) {
        executor.submit {
            try {
                val response = get("$serverUrl/api/code/history?limit=$limit")
                Log.i(TAG, "getCodeHistory response: ${response?.optString("status")}")
                mainHandler.post { callback(response) }
            } catch (e: Exception) {
                Log.e(TAG, "getCodeHistory failed: ${e.message}")
                mainHandler.post { callback(null) }
            }
        }
    }

    // ── JavaScript Interface (exposed to WebView) ─────────────────────────────

    inner class CodeJsBridge {

        @JavascriptInterface
        fun getServerUrl(): String = serverUrl

        @JavascriptInterface
        fun submitCode(prompt: String, language: String) {
            this@CodeAgentClient.submitCode(prompt, language.ifEmpty { null }) { response ->
                pushToWebView("onCodeGenerated", response)
            }
        }

        @JavascriptInterface
        fun uploadLogs(logs: String) {
            this@CodeAgentClient.uploadLogs(logs) { response ->
                pushToWebView("onBugAnalyzed", response)
            }
        }

        @JavascriptInterface
        fun reviewCode(code: String) {
            this@CodeAgentClient.viewReviewReports(code) { response ->
                pushToWebView("onCodeReviewed", response)
            }
        }

        @JavascriptInterface
        fun explainCode(code: String) {
            this@CodeAgentClient.explainCode(code) { response ->
                pushToWebView("onCodeExplained", response)
            }
        }

        @JavascriptInterface
        fun refactorCode(code: String) {
            this@CodeAgentClient.receiveFixes(code) { response ->
                pushToWebView("onCodeRefactored", response)
            }
        }

        @JavascriptInterface
        fun analyzeTrace(trace: String) {
            this@CodeAgentClient.analyzeStackTraces(trace) { response ->
                pushToWebView("onTraceAnalyzed", response)
            }
        }

        @JavascriptInterface
        fun generateProject(type: String, name: String, desc: String) {
            this@CodeAgentClient.generateProjects(type, name, desc) { response ->
                pushToWebView("onProjectGenerated", response)
            }
        }

        @JavascriptInterface
        fun generateTests(code: String, framework: String) {
            this@CodeAgentClient.generateTests(code, framework) { response ->
                pushToWebView("onTestsGenerated", response)
            }
        }

        private fun pushToWebView(callbackName: String, response: JSONObject?) {
            val wv = webView ?: return
            val json = (response ?: JSONObject().put("status", "error")).toString().replace("'", "\\'")
            mainHandler.post {
                wv.evaluateJavascript(
                    "if(window.$callbackName) window.$callbackName('$json');",
                    null,
                )
            }
        }
    }

    fun createJsBridge() = CodeJsBridge()

    // ── HTTP helpers ──────────────────────────────────────────────────────────

    private fun post(endpoint: String, payload: JSONObject): JSONObject? {
        val url  = URL(endpoint)
        val conn = url.openConnection() as HttpURLConnection
        return try {
            conn.requestMethod  = "POST"
            conn.doOutput       = true
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
