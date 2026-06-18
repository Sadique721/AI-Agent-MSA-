import 'dart:async';
import 'dart:convert';
import 'package:http/http.dart' as http;
import '../utils/device_telemetry.dart';

class ReasoningClient {
  final String serverUrl;
  final DeviceTelemetry telemetry = DeviceTelemetry();
  bool _pollingActive = false;
  Timer? _pollTimer;

  ReasoningClient({required this.serverUrl});

  void start(Function(String) onStatusReceived) {
    _pollingActive = true;
    sendCapabilities();
    // FIX ISSUE-2: changed from 30s to 60s to reduce battery drain
    _pollTimer = Timer.periodic(const Duration(seconds: 60), (timer) async {
      if (!_pollingActive) return;
      try {
        await pollAgentStatus(onStatusReceived);
        await sendHeartbeat();
      } catch (_) {}
    });
  }

  void stop() {
    _pollingActive = false;
    _pollTimer?.cancel();
  }

  Future<void> sendCapabilities() async {
    try {
      final caps = await telemetry.getCapabilities();
      // FIX ISSUE-1: 10-second timeout to prevent indefinite hang
      final response = await http.post(
        Uri.parse('$serverUrl/mobile/capabilities'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode(caps),
      ).timeout(const Duration(seconds: 10));
      if (response.statusCode == 200) {
        print('[ReasoningClient] Capabilities sent successfully');
      }
    } catch (e) {
      print('[ReasoningClient] sendCapabilities failed: $e');
    }
  }

  Future<void> sendHeartbeat() async {
    try {
      final battery = await telemetry.getBatteryLevel();
      final wifi = await telemetry.isWifiConnected();
      final charging = await telemetry.isCharging();
      final devId = await telemetry.getDeviceId();

      final payload = {
        'event': 'heartbeat',
        'battery': battery,
        'wifi': wifi,
        'charging': charging,
        'device_id': devId,
      };

      // FIX ISSUE-1: 10-second timeout
      await http.post(
        Uri.parse('$serverUrl/mobile/status'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode(payload),
      ).timeout(const Duration(seconds: 10));
    } catch (_) {}
  }

  Future<void> pollAgentStatus(Function(String) callback) async {
    try {
      // FIX ISSUE-1: 10-second timeout
      final response = await http.get(
        Uri.parse('$serverUrl/api/reasoning-status'),
      ).timeout(const Duration(seconds: 10));
      if (response.statusCode == 200) {
        callback(response.body);
      }
    } catch (_) {}
  }

  Future<Map<String, dynamic>?> sendReasonRequest(String task) async {
    try {
      // FIX ISSUE-1: 30-second timeout for reasoning requests
      final response = await http.post(
        Uri.parse('$serverUrl/api/reason'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'task': task}),
      ).timeout(const Duration(seconds: 30));
      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      }
    } catch (_) {}
    return null;
  }
}
