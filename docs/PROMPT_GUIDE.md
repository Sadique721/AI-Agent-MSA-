# Prompt Engineering Guide — MSA V5.0

All system prompts in MSA AI Agent V5.0 are decoupled from python code and saved under the `prompts/` directory.

---

## 1. Modifying Prompts

To adjust the behavior of any agent, edit its corresponding Markdown file in `prompts/`:
- `planner.md`: Decomposes query into step DAG.
- `coder.md`: Rules for writing clean code with type annotations.
- `reviewer.md`: Rubric for evaluating code safety and complexity.
- `reflection.md`: Self-critique score threshold guidelines.

---

## 2. Template Variables

The `PromptLoader` reads prompt templates and performs substitution using double braces `{{variable_name}}`.

Common parameters injected by the workflow:
- `{{user_query}}`
- `{{persona}}`
- `{{available_tools}}`
- `{{memory_context}}`
- `{{rag_context}}`

---

## 3. Dynamic Rendering Example

If you want to render a prompt manually inside an endpoint or a plugin:

```python
from backend.shared.prompt_loader import get_prompt_loader

loader = get_prompt_loader()
# Automatically replaces {{name}} in prompts/test.md
prompt = loader.render("test", name="Md Sadique Amin")
```
