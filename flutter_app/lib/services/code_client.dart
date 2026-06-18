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
      );
      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      }
    } catch (_) {}
    return null;
  }

  Future<Map<String, dynamic>?> uploadLogs(String logs) async {
    try {
      final response = await http.post(
        Uri.parse('$serverUrl/api/code/debug'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'logs': logs}),
      );
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
      );
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
      );
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
      );
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
      final response = await http.post(
        Uri.parse('$serverUrl/api/code/test'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode(payload),
      );
      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      }
    } catch (_) {}
    return null;
  }

  Future<Map<String, dynamic>?> analyzeStackTrace(String trace) async {
    try {
      final response = await http.post(
        Uri.parse('$serverUrl/api/code/stacktrace'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'trace': trace}),
      );
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
