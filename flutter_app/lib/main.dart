import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:webview_flutter/webview_flutter.dart';
import 'package:permission_handler/permission_handler.dart';
import 'services/reasoning_client.dart';
import 'services/validation_service.dart';
import 'utils/device_telemetry.dart';

// ---------------------------------------------------------------------------
// App Entry Point
// ---------------------------------------------------------------------------
void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const MsaAiAgentApp());
}

class MsaAiAgentApp extends StatelessWidget {
  const MsaAiAgentApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'MSA AI AGENT',
      debugShowCheckedModeBanner: false,
      theme: ThemeData.dark().copyWith(
        primaryColor: Colors.indigo,
        scaffoldBackgroundColor: const Color(0xFF050B18),
        colorScheme: const ColorScheme.dark(
          primary: Color(0xFF00D4FF),
          secondary: Color(0xFF7C3AED),
        ),
      ),
      home: const MsaHome(),
    );
  }
}

// ---------------------------------------------------------------------------
// Home Screen
// ---------------------------------------------------------------------------
class MsaHome extends StatefulWidget {
  const MsaHome({super.key});

  @override
  State<MsaHome> createState() => _MsaHomeState();
}

class _MsaHomeState extends State<MsaHome> {
  late final WebViewController _webController;

  // FIX BUG-1: Server URL is now configurable — not hardcoded to emulator IP
  String _serverUrl = 'http://192.168.1.100:5000'; // Will be loaded from prefs
  late ReasoningClient _reasoningClient;
  late ValidationService _validationService;
  final DeviceTelemetry _telemetry = DeviceTelemetry();

  @override
  void initState() {
    super.initState();
    _loadServerUrl();
  }

  // ── Load saved server URL from SharedPreferences ──────────────────────────
  Future<void> _loadServerUrl() async {
    final prefs = await SharedPreferences.getInstance();
    final savedUrl = prefs.getString('msa_server_url');
    if (savedUrl != null && savedUrl.isNotEmpty) {
      _serverUrl = savedUrl;
    }
    _initWebView();
    _initClients();
    await _requestPermissions();
  }

  void _initClients() {
    _reasoningClient = ReasoningClient(serverUrl: _serverUrl);
    _validationService = ValidationService(serverUrl: _serverUrl);
  }

  void _initWebView() {
    _webController = WebViewController()
      ..setJavaScriptMode(JavaScriptMode.unrestricted)
      ..setNavigationDelegate(
        NavigationDelegate(
          onPageFinished: (String url) {
            _injectJsBridges();
          },
          onWebResourceError: (WebResourceError error) {
            debugPrint('[WebView] Error: ${error.description}');
          },
        ),
      )
      ..addJavaScriptChannel(
        'MsaBridgeChannel',
        onMessageReceived: (JavaScriptMessage message) {
          _handleJsMessage(message.message);
        },
      )
      ..loadRequest(Uri.parse('$_serverUrl/app'));

    _reasoningClient.start((statusJson) {
      _webController.runJavaScript(
        "if(window.onMsaServerStatus) window.onMsaServerStatus('$statusJson');"
      );
    });
  }

  // ── Permission Requests ───────────────────────────────────────────────────
  Future<void> _requestPermissions() async {
    await [
      Permission.microphone,
      Permission.location,
      Permission.phone,
      Permission.sms,
      Permission.contacts,
      Permission.camera,
    ].request();
  }

  // ── JavaScript Bridge Injection ───────────────────────────────────────────
  void _injectJsBridges() {
    final serverUrlEscaped = _serverUrl.replaceAll("'", "\\'");
    final js = '''
      (function() {
        window.MsaBridge = {
          getServerUrl: function() { return '$serverUrlEscaped'; },
          getDeviceStatus: function() {
            return JSON.stringify({
              battery: 85,
              wifi: true,
              location_enabled: true,
              agent_state: 'IDLE'
            });
          },
          sendCapabilities: function() {
            MsaBridgeChannel.postMessage(JSON.stringify({event: 'sendCapabilities'}));
          },
          notifyActionComplete: function(action, detail, taskId) {
            MsaBridgeChannel.postMessage(JSON.stringify({
              event: 'notifyActionComplete',
              action: action,
              detail: detail,
              taskId: taskId
            }));
          },
          approveAction: function(confirmed, goal) {
            MsaBridgeChannel.postMessage(JSON.stringify({
              event: 'approveAction',
              confirmed: confirmed,
              goal: goal
            }));
          },
          openSettings: function() {
            MsaBridgeChannel.postMessage(JSON.stringify({event: 'openSettings'}));
          }
        };

        window.MsaStatus = {
          getStatus: function() {
            return JSON.stringify({
              state: 'IDLE',
              goal: '',
              current_step: 0,
              total_steps: 0,
              progress: 0
            });
          },
          getState: function() { return 'IDLE'; },
          getGoal: function() { return ''; },
          getProgress: function() { return 0; },
          isIdle: function() { return true; }
        };
      })();
    ''';
    _webController.runJavaScript(js);
  }

  // ── JavaScript Message Handler ────────────────────────────────────────────
  void _handleJsMessage(String message) {
    try {
      final data = jsonDecode(message);
      final event = data['event'];

      if (event == 'sendCapabilities') {
        _reasoningClient.sendCapabilities();
      } else if (event == 'notifyActionComplete') {
        _validationService.validateAndReport(
          data['action'],
          data['detail'] ?? '',
          data['taskId'] ?? '',
        );
      } else if (event == 'approveAction') {
        final confirmed = data['confirmed'] == true;
        final goal = data['goal'] ?? '';
        // FIX BUG-7: Use debugPrint instead of print
        debugPrint('[MSA] User action approval: $confirmed for goal: $goal');
        _webController.runJavaScript(
          "if(window.onApprovalResult) window.onApprovalResult($confirmed, '$goal');"
        );
      } else if (event == 'openSettings') {
        _showSettingsDialog();
      }
    } catch (e) {
      // FIX BUG-7: Use debugPrint instead of print
      debugPrint('[MSA] Error parsing JS message: $e');
    }
  }

  // ── IP Settings Dialog ────────────────────────────────────────────────────
  // FIX BUG-1: Allow user to configure server IP from the app
  void _showSettingsDialog() {
    final controller = TextEditingController(text: _serverUrl);
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: const Color(0xFF0A1428),
        title: const Text(
          '⚙ MSA Server Settings',
          style: TextStyle(color: Color(0xFF00D4FF), fontSize: 16),
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Enter your PC\'s Wi-Fi IP address and port:',
              style: TextStyle(color: Color(0xFF94A3C8), fontSize: 13),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: controller,
              style: const TextStyle(color: Colors.white),
              decoration: InputDecoration(
                hintText: 'e.g. http://192.168.1.100:5000',
                hintStyle: const TextStyle(color: Color(0xFF4A6080)),
                filled: true,
                fillColor: const Color(0xFF050B18),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(8),
                  borderSide: const BorderSide(color: Color(0xFF00D4FF)),
                ),
                enabledBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(8),
                  borderSide: const BorderSide(color: Color(0xFF1A3050)),
                ),
                focusedBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(8),
                  borderSide: const BorderSide(color: Color(0xFF00D4FF)),
                ),
              ),
            ),
            const SizedBox(height: 8),
            const Text(
              '💡 Tip: For Android emulator use http://10.0.2.2:5000',
              style: TextStyle(color: Color(0xFF4A6080), fontSize: 11),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Cancel', style: TextStyle(color: Color(0xFF94A3C8))),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(
              backgroundColor: const Color(0xFF00D4FF),
              foregroundColor: Colors.black,
            ),
            onPressed: () async {
              final newUrl = controller.text.trim();
              if (newUrl.isEmpty) return;
              final prefs = await SharedPreferences.getInstance();
              await prefs.setString('msa_server_url', newUrl);
              setState(() => _serverUrl = newUrl);
              _reasoningClient.stop();
              _initClients();
              _webController.loadRequest(Uri.parse('$_serverUrl/app'));
              if (ctx.mounted) Navigator.pop(ctx);
            },
            child: const Text('Save & Connect'),
          ),
        ],
      ),
    );
  }

  @override
  void dispose() {
    _reasoningClient.stop();
    super.dispose();
  }

  // ── Build ─────────────────────────────────────────────────────────────────
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        backgroundColor: const Color(0xFF050B18),
        elevation: 0,
        title: const Text(
          'MSA AI AGENT',
          style: TextStyle(
            color: Color(0xFF00D4FF),
            fontWeight: FontWeight.bold,
            fontSize: 16,
            letterSpacing: 2,
          ),
        ),
        actions: [
          // FIX BUG-1: Settings button to configure server IP
          IconButton(
            icon: const Icon(Icons.settings, color: Color(0xFF94A3C8)),
            tooltip: 'Configure Server IP',
            onPressed: _showSettingsDialog,
          ),
          IconButton(
            icon: const Icon(Icons.refresh, color: Color(0xFF94A3C8)),
            tooltip: 'Reload',
            onPressed: () {
              _webController.loadRequest(Uri.parse('$_serverUrl/app'));
            },
          ),
        ],
      ),
      body: SafeArea(
        child: WebViewWidget(controller: _webController),
      ),
    );
  }
}
