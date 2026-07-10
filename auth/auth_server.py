import base64
import hashlib
import hmac
import json
import os
import time
import logging
from flask import Flask, request, jsonify
from infrastructure.service_registry import BaseService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("msa.auth")

app = Flask(__name__)

# SECURITY: Read from environment — NEVER hardcode secrets
SECRET_KEY = os.environ.get("MSA_SECRET_KEY", "")
if not SECRET_KEY:
    raise RuntimeError("MSA_SECRET_KEY environment variable is required for auth service")

# Mock DB — in production, replace with real PostgreSQL user lookup
# Passwords are stored as SHA-256 hashes. REAL deployments must use bcrypt.
# Default passwords intentionally left empty — set via USER_ADMIN_HASH / USER_DEV_HASH env vars.
USERS_DB = {
    "admin": os.environ.get("USER_ADMIN_HASH", ""),
    "developer": os.environ.get("USER_DEV_HASH", ""),
}

def base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('utf-8')

def generate_jwt(payload: dict) -> str:
    """Generates a secure HS256 JWT using standard base64 and hmac libraries."""
    header = {"alg": "HS256", "typ": "JWT"}
    header_enc = base64url_encode(json.dumps(header).encode('utf-8'))
    payload_enc = base64url_encode(json.dumps(payload).encode('utf-8'))
    
    signature_base = f"{header_enc}.{payload_enc}".encode('utf-8')
    sig = hmac.new(SECRET_KEY.encode('utf-8'), signature_base, hashlib.sha256).digest()
    sig_enc = base64url_encode(sig)
    
    return f"{header_enc}.{payload_enc}.{sig_enc}"

def verify_jwt(token: str) -> bool:
    """Verifies HS256 JWT token signature and expiry."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return False
        header_enc, payload_enc, sig_enc = parts
        
        signature_base = f"{header_enc}.{payload_enc}".encode('utf-8')
        expected_sig = hmac.new(SECRET_KEY.encode('utf-8'), signature_base, hashlib.sha256).digest()
        expected_sig_enc = base64url_encode(expected_sig)
        
        if not hmac.compare_digest(sig_enc, expected_sig_enc):
            return False
            
        # Decode and check expiry
        payload_bytes = base64.urlsafe_b64decode(payload_enc + "==")
        payload = json.loads(payload_bytes.decode('utf-8'))
        
        if "exp" in payload and time.time() > payload["exp"]:
            return False
            
        return True
    except Exception:
        return False

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy", "service": "auth-server"}), 200

@app.route("/oauth/token", methods=["POST"])
def token():
    """OAuth 2.0 Token Endpoint issuing short-lived JWT tokens."""
    username = request.json.get("username") or request.form.get("username")
    password = request.json.get("password") or request.form.get("password")
    
    if not username or not password:
        return jsonify({"error": "invalid_request", "error_description": "Missing credentials"}), 400
        
    pw_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()
    if USERS_DB.get(username) != pw_hash:
        return jsonify({"error": "invalid_grant", "error_description": "Invalid username or password"}), 401
        
    # Generate token payload
    now = int(time.time())
    payload = {
        "iss": "msa-auth-server",
        "sub": username,
        "iat": now,
        "exp": now + 3600,  # 1 hour expiry
        "roles": ["admin"] if username == "admin" else ["developer"]
    }
    
    access_token = generate_jwt(payload)
    return jsonify({
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_in": 3600
    }), 200

@app.route("/oauth/verify", methods=["POST"])
def verify():
    token_str = request.json.get("token")
    if not token_str:
        return jsonify({"valid": False, "error": "Missing token"}), 400
    is_valid = verify_jwt(token_str)
    return jsonify({"valid": is_valid}), 200

class AuthService(BaseService):
    def __init__(self):
        super().__init__()

    def start(self) -> None:
        super().start()
        logger.info("Authentication Service running.")

    def stop(self) -> None:
        super().stop()
        logger.info("Authentication Service stopped.")

if __name__ == "__main__":
    app.run(port=8081, host="0.0.0.0", debug=False)
