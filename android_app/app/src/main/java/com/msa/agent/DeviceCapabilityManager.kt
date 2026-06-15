package com.msa.agent

import android.Manifest
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.PackageManager
import android.location.LocationManager
import android.net.ConnectivityManager
import android.net.NetworkCapabilities
import android.os.BatteryManager
import android.os.Environment
import android.os.StatFs
import androidx.core.content.ContextCompat
import org.json.JSONArray
import org.json.JSONObject

/**
 * DeviceCapabilityManager.kt
 * ===========================
 * Phase-2: Detects and packages Android device capabilities for the
 * MSA backend ReasoningEngine. Called once on startup and on demand.
 *
 * Capabilities reported:
 *   - Battery level %
 *   - WiFi / Mobile network status
 *   - GPS / Location enabled
 *   - Free + total storage (GB)
 *   - Installed apps (display names)
 *   - Granted runtime permissions
 */
class DeviceCapabilityManager(private val context: Context) {

    /**
     * Build and return the full device capability JSON payload.
     * Sent to POST /mobile/capabilities on the backend.
     */
    fun getCapabilities(): JSONObject {
        val payload = JSONObject()

        payload.put("battery",          getBatteryLevel())
        payload.put("wifi",             isWifiConnected())
        payload.put("mobile_data",      isMobileDataConnected())
        payload.put("location_enabled", isLocationEnabled())
        payload.put("storage_free_gb",  getFreeStorageGb())
        payload.put("storage_total_gb", getTotalStorageGb())
        payload.put("apps",             getInstalledApps())
        payload.put("permissions",      getGrantedPermissions())
        payload.put("device_id",        getDeviceId())

        return payload
    }

    // ── Battery ───────────────────────────────────────────────────────────────

    fun getBatteryLevel(): Int {
        val intentFilter = IntentFilter(Intent.ACTION_BATTERY_CHANGED)
        val batteryStatus = context.registerReceiver(null, intentFilter) ?: return -1
        val level  = batteryStatus.getIntExtra(BatteryManager.EXTRA_LEVEL, -1)
        val scale  = batteryStatus.getIntExtra(BatteryManager.EXTRA_SCALE, -1)
        return if (level >= 0 && scale > 0) (level * 100 / scale) else -1
    }

    fun isCharging(): Boolean {
        val intentFilter = IntentFilter(Intent.ACTION_BATTERY_CHANGED)
        val batteryStatus = context.registerReceiver(null, intentFilter) ?: return false
        val status = batteryStatus.getIntExtra(BatteryManager.EXTRA_STATUS, -1)
        return status == BatteryManager.BATTERY_STATUS_CHARGING ||
               status == BatteryManager.BATTERY_STATUS_FULL
    }

    // ── Network ───────────────────────────────────────────────────────────────

    fun isWifiConnected(): Boolean {
        val cm = context.getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
        val network = cm.activeNetwork ?: return false
        val caps    = cm.getNetworkCapabilities(network) ?: return false
        return caps.hasTransport(NetworkCapabilities.TRANSPORT_WIFI)
    }

    fun isMobileDataConnected(): Boolean {
        val cm = context.getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
        val network = cm.activeNetwork ?: return false
        val caps    = cm.getNetworkCapabilities(network) ?: return false
        return caps.hasTransport(NetworkCapabilities.TRANSPORT_CELLULAR)
    }

    fun isInternetAvailable(): Boolean = isWifiConnected() || isMobileDataConnected()

    // ── Location ──────────────────────────────────────────────────────────────

    fun isLocationEnabled(): Boolean {
        val lm = context.getSystemService(Context.LOCATION_SERVICE) as LocationManager
        return try {
            lm.isProviderEnabled(LocationManager.GPS_PROVIDER) ||
            lm.isProviderEnabled(LocationManager.NETWORK_PROVIDER)
        } catch (e: Exception) { false }
    }

    // ── Storage ───────────────────────────────────────────────────────────────

    fun getFreeStorageGb(): Double {
        return try {
            val stat = StatFs(Environment.getExternalStorageDirectory().path)
            val free = stat.availableBlocksLong * stat.blockSizeLong
            String.format("%.2f", free / (1024.0 * 1024 * 1024)).toDouble()
        } catch (e: Exception) { -1.0 }
    }

    fun getTotalStorageGb(): Double {
        return try {
            val stat  = StatFs(Environment.getExternalStorageDirectory().path)
            val total = stat.blockCountLong * stat.blockSizeLong
            String.format("%.2f", total / (1024.0 * 1024 * 1024)).toDouble()
        } catch (e: Exception) { -1.0 }
    }

    // ── Apps ──────────────────────────────────────────────────────────────────

    fun getInstalledApps(): JSONArray {
        val result = JSONArray()
        try {
            val pm   = context.packageManager
            val apps = pm.getInstalledApplications(PackageManager.GET_META_DATA)
            // Return only user-installed or well-known apps (skip system noise)
            val userApps = apps.filter { appInfo ->
                val isSystem = (appInfo.flags and android.content.pm.ApplicationInfo.FLAG_SYSTEM) != 0
                !isSystem || isKnownApp(appInfo.packageName)
            }
            userApps.take(80).forEach { appInfo ->
                try {
                    val label = pm.getApplicationLabel(appInfo).toString()
                    result.put(label)
                } catch (e: Exception) { /* skip */ }
            }
        } catch (e: Exception) { /* permission not granted */ }
        return result
    }

    private fun isKnownApp(pkg: String): Boolean {
        val known = listOf(
            "com.whatsapp", "com.google.android.youtube", "com.android.chrome",
            "com.facebook.katana", "com.instagram.android", "com.twitter.android",
            "com.google.android.gm", "com.google.android.maps",
            "com.spotify.music", "com.netflix.mediaclient",
            "com.google.android.apps.photos", "com.samsung.android.messaging",
        )
        return known.any { pkg.startsWith(it) }
    }

    // ── Permissions ───────────────────────────────────────────────────────────

    fun getGrantedPermissions(): JSONArray {
        val result   = JSONArray()
        val checkList = listOf(
            Manifest.permission.RECORD_AUDIO,
            Manifest.permission.ACCESS_FINE_LOCATION,
            Manifest.permission.READ_PHONE_STATE,
            Manifest.permission.SEND_SMS,
            Manifest.permission.CALL_PHONE,
            Manifest.permission.CAMERA,
            Manifest.permission.READ_CONTACTS,
        )
        for (perm in checkList) {
            val label = perm.substringAfterLast(".")
            if (ContextCompat.checkSelfPermission(context, perm) == PackageManager.PERMISSION_GRANTED) {
                result.put(label)
            }
        }
        return result
    }

    // ── Device ID ─────────────────────────────────────────────────────────────

    fun getDeviceId(): String {
        return try {
            android.provider.Settings.Secure.getString(
                context.contentResolver,
                android.provider.Settings.Secure.ANDROID_ID
            ) ?: "unknown"
        } catch (e: Exception) { "unknown" }
    }
}
