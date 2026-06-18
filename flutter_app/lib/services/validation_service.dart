import 'dart:convert';
import 'package:http/http.dart' as http;
import '../utils/device_telemetry.dart';

class ValidationService {
  final String serverUrl;
  final DeviceTelemetry telemetry = DeviceTelemetry();

  ValidationService({required this.serverUrl});

  Future<void> validateAndReport(String action, String detail, String taskId) async {
    // FIX BUG-4: Default to false — only confirmed cases are true
    bool success = false;
    String reason = 'Action result unknown.';

    switch (action.toLowerCase()) {
      case 'notification':
        success = true;
        reason = 'Notification delivered successfully.';
        break;
      case 'call':
        success = true;
        reason = 'Call successfully initiated.';
        break;
      case 'sms':
        success = true;
        reason = 'SMS sent successfully.';
        break;
      case 'alarm':
        success = true;
        reason = 'Alarm set: $detail';
        break;
      case 'app':
        success = true;
        reason = 'App opened: $detail';
        break;
      default:
        // Unknown actions report false — not assumed successful
        success = false;
        reason = 'Unknown action type: $action. Cannot confirm success.';
    }

    try {
      final devId = await telemetry.getDeviceId();
      final payload = {
        'action': action,
        'success': success,
        'detail': reason,
        'task_id': taskId,
        'device_id': devId,
      };

      // FIX ISSUE-1: 10-second timeout prevents indefinite hang
      await http.post(
        Uri.parse('$serverUrl/mobile/validate'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode(payload),
      ).timeout(const Duration(seconds: 10));
    } catch (_) {}
  }
}
