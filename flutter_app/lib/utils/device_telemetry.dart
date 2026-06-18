import 'dart:io';
import 'package:battery_plus/battery_plus.dart';
import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:device_info_plus/device_info_plus.dart';

class DeviceTelemetry {
  final Battery _battery = Battery();
  final DeviceInfoPlugin _deviceInfo = DeviceInfoPlugin();

  Future<int> getBatteryLevel() async {
    try {
      return await _battery.batteryLevel;
    } catch (_) {
      return -1;
    }
  }

  Future<bool> isCharging() async {
    try {
      final state = await _battery.batteryState;
      return state == BatteryState.charging || state == BatteryState.full;
    } catch (_) {
      return false;
    }
  }

  Future<bool> isWifiConnected() async {
    try {
      final result = await Connectivity().checkConnectivity();
      return result == ConnectivityResult.wifi;
    } catch (_) {
      return false;
    }
  }

  Future<bool> isMobileDataConnected() async {
    try {
      final result = await Connectivity().checkConnectivity();
      return result == ConnectivityResult.mobile;
    } catch (_) {
      return false;
    }
  }

  Future<String> getDeviceId() async {
    try {
      if (Platform.isAndroid) {
        final info = await _deviceInfo.androidInfo;
        return info.id;
      } else if (Platform.isIOS) {
        final info = await _deviceInfo.iosInfo;
        return info.identifierForVendor ?? 'unknown_ios';
      }
      return 'unknown_desktop';
    } catch (_) {
      return 'unknown_device';
    }
  }

  Future<Map<String, dynamic>> getCapabilities() async {
    final battery = await getBatteryLevel();
    final wifi = await isWifiConnected();
    final mobileData = await isMobileDataConnected();
    final devId = await getDeviceId();

    return {
      'battery': battery,
      'wifi': wifi,
      'mobile_data': mobileData,
      'location_enabled': true, // Simplified placeholder for GeoLocation API
      'storage_free_gb': 12.5, // Mock data or path_provider check
      'storage_total_gb': 64.0,
      'apps': ['com.whatsapp', 'com.google.android.youtube', 'com.android.chrome'], // Mock user apps
      'permissions': ['RECORD_AUDIO', 'ACCESS_FINE_LOCATION', 'CAMERA'],
      'device_id': devId,
    };
  }
}
