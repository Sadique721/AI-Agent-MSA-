import time
import pytest
from shared.uuid_v7 import generate_uuid_v7
from auth.auth_server import generate_jwt, verify_jwt
from auth.pdp_server import evaluate_policy
from gateway.api_gateway import CircuitBreaker, is_rate_limited

def test_uuid_v7_generation():
    """Verify UUID v7 timestamp-based ordering and structure."""
    u1 = generate_uuid_v7()
    time.sleep(0.005)
    u2 = generate_uuid_v7()
    
    assert str(u1) != str(u2)
    # Timestamp ordering verification
    assert u1.bytes < u2.bytes
    # Version check (4th bit of byte 6 is version, 7)
    assert u1.variant == "specified" or u1.hex[12] == '7'

def test_token_issuance_and_verification():
    """Verify standard JWT signatures and expiration parameters."""
    payload = {"sub": "developer", "role": "developer", "exp": time.time() + 10}
    token = generate_jwt(payload)
    
    assert token is not None
    assert verify_jwt(token) is True
    
    # Verify expired token detection
    expired_payload = {"sub": "developer", "role": "developer", "exp": time.time() - 10}
    expired_token = generate_jwt(expired_payload)
    assert verify_jwt(expired_token) is False

def test_policy_decision_point():
    """Verify RBAC and ABAC dynamic checks evaluate correctly."""
    # Admin has wildcard access
    assert evaluate_policy("admin", "delete", "any_resource", {}) is True
    
    # Developer can write code but cannot delete database schemas
    assert evaluate_policy("developer", "read", "code", {}) is True
    assert evaluate_policy("developer", "delete", "code", {}) is False
    
    # Guest has restricted access
    assert evaluate_policy("guest", "read", "memory", {}) is True
    assert evaluate_policy("guest", "execute", "code", {}) is False

    # ABAC conditional check (fails if environment is not local/office)
    context_office = {"environment": "office"}
    context_home = {"environment": "home"}
    
    assert evaluate_policy("developer", "execute", "code", context_office) is True
    assert evaluate_policy("developer", "execute", "code", context_home) is False

def test_gateway_breakers_and_limits():
    """Verify Gateway components correctly record faults and limit IP access rates."""
    breaker = CircuitBreaker()
    assert breaker.allow_request() is True
    
    # Trigger breaker trip
    for _ in range(5):
        breaker.record_failure()
    assert breaker.allow_request() is False
    
    breaker.record_success()
    assert breaker.allow_request() is True

    # Rate limiting verification
    ip = "192.168.1.1"
    # Ensure ip requests resets/initialises
    for _ in range(105):
        limited = is_rate_limited(ip)
    assert limited is True
