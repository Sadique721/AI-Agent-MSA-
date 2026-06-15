package com.msa.agent

import android.os.Bundle
import android.widget.Button
import android.widget.EditText
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import org.json.JSONObject

class CodeReviewActivity : AppCompatActivity() {

    private lateinit var etCodeInput: EditText
    private lateinit var btnReview: Button
    private lateinit var tvResult: TextView
    private lateinit var client: CodeAgentClient

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_code_review)
        supportActionBar?.title = "Code Reviewer"

        etCodeInput = findViewById(R.id.et_code_input)
        btnReview = findViewById(R.id.btn_review)
        tvResult = findViewById(R.id.tv_result)

        client = CodeAgentClient(this, "http://10.0.2.2:5000")

        btnReview.setOnClickListener {
            val code = etCodeInput.text.toString().trim()
            if (code.isEmpty()) {
                Toast.makeText(this, "Please paste some code first", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }

            tvResult.text = "Reviewing code..."
            client.viewReviewReports(code) { response ->
                if (response != null) {
                    val status = response.optString("status")
                    if (status == "success") {
                        val result = response.optJSONObject("result")
                        if (result != null) {
                            val grade = result.optString("grade", "N/A")
                            val score = result.optInt("score", 0)
                            val comments = result.optJSONArray("comments")
                            val commentsList = StringBuilder()
                            if (comments != null) {
                                for (i in 0 until comments.length()) {
                                    commentsList.append("- ").append(comments.getString(i)).append("\n")
                                }
                            }
                            tvResult.text = "Grade: $grade (${score}/100)\n\nComments:\n$commentsList"
                        } else {
                            tvResult.text = "Failed to parse result."
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
