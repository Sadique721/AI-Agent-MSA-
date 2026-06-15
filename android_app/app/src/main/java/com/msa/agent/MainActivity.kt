package com.msa.agent

import android.Manifest
import android.content.pm.PackageManager
import android.os.Bundle
import android.webkit.PermissionRequest
import android.webkit.WebChromeClient
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Toast
import androidx.activity.OnBackPressedCallback
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat

/**
 * MainActivity.kt
 * ===============
 * Phase-2 upgrade:
 *   - Initialises DeviceCapabilityManager, AgentStatusManager, ReasoningClient
 *   - Attaches MsaJsBridge + MsaStatusBridge JavaScript interfaces to WebView
 *   - Requests Phase-2 permissions (location, phone state, SMS, call)
 *   - Sends device capabilities to backend on first launch
 *   - Registers WebView JS callbacks for status updates
 */
class MainActivity : AppCompatActivity() {

    private lateinit var webView: WebView

    // Phase-1: server URL (edit this to match your laptop IP)
    private val serverUrl = "http://10.0.2.2:5000"
    private val appUrl    = "$serverUrl/app"

    // Phase-2 components
    private lateinit var capabilityManager: DeviceCapabilityManager
    private lateinit var reasoningClient:   ReasoningClient
    private lateinit var validationService: ValidationService

    // Permission request codes
    private companion object {
        const val REQ_AUDIO    = 101
        const val REQ_PHASE2   = 102
    }

    // All Phase-2 permissions
    private val phase2Permissions = arrayOf(
        Manifest.permission.RECORD_AUDIO,
        Manifest.permission.ACCESS_FINE_LOCATION,
        Manifest.permission.ACCESS_COARSE_LOCATION,
        Manifest.permission.READ_PHONE_STATE,
        Manifest.permission.SEND_SMS,
        Manifest.permission.CALL_PHONE,
        Manifest.permission.READ_CONTACTS,
    )

    // ── Lifecycle ─────────────────────────────────────────────────────────────

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        supportActionBar?.hide()

        // Init Phase-2 components
        capabilityManager = DeviceCapabilityManager(this)
        reasoningClient   = ReasoningClient(this, serverUrl)
        validationService = ValidationService(this, serverUrl)

        // Setup WebView
        webView = findViewById(R.id.webview)
        setupWebView()

        // Back press handler
        onBackPressedDispatcher.addCallback(this, object : OnBackPressedCallback(true) {
            override fun handleOnBackPressed() {
                if (webView.canGoBack()) webView.goBack() else finish()
            }
        })

        // Request permissions — Phase-2 first, audio included
        requestPhase2Permissions()
    }

    override fun onResume() {
        super.onResume()
        // Start reasoning client if not already running
        reasoningClient.start()
    }

    override fun onPause() {
        super.onPause()
        reasoningClient.stop()
    }

    override fun onDestroy() {
        super.onDestroy()
        AgentStatusManager.detachWebView()
        reasoningClient.detachWebView()
        reasoningClient.stop()
    }

    // ── WebView setup ─────────────────────────────────────────────────────────

    private fun setupWebView() {
        val settings = webView.settings
        settings.javaScriptEnabled          = true
        settings.domStorageEnabled          = true
        settings.mediaPlaybackRequiresUserGesture = false
        settings.useWideViewPort            = true
        settings.loadWithOverviewMode       = true
        settings.cacheMode                  = WebSettings.LOAD_DEFAULT
        settings.databaseEnabled            = true
        settings.allowFileAccess            = true
        settings.mixedContentMode           = WebSettings.MIXED_CONTENT_ALWAYS_ALLOW

        // Attach Phase-2 JavaScript interfaces
        webView.addJavascriptInterface(reasoningClient.createJsBridge(),  "MsaBridge")
        webView.addJavascriptInterface(AgentStatusManager.createJsBridge(), "MsaStatus")

        // Attach WebView to managers for JS push updates
        AgentStatusManager.attachWebView(webView)
        reasoningClient.attachWebView(webView)

        webView.webViewClient = object : WebViewClient() {
            override fun shouldOverrideUrlLoading(view: WebView?, url: String?): Boolean {
                return false
            }

            override fun onPageFinished(view: WebView?, url: String?) {
                super.onPageFinished(view, url)
                // Inject Phase-2 JS helper after page load
                injectStatusJs()
            }
        }

        webView.webChromeClient = object : WebChromeClient() {
            override fun onPermissionRequest(request: PermissionRequest?) {
                request?.let {
                    val granted = it.resources.filter { r ->
                        r == PermissionRequest.RESOURCE_AUDIO_CAPTURE ||
                        r == PermissionRequest.RESOURCE_VIDEO_CAPTURE
                    }
                    if (granted.isNotEmpty()) {
                        it.grant(granted.toTypedArray())
                        return
                    }
                }
                super.onPermissionRequest(request)
            }
        }

        webView.loadUrl(appUrl)
    }

    /**
     * Inject JavaScript that:
     *  - Registers window.onMsaStatusUpdate handler → updates UI panel
     *  - Registers window.onMsaServerStatus handler → server health updates
     *  - Registers window.onApprovalResult handler → approval dialog
     */
    private fun injectStatusJs() {
        val js = """
            (function() {
                // Status panel updater — called by AgentStatusManager.notifyUI()
                window.onMsaStatusUpdate = function(jsonStr) {
                    try {
                        var s = JSON.parse(jsonStr);
                        var panel = document.getElementById('reasoning-status-panel');
                        if (panel) {
                            panel.innerHTML =
                                '<b>🧠 ' + s.state + '</b><br>' +
                                (s.goal ? '🎯 ' + s.goal + '<br>' : '') +
                                (s.total_steps > 0 ? '📋 Step ' + s.current_step + '/' + s.total_steps + '<br>' : '') +
                                (s.progress > 0 ? '<div style="background:#4CAF50;height:4px;width:' + s.progress + '%;border-radius:2px;"></div>' : '') +
                                (s.validation_result ? '✓ ' + s.validation_result : '') +
                                (s.last_error ? '⚠ ' + s.last_error : '');
                        }
                    } catch(e) {}
                };

                // Server status handler
                window.onMsaServerStatus = function(jsonStr) {
                    try {
                        var s = JSON.parse(jsonStr);
                        var indicator = document.getElementById('server-status-dot');
                        if (indicator) {
                            indicator.style.background = s.status === 'online' ? '#4CAF50' : '#f44336';
                        }
                    } catch(e) {}
                };

                // Approval result handler
                window.onApprovalResult = function(confirmed, goal) {
                    var msg = confirmed
                        ? '✓ Action approved: ' + goal
                        : '✗ Action cancelled: ' + goal;
                    console.log('[MSA] ' + msg);
                };
            })();
        """.trimIndent()
        webView.evaluateJavascript(js, null)
    }

    // ── Permissions ───────────────────────────────────────────────────────────

    private fun requestPhase2Permissions() {
        val missing = phase2Permissions.filter {
            ContextCompat.checkSelfPermission(this, it) != PackageManager.PERMISSION_GRANTED
        }
        if (missing.isNotEmpty()) {
            ActivityCompat.requestPermissions(this, missing.toTypedArray(), REQ_PHASE2)
        } else {
            onAllPermissionsGranted()
        }
    }

    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<out String>,
        grantResults: IntArray,
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)

        val grantedCount = grantResults.count { it == PackageManager.PERMISSION_GRANTED }
        val totalCount   = grantResults.size

        when (requestCode) {
            REQ_PHASE2 -> {
                Toast.makeText(
                    this,
                    "MSA Phase-2: $grantedCount/$totalCount permissions granted.",
                    Toast.LENGTH_SHORT,
                ).show()
                // Reload WebView to reflect new permission state
                webView.reload()
                onAllPermissionsGranted()
            }
        }
    }

    private fun onAllPermissionsGranted() {
        // Send full capabilities to backend now that permissions are resolved
        Thread {
            try {
                reasoningClient.sendCapabilities()
            } catch (e: Exception) {
                // Server may not be ready yet — client will retry on start()
            }
        }.start()
    }
}
