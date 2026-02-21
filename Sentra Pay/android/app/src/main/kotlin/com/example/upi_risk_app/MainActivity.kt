package com.example.upi_risk_app

import android.os.Bundle
import android.provider.Settings
import android.view.WindowManager
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

class MainActivity : FlutterActivity() {

    private val CHANNEL = "com.sentra.security"

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        // FLAG_SECURE: makes the screen appear black to any other app
        // (screenshots, screen recorders, accessibility services all see nothing)
        window.setFlags(
            WindowManager.LayoutParams.FLAG_SECURE,
            WindowManager.LayoutParams.FLAG_SECURE
        )
    }

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        MethodChannel(
            flutterEngine.dartExecutor.binaryMessenger,
            CHANNEL
        ).setMethodCallHandler { call, result ->
            when (call.method) {
                "checkOverlay" -> {
                    // Returns true if any app has SYSTEM_ALERT_WINDOW permission active
                    result.success(Settings.canDrawOverlays(this))
                }
                "checkAccessibility" -> {
                    result.success(isSuspiciousAccessibilityActive())
                }
                else -> result.notImplemented()
            }
        }
    }

    /**
     * Returns true if any non-system accessibility service is enabled.
     * Known safe system services (TalkBack, manufacturer assistants) are whitelisted.
     */
    private fun isSuspiciousAccessibilityActive(): Boolean {
        val enabled = Settings.Secure.getString(
            contentResolver,
            Settings.Secure.ENABLED_ACCESSIBILITY_SERVICES
        ) ?: return false

        if (enabled.isBlank()) return false

        val trustedPrefixes = listOf(
            "com.google.android.marvin.talkback",
            "com.google.android.accessibility",
            "com.android.talkback",
            "com.samsung.android.accessibility",
            "com.vivo.accessibility",
            "com.miui.accessibilityservice",
            "com.huawei.accessibility",
            "com.oppo.accessibility"
        )

        for (service in enabled.split(":")) {
            val pkg = service.split("/").firstOrNull()?.trim() ?: continue
            if (pkg.isEmpty()) continue
            if (trustedPrefixes.none { pkg.startsWith(it) }) {
                return true // Unknown app has accessibility access
            }
        }
        return false
    }
}
