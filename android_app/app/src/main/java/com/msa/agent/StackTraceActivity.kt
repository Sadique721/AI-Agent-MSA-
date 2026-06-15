package com.msa.agent

import android.os.Bundle
import android.widget.Button
import android.widget.EditText
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import org.json.JSONObject

class StackTraceActivity : AppCompatActivity() {

    private lateinit var etTraceInput: EditText
    private lateinit var btnAnalyze: Button
    private lateinit var tvResult: TextView
    private lateinit var client: CodeAgentClient

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_stack_trace)
        supportActionBar?.title = "Stack Trace Analyzer"

        etTraceInput = findViewById(R.id.et_trace_input)
        btnAnalyze = findViewById(R.id.btn_analyze)
        tvResult = findViewById(R.id.tv_result)

        client = CodeAgentClient(this, "http://10.0.2.2:5000")

        btnAnalyze.setOnClickListener {
            val trace = etTraceInput.text.toString().trim()
            if (trace.isEmpty()) {
                Toast.makeText(this, "Please paste a stacktrace first", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }

            tvResult.text = "Analyzing stack trace..."
            client.analyzeStackTraces(trace) { response ->
                if (response != null) {
                    val status = response.optString("status")
                    if (status == "success") {
                        val result = response.optJSONObject("result")
                        if (result != null) {
                            val file = result.optString("file", "Unknown")
                            val line = result.optInt("line", 0)
                            val rootCause = result.optString("rootCause", result.optString("issue", "Unknown"))
                            val recommended = result.optJSONArray("recommendedFixes") ?: result.optJSONArray("suggestion")
                            val fixes = StringBuilder()
                            if (recommended != null) {
                                for (i in 0 until recommended.length()) {
                                    fixes.append("- ").append(recommended.getString(i)).append("\n")
                                }
                            } else {
                                val singleSuggestion = result.optString("suggestion", "")
                                if (singleSuggestion.isNotEmpty()) {
                                    fixes.append("- ").append(singleSuggestion).append("\n")
                                }
                            }
                            tvResult.text = "File: $file\nLine: $line\n\nRoot Cause:\n$rootCause\n\nRecommended Fixes:\n$fixes"
                        } else {
                            tvResult.text = "Failed to parse analysis."
                        }
                    } else {
                        tvResult.text = "Error: " + response.optString("message", "unknown error")
                    }
                } else {
                    tvResult.text = "Could not connect to backend server."
                }
            }
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        client.shutdown()
    }
}
