package com.msa.agent

import android.os.Bundle
import android.widget.Button
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import org.json.JSONObject

class CodingHistoryActivity : AppCompatActivity() {

    private lateinit var btnRefresh: Button
    private lateinit var tvHistory: TextView
    private lateinit var client: CodeAgentClient

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_coding_history)
        supportActionBar?.title = "Coding Agent History"

        btnRefresh = findViewById(R.id.btn_refresh)
        tvHistory = findViewById(R.id.tv_history)

        client = CodeAgentClient(this, "http://10.0.2.2:5000")

        btnRefresh.setOnClickListener {
            loadHistory()
        }

        // Auto load on start
        loadHistory()
    }

    private fun loadHistory() {
        tvHistory.text = "Loading coding history..."
        client.getCodeHistory(20) { response ->
            if (response != null) {
                val status = response.optString("status")
                if (status == "success" || status == "ok") {
                    val history = response.optJSONArray("history")
                    if (history != null && history.length() > 0) {
                        val historyText = StringBuilder()
                        for (i in 0 until history.length()) {
                            val entry = history.get(i)
                            if (entry is JSONObject) {
                                val category = entry.optString("category", "info")
                                val text = entry.optString("text", entry.optString("content", ""))
                                val time = entry.optString("timestamp", "")
                                historyText.append("[")
                                    .append(category.uppercase())
                                    .append("] ")
                                    .append(time)
                                    .append("\n")
                                    .append(text)
                                    .append("\n\n-----------------\n\n")
                            } else {
                                historyText.append(entry.toString()).append("\n\n-----------------\n\n")
                            }
                        }
                        tvHistory.text = historyText.toString()
                    } else {
                        tvHistory.text = "No history entries found."
                    }
                } else {
                    tvHistory.text = "Error: " + response.optString("message", "unknown error")
                }
            } else {
                tvHistory.text = "Could not connect to backend server."
            }
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        client.shutdown()
    }
}
