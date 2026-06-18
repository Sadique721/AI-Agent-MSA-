import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:webview_flutter/webview_flutter.dart';
import 'package:permission_handler/permission_handler.dart';
import 'services/reasoning_client.dart';
import 'services/validation_service.dart';
import 'utils/device_telemetry.dart';

void main() {
  runApp(const MsaAiAgentApp());
}

class MsaAiAgentApp extends StatelessWidget {
  const MsaAiAgentApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'MSA AI AGENT',
      theme: ThemeData.dark().copyWith(
        primaryColor: Colors.indigo,
        scaffoldBackgroundColor: const Color(0xFF050B18),
      ),
      home: const MsaHome(),
    );
  }
}

class MsaHome extends StatefulWidget {
  const MsaHome({super.key});

  @override
  State<MsaHome> createState() => _MsaHomeState();
}

class _MsaHomeState extends State<MsaHome> {
  late final WebViewController _webController;
  final String _serverUrl = 'http://10.0.2.2:5000'; // Default emulator loopback
  late final ReasoningClient _reasoningClient;
  late final ValidationService _validationService;
  final DeviceTelemetry _telemetry = DeviceTelemetry();

  @override
  void initState() {
    super.initState();
    _reasoningClient = ReasoningClient(serverUrl: _serverUrl);
    _validationService = ValidationService(serverUrl: _serverUrl);

    _requestPermissions();

    _webController = WebViewController()
      ..setJavaScriptMode(JavaScriptMode.unrestricted)
      ..setNavigationDelegate(
        NavigationDelegate(
          onPageFinished: (String url) {
            _injectJsBridges();
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

  void _injectJsBridges() {
    final js = '''
      (function() {
        window.MsaBridge = {
          getServerUrl: function() { return '$_serverUrl'; },
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
        print('User action approval: $confirmed for goal: $goal');
        _webController.runJavaScript(
          "if(window.onApprovalResult) window.onApprovalResult($confirmed, '$goal');"
        );
      }
    } catch (e) {
      print('Error parsing JS message: $e');
    }
  }

  @override
  void dispose() {
    _reasoningClient.stop();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: WebViewWidget(controller: _webController),
      ),
    );
  }
}
