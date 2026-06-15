package com.msa.agent

import android.os.Bundle
import android.widget.Button
import android.widget.EditText
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import org.json.JSONObject

class ProjectGeneratorActivity : AppCompatActivity() {

    private lateinit var etProjectName: EditText
    private lateinit var etProjectType: EditText
    private lateinit var etProjectDesc: EditText
    private lateinit var btnGenerate: Button
    private lateinit var tvResult: TextView
    private lateinit var client: CodeAgentClient

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_project_generator)
        supportActionBar?.title = "Project Generator"

        etProjectName = findViewById(R.id.et_project_name)
        etProjectType = findViewById(R.id.et_project_type)
        etProjectDesc = findViewById(R.id.et_project_desc)
        btnGenerate = findViewById(R.id.btn_generate)
        tvResult = findViewById(R.id.tv_result)

        client = CodeAgentClient(this, "http://10.0.2.2:5000")

        btnGenerate.setOnClickListener {
            val name = etProjectName.text.toString().trim()
            val type = etProjectType.text.toString().trim()
            val desc = etProjectDesc.text.toString().trim()

            if (name.isEmpty() || type.isEmpty()) {
                Toast.makeText(this, "Project name and type are required", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }

            tvResult.text = "Generating project structure..."
            client.generateProjects(type, name, desc) { response ->
                if (response != null) {
                    val status = response.optString("status")
                    if (status == "success") {
                        val result = response.optJSONObject("result")
                        if (result != null) {
                            val language = result.optString("language", "N/A")
                            val files = result.optJSONArray("files")
                            val fileList = StringBuilder()
                            if (files != null) {
                                for (i in 0 until files.length()) {
                                    val f = files.getJSONObject(i)
                                    fileList.append("✓ ").append(f.optString("path")).append("\n")
                                }
                            }
                            val explanation = result.optString("explanation", "")
                            tvResult.text = "Language: $language\n\nGenerated Files:\n$fileList\nSummary:\n$explanation"
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
