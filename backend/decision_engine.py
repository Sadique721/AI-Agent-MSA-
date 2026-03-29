try:
    from llama_cpp import Llama
except ImportError:
    Llama = None
import json
import os

class DecisionEngine:
    def __init__(self, model_path="models/llm/llama-2-7b-chat.Q4_K_M.gguf"):
        model_full_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), model_path)
        if Llama and os.path.exists(model_full_path):
            self.llm = Llama(model_path=model_full_path, n_ctx=2048, n_threads=4)
        else:
            print(f"[Warning] LLM not found at {model_full_path} or llama_cpp missing. Decision Engine offline.")
            self.llm = None
        self.profile = self.load_profile()

    def load_profile(self):
        try:
            import os
            profile_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data/user_profile.json")
            with open(profile_path, "r") as f:
                return json.load(f)
        except:
            return {"name": "Md Sadique Amin", "role": "software engineer"}

    def process_command(self, user_input, context):
        if not self.llm:
            return {"response": f"Mocking decision for {user_input}", "action": "none"}
            
        prompt = f"""
You are MSA, an AI assistant. Your user's profile: Name {self.profile.get('name', 'Unknown')}, Role {self.profile.get('role', 'Unknown')}.
Previous context: {context}
User command: {user_input}

Decide the best action. Respond ONLY with a JSON object containing:
- "response": a short spoken reply (in Hinglish or English)
- "action": one of: "open_app", "shutdown", "restart", "mobile_open_app", "mobile_make_call", "mobile_set_alarm", "automation", "internet_search", "vision", "none"
- "parameters": an object with required parameters (e.g., {{"app": "chrome"}})

If the command is unclear or not an action, set action to "none".
"""
        try:
            output = self.llm(prompt, max_tokens=256, temperature=0.7, stop=["\n\n"])
            text = output['choices'][0]['text'].strip()
            # Extract JSON from text (may have extra text)
            start = text.find('{')
            end = text.rfind('}') + 1
            if start >= 0 and end > start:
                json_str = text[start:end]
                return json.loads(json_str)
        except Exception as e:
            print(f"LLM Error: {e}")
            pass
        # Fallback
        return {"response": "I didn't understand the complex logic.", "action": "none", "parameters": {}}
