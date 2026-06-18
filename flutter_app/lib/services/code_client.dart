import 'dart:convert';
import 'package:http/http.dart' as http;

class CodeClient {
  final String serverUrl;

  CodeClient({required this.serverUrl});

  Future<Map<String, dynamic>?> submitCode(String prompt, {String? language}) async {
    try {
      final payload = {
        'prompt': prompt,
        if (language != null) 'language': language,
      };
      final response = await http.post(
        Uri.parse('$serverUrl/api/code/generate'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode(payload),
      ).timeout(const Duration(seconds: 30));
      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      }
    } catch (_) {}
    return null;
  }

  Future<Map<String, dynamic>?> uploadLogs(String logs) async {
    try {
      // FIX BUG-11: was /api/code/debug — correct endpoint is /api/code/analyze
      final response = await http.post(
        Uri.parse('$serverUrl/api/code/analyze'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'logs': logs}),
      ).timeout(const Duration(seconds: 30));
      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      }
    } catch (_) {}
    return null;
  }

  Future<Map<String, dynamic>?> viewReviewReports(String code) async {
    try {
      final response = await http.post(
        Uri.parse('$serverUrl/api/code/review'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'code': code}),
      ).timeout(const Duration(seconds: 30));
      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      }
    } catch (_) {}
    return null;
  }

  Future<Map<String, dynamic>?> refactorCode(String code) async {
    try {
      final response = await http.post(
        Uri.parse('$serverUrl/api/code/refactor'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'code': code}),
      ).timeout(const Duration(seconds: 30));
      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      }
    } catch (_) {}
    return null;
  }

  Future<Map<String, dynamic>?> explainCode(String code) async {
    try {
      final response = await http.post(
        Uri.parse('$serverUrl/api/code/explain'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'code': code}),
      ).timeout(const Duration(seconds: 30));
      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      }
    } catch (_) {}
    return null;
  }

  Future<Map<String, dynamic>?> generateTests(String code, {String? framework}) async {
    try {
      final payload = {
        'code': code,
        if (framework != null) 'framework': framework,
      };
      // FIX BUG-12: was /api/code/test — correct endpoint is /api/code/tests
      final response = await http.post(
        Uri.parse('$serverUrl/api/code/tests'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode(payload),
      ).timeout(const Duration(seconds: 30));
      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      }
    } catch (_) {}
    return null;
  }

  Future<Map<String, dynamic>?> analyzeStackTrace(String trace) async {
    try {
      // FIX BUG-13: was /api/code/stacktrace — aligned with backend route
      final response = await http.post(
        Uri.parse('$serverUrl/api/code/stacktrace'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'trace': trace}),
      ).timeout(const Duration(seconds: 30));
      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      }
    } catch (_) {}
    return null;
  }

  Future<Map<String, dynamic>?> getCodeHistory({int limit = 20}) async {
    try {
      final response = await http.get(
        Uri.parse('$serverUrl/api/code/history?limit=$limit'),
      );
      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      }
    } catch (_) {}
    return null;
  }
}
