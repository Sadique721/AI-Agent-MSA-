"""
tests/test_mobile_reasoning.py
================================
Phase-2 tests for the mobile reasoning API endpoints.

Tests:
  - POST /mobile/capabilities — device context upload
  - POST /mobile/validate     — action validation reporting
  - POST /mobile/status       — heartbeat / status
  - POST /mobile/task-result  — task result upload
  - GET  /api/reasoning-status — Phase-2 subsystem health
"""
import sys
import os
import json
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import Flask test client
from backend.server import app


@pytest.fixture(scope="module")
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ── Sample payloads ────────────────────────────────────────────────────────────

CAPABILITIES_PAYLOAD = {
    "battery":          82,
    "wifi":             True,
    "mobile_data":      False,
    "location_enabled": True,
    "storage_free_gb":  12.5,
    "storage_total_gb": 64.0,
    "apps":             ["WhatsApp", "Chrome", "YouTube", "Gmail"],
    "permissions":      ["RECORD_AUDIO", "ACCESS_FINE_LOCATION"],
    "device_id":        "test_device_001",
}

VALIDATE_PAYLOAD = {
    "action":    "notification",
    "success":   True,
    "detail":    "Notification sent for alarm at 7:00 AM",
    "task_id":   "task_alarm_001",
    "device_id": "test_device_001",
}

STATUS_PAYLOAD = {
    "event":     "heartbeat",
    "battery":   78,
    "wifi":      True,
    "charging":  False,
    "device_id": "test_device_001",
    "state":     "IDLE",
}

TASK_RESULT_PAYLOAD = {
    "task_id":   "task_search_001",
    "result":    "Found 25 Java developer jobs in Ahmedabad. Top result: Senior Java Dev at TCS.",
    "success":   True,
    "device_id": "test_device_001",
}


# ── POST /mobile/capabilities ─────────────────────────────────────────────────

class TestMobileCapabilities:

    def test_capabilities_returns_200(self, client):
        resp = client.post(
            "/mobile/capabilities",
            data=json.dumps(CAPABILITIES_PAYLOAD),
            content_type="application/json",
        )
        assert resp.status_code == 200

    def test_capabilities_status_ok(self, client):
        resp = client.post(
            "/mobile/capabilities",
            data=json.dumps(CAPABILITIES_PAYLOAD),
            content_type="application/json",
        )
        data = json.loads(resp.data)
        assert data["status"] == "ok"
        assert data["received"] is True

    def test_capabilities_summary_in_response(self, client):
        resp = client.post(
            "/mobile/capabilities",
            data=json.dumps(CAPABILITIES_PAYLOAD),
            content_type="application/json",
        )
        data = json.loads(resp.data)
        assert "summary" in data
        assert "Battery" in data["summary"] or "82" in data["summary"]

    def test_capabilities_empty_payload(self, client):
        resp = client.post(
            "/mobile/capabilities",
            data=json.dumps({}),
            content_type="application/json",
        )
        assert resp.status_code == 200  # Should handle gracefully

    def test_capabilities_partial_payload(self, client):
        payload = {"battery": 50, "wifi": False}
        resp = client.post(
            "/mobile/capabilities",
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert resp.status_code == 200


# ── POST /mobile/validate ─────────────────────────────────────────────────────

class TestMobileValidate:

    def test_validate_returns_200(self, client):
        resp = client.post(
            "/mobile/validate",
            data=json.dumps(VALIDATE_PAYLOAD),
            content_type="application/json",
        )
        assert resp.status_code == 200

    def test_validate_status_ok(self, client):
        resp = client.post(
            "/mobile/validate",
            data=json.dumps(VALIDATE_PAYLOAD),
            content_type="application/json",
        )
        data = json.loads(resp.data)
        assert data["status"] == "ok"
        assert data["recorded"] is True

    def test_validate_failure_reported(self, client):
        payload = {
            "action":    "call",
            "success":   False,
            "detail":    "Call dropped after 2 seconds",
            "task_id":   "task_call_001",
            "device_id": "test_device_001",
        }
        resp = client.post(
            "/mobile/validate",
            data=json.dumps(payload),
            content_type="application/json",
        )
        data = json.loads(resp.data)
        assert data["status"] == "ok"
        assert "failed" in data["message"].lower() or "✗" in data["message"]

    def test_validate_success_message(self, client):
        resp = client.post(
            "/mobile/validate",
            data=json.dumps(VALIDATE_PAYLOAD),
            content_type="application/json",
        )
        data = json.loads(resp.data)
        assert "succeeded" in data["message"] or "✓" in data["message"]


# ── POST /mobile/status ───────────────────────────────────────────────────────

class TestMobileStatus:

    def test_status_returns_200(self, client):
        resp = client.post(
            "/mobile/status",
            data=json.dumps(STATUS_PAYLOAD),
            content_type="application/json",
        )
        assert resp.status_code == 200

    def test_status_ok(self, client):
        resp = client.post(
            "/mobile/status",
            data=json.dumps(STATUS_PAYLOAD),
            content_type="application/json",
        )
        data = json.loads(resp.data)
        assert data["status"] == "ok"
        assert data["received"] is True

    def test_multiple_status_posts(self, client):
        for i in range(3):
            payload = {**STATUS_PAYLOAD, "battery": 80 - i * 5}
            resp = client.post(
                "/mobile/status",
                data=json.dumps(payload),
                content_type="application/json",
            )
            assert resp.status_code == 200


# ── POST /mobile/task-result ──────────────────────────────────────────────────

class TestMobileTaskResult:

    def test_task_result_returns_200(self, client):
        resp = client.post(
            "/mobile/task-result",
            data=json.dumps(TASK_RESULT_PAYLOAD),
            content_type="application/json",
        )
        assert resp.status_code == 200

    def test_task_result_status_ok(self, client):
        resp = client.post(
            "/mobile/task-result",
            data=json.dumps(TASK_RESULT_PAYLOAD),
            content_type="application/json",
        )
        data = json.loads(resp.data)
        assert data["status"] == "ok"
        assert data["task_id"] == "task_search_001"

    def test_task_result_contains_validation(self, client):
        resp = client.post(
            "/mobile/task-result",
            data=json.dumps(TASK_RESULT_PAYLOAD),
            content_type="application/json",
        )
        data = json.loads(resp.data)
        # Validation may be None if Validator not ready, but field must exist
        assert "validation" in data

    def test_task_result_failure_handled(self, client):
        payload = {
            "task_id":   "task_fail_001",
            "result":    "",
            "success":   False,
            "device_id": "test_device_001",
        }
        resp = client.post(
            "/mobile/task-result",
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert resp.status_code == 200


# ── GET /api/reasoning-status ────────────────────────────────────────────────

class TestReasoningStatus:

    def test_reasoning_status_returns_200(self, client):
        resp = client.get("/api/reasoning-status")
        assert resp.status_code == 200

    def test_reasoning_status_online(self, client):
        resp = client.get("/api/reasoning-status")
        data = json.loads(resp.data)
        assert data["status"] == "online"

    def test_reasoning_status_has_phase2_key(self, client):
        resp = client.get("/api/reasoning-status")
        data = json.loads(resp.data)
        assert "phase2_subsystems" in data

    def test_reasoning_status_has_mobile_capabilities(self, client):
        # First send capabilities, then check status reflects them
        client.post(
            "/mobile/capabilities",
            data=json.dumps(CAPABILITIES_PAYLOAD),
            content_type="application/json",
        )
        resp = client.get("/api/reasoning-status")
        data = json.loads(resp.data)
        assert "mobile_capabilities" in data
