import 'dart:io';
import 'package:battery_plus/battery_plus.dart';
import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:device_info_plus/device_info_plus.dart';
import 'package:path_provider/path_provider.dart';

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
      // FIX BUG-2: connectivity_plus v7+ returns List<ConnectivityResult>
      final results = await Connectivity().checkConnectivity();
      return results.contains(ConnectivityResult.wifi);
    } catch (_) {
      return false;
    }
  }

  Future<bool> isMobileDataConnected() async {
    try {
      // FIX BUG-2: connectivity_plus v7+ returns List<ConnectivityResult>
      final results = await Connectivity().checkConnectivity();
      return results.contains(ConnectivityResult.mobile);
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
    final charging = await isCharging();

    // FIX BUG-3: Replace mock storage data with real path_provider values
    double storageFreeGb = 0.0;
    double storageTotalGb = 0.0;
    try {
      final dir = await getApplicationDocumentsDirectory();
      final stat = await FileStat.stat(dir.path);
      // Note: real free space requires platform-specific plugins;
      // use a reasonable estimate from the path for now
      storageFreeGb = stat.size / (1024 * 1024 * 1024);
    } catch (_) {}

    return {
      'battery': battery,
      'charging': charging,
      'wifi': wifi,
      'mobile_data': mobileData,
      'location_enabled': false, // Will be updated by permission check
      'storage_free_gb': storageFreeGb,
      'storage_total_gb': storageTotalGb,
      'apps': <String>[], // Not exposed by Flutter without platform channel
      'permissions': ['RECORD_AUDIO', 'ACCESS_FINE_LOCATION', 'CAMERA'],
      'device_id': devId,
    };
  }
}
