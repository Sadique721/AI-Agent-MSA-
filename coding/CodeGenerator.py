"""
coding/CodeGenerator.py
======================
Generates source code from natural language prompts.
Provides templates and rule-based generation, with optional LLM integration.
"""

import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("msa.coding.generator")

class CodeGenerator:
    def __init__(self, llm: Any = None):
        self.llm = llm

    def generate(self, prompt: str, language: str = None) -> Dict[str, Any]:
        """
        Main entry point for generating code from a prompt.
        Attempts to automatically detect target language/framework if not supplied.
        """
        prompt_lower = prompt.lower()
        if not language:
            if "spring" in prompt_lower or "springboot" in prompt_lower:
                language = "springboot"
            elif "angular" in prompt_lower:
                language = "angular"
            elif "javascript" in prompt_lower or "js" in prompt_lower or "node" in prompt_lower:
                language = "javascript"
            elif "java" in prompt_lower:
                language = "java"
            elif "sql" in prompt_lower or "database" in prompt_lower:
                language = "sql"
            elif "python" in prompt_lower or "pytest" in prompt_lower:
                language = "python"
            else:
                language = "python"  # default

        # Try LLM if available
        if self.llm:
            try:
                return self._llm_generate(prompt, language)
            except Exception as e:
                logger.warning("LLM generate failed: %s. Falling back to rule-based.", e)

        # Rule-based / template fallbacks
        if language == "springboot":
            return self.generate_springboot(prompt)
        elif language == "angular":
            return self.generate_angular(prompt)
        elif language == "java":
            return self.generate_java(prompt)
        elif language == "sql":
            return self.generate_sql(prompt)
        elif language == "javascript":
            return self.generate_javascript(prompt)
        else:
            return self.generate_python(prompt)

    def generate_java(self, prompt: str) -> Dict[str, Any]:
        """Generate plain Java class."""
        class_name = self._extract_class_name(prompt, "CustomerService")
        content = f"""package com.example.demo.service;

import java.util.List;
import java.util.ArrayList;

public class {class_name} {{
    private final List<String> items = new ArrayList<>();

    public void add(String item) {{
        if (item == null) {{
            throw new IllegalArgumentException("Item cannot be null");
        }}
        items.add(item);
    }}

    public List<String> getAll() {{
        return new ArrayList<>(items);
    }}
}}
"""
        return {
            "language": "java",
            "files": [
                {
                    "path": f"src/main/java/com/example/demo/service/{class_name}.java",
                    "content": content
                }
            ],
            "explanation": f"Generated plain Java helper class `{class_name}` with basic validations and item listing."
        }

    def generate_springboot(self, prompt: str) -> Dict[str, Any]:
        """Generate Spring Boot entity, repository, service, and controller."""
        entity = self._extract_class_name(prompt, "Customer")
        entity_lower = entity.lower()
        
        controller_content = f"""package com.example.demo.controller;

import com.example.demo.model.{entity};
import com.example.demo.service.{entity}Service;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/{entity_lower}s")
public class {entity}Controller {{

    @Autowired
    private {entity}Service service;

    @GetMapping
    public List<{entity}> getAll() {{
        return service.findAll();
    }}

    @GetMapping("/{{id}}")
    public ResponseEntity<{entity}> getById(@PathVariable Long id) {{
        return service.findById(id)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }}

    @PostMapping
    public {entity} create(@RequestBody {entity} item) {{
        return service.save(item);
    }}

    @DeleteMapping("/{{id}}")
    public ResponseEntity<Void> delete(@PathVariable Long id) {{
        service.deleteById(id);
        return ResponseEntity.noContent().build();
    }}
}}
"""

        service_content = f"""package com.example.demo.service;

import com.example.demo.model.{entity};
import com.example.demo.repository.{entity}Repository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Optional;

@Service
public class {entity}Service {{

    @Autowired
    private {entity}Repository repository;

    public List<{entity}> findAll() {{
        return repository.findAll();
    }}

    public Optional<{entity}> findById(Long id) {{
        return repository.findById(id);
    }}

    public {entity} save({entity} item) {{
        return repository.save(item);
    }}

    public void deleteById(Long id) {{
        repository.deleteById(id);
    }}
}}
"""

        repo_content = f"""package com.example.demo.repository;

import com.example.demo.model.{entity};
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface {entity}Repository extends JpaRepository<{entity}, Long> {{
}}
"""

        model_content = f"""package com.example.demo.model;

import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;

@Entity
public class {entity} {{

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    private String name;

    public {entity}() {{
    }}

    public Long getId() {{
        return id;
    }}

    public void setId(Long id) {{
        this.id = id;
    }}

    public String getName() {{
        return name;
    }}

    public void setName(String name) {{
        this.name = name;
    }}
}}
"""

        return {
            "language": "springboot",
            "files": [
                {"path": f"src/main/java/com/example/demo/controller/{entity}Controller.java", "content": controller_content},
                {"path": f"src/main/java/com/example/demo/service/{entity}Service.java", "content": service_content},
                {"path": f"src/main/java/com/example/demo/repository/{entity}Repository.java", "content": repo_content},
                {"path": f"src/main/java/com/example/demo/model/{entity}.java", "content": model_content}
            ],
            "explanation": f"Generated complete Spring Boot CRUD APIs for `{entity}` including Controller, Service layer, Repository interface, and JPA entity."
        }

    def generate_angular(self, prompt: str) -> Dict[str, Any]:
        """Generate Angular components (ts, html, css)."""
        name = self._extract_class_name(prompt, "login").lower()
        pascal_name = name.capitalize()

        ts_content = f"""import {{ Component, OnInit }} from '@angular/core';
import {{ FormBuilder, FormGroup, Validators }} from '@angular/forms';

@Component({{
  selector: 'app-{name}',
  templateUrl: './{name}.component.html',
  styleUrls: ['./{name}.component.css']
}})
export class {pascal_name}Component implements OnInit {{
  myForm!: FormGroup;
  submitted = false;

  constructor(private fb: FormBuilder) {{}}

  ngOnInit(): void {{
    this.myForm = this.fb.group({{
      username: ['', [Validators.required, Validators.minLength(4)]],
      password: ['', [Validators.required, Validators.minLength(6)]]
    }});
  }}

  onSubmit(): void {{
    this.submitted = true;
    if (this.myForm.invalid) {{
      return;
    }}
    console.log('Submitted successfully', this.myForm.value);
  }}
}}
"""

        html_content = f"""<div class="{name}-container">
  <h2>{pascal_name} Form</h2>
  <form [formGroup]="myForm" (ngSubmit)="onSubmit()">
    <div class="form-group">
      <label for="username">Username</label>
      <input id="username" type="text" formControlName="username" class="form-control" />
      <div *ngIf="submitted && myForm.controls['username'].errors" class="error">
        Username is required (min 4 characters).
      </div>
    </div>
    <div class="form-group">
      <label for="password">Password</label>
      <input id="password" type="password" formControlName="password" class="form-control" />
      <div *ngIf="submitted && myForm.controls['password'].errors" class="error">
        Password is required (min 6 characters).
      </div>
    </div>
    <button type="submit" class="btn btn-primary">Submit</button>
  </form>
</div>
"""

        css_content = f""".{name}-container {{
  max-width: 400px;
  margin: 40px auto;
  padding: 20px;
  border: 1px solid #ccc;
  border-radius: 4px;
}}
.form-group {{
  margin-bottom: 15px;
}}
.error {{
  color: red;
  font-size: 12px;
  margin-top: 5px;
}}
"""

        return {
            "language": "angular",
            "files": [
                {"path": f"src/app/{name}/{name}.component.ts", "content": ts_content},
                {"path": f"src/app/{name}/{name}.component.html", "content": html_content},
                {"path": f"src/app/{name}/{name}.component.css", "content": css_content}
            ],
            "explanation": f"Generated Angular component files for `{pascal_name}Component` including Form validation, reactive state logic, view layout, and stylesheets."
        }

    def generate_sql(self, prompt: str) -> Dict[str, Any]:
        """Generate SQL schema creation and CRUD query scripts."""
        table = self._extract_class_name(prompt, "customers").lower()
        sql = f"""-- Create Table
CREATE TABLE IF NOT EXISTS {table} (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert Query
INSERT INTO {table} (name, email) VALUES ('MD SADIQUE AMIN', 'sadique@example.com');

-- Select Query
SELECT * FROM {table} WHERE name LIKE '%SADIQUE%';

-- Update Query
UPDATE {table} SET email = 'new_email@example.com' WHERE id = 1;

-- Delete Query
DELETE FROM {table} WHERE id = 1;
"""
        return {
            "language": "sql",
            "files": [
                {"path": f"schema_{table}.sql", "content": sql}
            ],
            "explanation": f"Generated DDL table definitions and CRUD scripts for database table `{table}`."
        }

    def generate_python(self, prompt: str) -> Dict[str, Any]:
        """Generate clean Python script."""
        name = self._extract_class_name(prompt, "customer_search").lower()
        python_content = f"""def search_customer(query: str, customers: list) -> list:
    \"\"\"
    Searches customers by name matching the query case-insensitively.
    \"\"\"
    if not query:
        return []
    
    normalized_query = query.strip().lower()
    return [c for c in customers if normalized_query in c.get("name", "").lower()]

if __name__ == "__main__":
    db = [
        {{"id": 1, "name": "MD SADIQUE AMIN"}},
        {{"id": 2, "name": "DeepMind Team"}},
        {{"id": 3, "name": "Python Developer"}}
    ]
    results = search_customer("sadique", db)
    print("Search Results:", results)
"""
        return {
            "language": "python",
            "files": [
                {"path": f"{name}.py", "content": python_content}
            ],
            "explanation": "Generated Python search function with local mock list structure and executable script entry point."
        }

    def generate_javascript(self, prompt: str) -> Dict[str, Any]:
        """Generate Node JS Express REST server endpoint."""
        name = self._extract_class_name(prompt, "server").lower()
        js_content = f"""const express = require('express');
const app = express();
const PORT = process.env.PORT || 3000;

app.use(express.json());

let customers = [
    {{ id: 1, name: 'MD SADIQUE AMIN', email: 'sadique@example.com' }}
];

// GET search customers
app.get('/api/customers/search', (req, res) => {{
    const query = (req.query.q || '').toLowerCase();
    const results = customers.filter(c => c.name.toLowerCase().includes(query));
    res.json(results);
}});

// POST create customer
app.post('/api/customers', (req, res) => {{
    const {{ name, email }} = req.body;
    if (!name || !email) {{
        return res.status(400).json({{ error: 'Name and email are required' }});
    }}
    const newCustomer = {{ id: customers.length + 1, name, email }};
    customers.push(newCustomer);
    res.status(201).json(newCustomer);
}});

app.listen(PORT, () => {{
    console.log(`Server is running on port ${{PORT}}`);
}});
"""
        return {
            "language": "javascript",
            "files": [
                {"path": f"{name}.js", "content": js_content}
            ],
            "explanation": "Generated NodeJS Express REST endpoint script featuring customer search and creation."
        }

    def _extract_class_name(self, prompt: str, default: str) -> str:
        """Helper to extract a clean class/component name from prompt."""
        words = prompt.split()
        keywords = ["class", "component", "entity", "api", "endpoint", "for", "table"]
        for i, w in enumerate(words):
            if w.lower() in keywords and i + 1 < len(words):
                name = words[i+1].replace("'", "").replace('"', "").replace("`", "").strip(".,!?")
                if len(name) > 2 and name.lower() not in keywords:
                    return name
        return default

    def _llm_generate(self, prompt: str, language: str) -> Dict[str, Any]:
        """Generates code utilizing local LLM model."""
        system_prompt = (
            f"You are a Senior Software Engineer. Generate clean, syntactically correct, "
            f"modular code in {language} for: '{prompt}'. Return response as a JSON dictionary "
            f"with keys 'language', 'files' (a list of objects with 'path' and 'content'), "
            f"and 'explanation'. Do not output raw markdown around the JSON, return ONLY valid raw JSON."
        )
        # Call llama_cpp
        response = self.llm.create_chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2
        )
        raw_text = response['choices'][0]['message']['content'].strip()
        # Clean potential markdown fences
        if raw_text.startswith("```json"):
            raw_text = raw_text[7:]
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3]
        return json.loads(raw_text.strip())
