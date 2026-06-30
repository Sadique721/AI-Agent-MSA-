import logging
from flask import Flask, request, jsonify
from infrastructure.service_registry import BaseService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("msa.pdp")

app = Flask(__name__)

# RBAC Policy mappings: role -> resource -> actions
ROLE_POLICIES = {
    "admin": {
        "*": ["create", "read", "update", "delete", "execute"]
    },
    "developer": {
        "code": ["read", "update", "execute"],
        "memory": ["read"],
        "workflows": ["read", "execute"]
    },
    "guest": {
        "memory": ["read"]
    }
}

def evaluate_policy(role: str, action: str, resource: str, context: dict) -> bool:
    """Evaluates RBAC and ABAC dynamic conditions."""
    if role not in ROLE_POLICIES:
        return False
        
    permissions = ROLE_POLICIES[role]
    
    # Check wildcard access
    if "*" in permissions:
        if action in permissions["*"]:
            return True
            
    # Check resource specific access
    if resource in permissions:
        if action in permissions[resource]:
            # ABAC dynamic condition evaluation
            if action == "execute" and resource == "code":
                # Only allow execution if the user's location environment is local/office
                if context.get("environment") not in ("local", "office"):
                    logger.warning("ABAC Blocked: environment not local/office.")
                    return False
            return True
            
    return False

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy", "service": "pdp-authorization"}), 200

@app.route("/api/v1/authorize", methods=["POST"])
def authorize():
    """Policy Decision Point endpoint assessing role and context access rules."""
    data = request.json or {}
    role = data.get("role")
    action = data.get("action")
    resource = data.get("resource")
    context = data.get("context", {})
    
    if not all([role, action, resource]):
        return jsonify({"authorized": False, "error": "Missing role, action, or resource"}), 400
        
    is_auth = evaluate_policy(role, action, resource, context)
    return jsonify({
        "authorized": is_auth,
        "policy": "RBAC/ABAC",
        "decision": "PERMIT" if is_auth else "DENY"
    }), 200

class PdpService(BaseService):
    def __init__(self):
        super().__init__()

    def start(self) -> None:
        super().start()
        logger.info("PDP Authorization Service running.")

    def stop(self) -> None:
        super().stop()
        logger.info("PDP Authorization Service stopped.")

if __name__ == "__main__":
    app.run(port=8082, host="0.0.0.0", debug=False)
