import time
import logging
from flask import Flask, request, jsonify, Response
import urllib.request
import urllib.error
from infrastructure.service_registry import BaseService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("msa.gateway")

app = Flask(__name__)

# State tracking for Gateway (Circuit Breaker & Rate Limiting)
CIRCUIT_BREAKER_THRESHOLD = 5
FAILURE_WINDOW = 30  # seconds
COOLDOWN_PERIOD = 15  # seconds

class CircuitBreaker:
    def __init__(self):
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF-OPEN

    def record_success(self):
        self.failure_count = 0
        self.state = "CLOSED"

    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= CIRCUIT_BREAKER_THRESHOLD:
            self.state = "OPEN"
            logger.error("Circuit breaker tripped to OPEN state.")

    def allow_request(self) -> bool:
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > COOLDOWN_PERIOD:
                self.state = "HALF-OPEN"
                logger.info("Circuit breaker entered HALF-OPEN state.")
                return True
            return False
        return True

# Map backends — read from env for Docker container networking
import os
backend_breaker  = CircuitBreaker()
BACKEND_URL      = os.environ.get("BACKEND_URL", "http://localhost:5000")
AUTH_SERVER_URL  = os.environ.get("AUTH_SERVER_URL", "http://localhost:8081")

# Simple Rate Limiter (IP-based)
RATE_LIMIT_MAX = 100  # requests
RATE_LIMIT_WINDOW = 60  # seconds
ip_requests = {}

def is_rate_limited(ip: str) -> bool:
    now = time.time()
    if ip not in ip_requests:
        ip_requests[ip] = []
    # Clean old requests
    ip_requests[ip] = [t for t in ip_requests[ip] if now - t < RATE_LIMIT_WINDOW]
    if len(ip_requests[ip]) >= RATE_LIMIT_MAX:
        return True
    ip_requests[ip].append(now)
    return False

@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "healthy",
        "circuit_breaker": backend_breaker.state,
        "service": "api-gateway"
    }), 200

@app.route("/api/v1/auth/<path:subpath>", methods=["GET", "POST"])
def route_auth(subpath):
    """Routes requests to the Auth server."""
    url = f"{AUTH_SERVER_URL}/{subpath}"
    if request.query_string:
        url += f"?{request.query_string.decode('utf-8')}"
        
    try:
        req = urllib.request.Request(
            url,
            data=request.get_data() or None,
            headers={k: v for k, v in request.headers if k.lower() not in ("host", "content-length")},
            method=request.method
        )
        with urllib.request.urlopen(req, timeout=3.0) as response:
            return Response(response.read(), status=response.status, headers=dict(response.getheaders()))
    except urllib.error.HTTPError as e:
        return Response(e.read(), status=e.code, headers=dict(e.headers))
    except Exception as e:
        logger.error("Failed to forward auth request: %s", e)
        return jsonify({"error": "Auth service unavailable"}), 503

@app.route("/api/v1/execute", methods=["POST"])
def execute_command():
    """Routes execution requests to the core backend executor service."""
    ip = request.remote_addr or "unknown"
    if is_rate_limited(ip):
        return jsonify({"error": "Too many requests. Rate limit exceeded."}), 429

    if not backend_breaker.allow_request():
        return jsonify({"error": "Service temporarily degraded (Circuit Breaker OPEN)"}), 503

    try:
        # Build forward request
        req = urllib.request.Request(
            f"{BACKEND_URL}/api/execute",
            data=request.get_data(),
            headers={k: v for k, v in request.headers if k.lower() not in ("host", "content-length")},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=5.0) as response:
            backend_breaker.record_success()
            return Response(response.read(), status=response.status, headers=dict(response.getheaders()))
    except Exception as e:
        logger.error("Backend request failed: %s", e)
        backend_breaker.record_failure()
        return jsonify({"error": "Core agent service unavailable"}), 502

class GatewayService(BaseService):
    def __init__(self):
        super().__init__()
        
    def start(self) -> None:
        super().start()
        logger.info("Gateway Service started.")

    def stop(self) -> None:
        super().stop()
        logger.info("Gateway Service stopped.")

if __name__ == "__main__":
    app.run(port=8080, host="0.0.0.0", debug=False)
