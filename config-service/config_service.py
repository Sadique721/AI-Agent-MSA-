import logging
from flask import Flask, request, jsonify
from infrastructure.service_registry import BaseService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("msa.config_service")

app = Flask(__name__)

# Mock configuration storage
CONFIG_STORE = {
    "default": {
        "max_connections": 100,
        "timeout": 30,
        "default_model": "llama3"
    },
    "production": {
        "max_connections": 1000,
        "timeout": 15,
        "default_model": "deepseek-coder"
    }
}

# Feature Flags configurations (Module 13)
FEATURE_FLAGS = {
    "enable_graph_rag": True,
    "enable_code_auditor": True,
    "enable_canary_routing": False
}

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy", "service": "config-feature-flag"}), 200

@app.route("/api/v1/config/<env>", methods=["GET"])
def get_config(env):
    """Retrieve configurations for a specific environment."""
    config = CONFIG_STORE.get(env, CONFIG_STORE["default"])
    return jsonify(config), 200

@app.route("/api/v1/flags", methods=["GET"])
def get_flags():
    """Lists all active feature flags."""
    return jsonify(FEATURE_FLAGS), 200

@app.route("/api/v1/flags/eval", methods=["POST"])
def evaluate_flag():
    """Evaluates target rule for user segments."""
    data = request.json or {}
    flag_name = data.get("flag")
    user_id = data.get("user_id")
    
    if not flag_name:
        return jsonify({"error": "Missing flag name"}), 400
        
    val = FEATURE_FLAGS.get(flag_name, False)
    # Canary evaluation simulation
    if flag_name == "enable_canary_routing" and user_id:
        # Route 10% of users to True using hashing
        val = (hash(user_id) % 10 == 0)
        
    return jsonify({
        "flag": flag_name,
        "value": val
    }), 200

class ConfigService(BaseService):
    def __init__(self):
        super().__init__()

    def start(self) -> None:
        super().start()
        logger.info("Configuration Service running.")

    def stop(self) -> None:
        super().stop()
        logger.info("Configuration Service stopped.")

if __name__ == "__main__":
    app.run(port=8083, host="0.0.0.0", debug=False)
