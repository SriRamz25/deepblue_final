import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';

/// Detects runtime threats before payments are processed.
/// Currently checks:
///   1. Overlay Attack — another app has SYSTEM_ALERT_WINDOW permission active
///   2. Accessibility Abuse — an unknown accessibility service is running
///
/// Both checks are Android-only. On web / iOS / desktop they return false (safe).
class SecurityService {
  static const _channel = MethodChannel('com.sentra.security');

  /// Returns true if an overlay threat is detected.
  static Future<bool> isOverlayActive() async {
    if (defaultTargetPlatform != TargetPlatform.android || kIsWeb) return false;
    try {
      final result = await _channel.invokeMethod<bool>('checkOverlay');
      return result ?? false;
    } on PlatformException {
      return false;
    }
  }

  /// Returns true if a suspicious (non-system) accessibility service is running.
  static Future<bool> isSuspiciousAccessibilityActive() async {
    if (defaultTargetPlatform != TargetPlatform.android || kIsWeb) return false;
    try {
      final result = await _channel.invokeMethod<bool>('checkAccessibility');
      return result ?? false;
    } on PlatformException {
      return false;
    }
  }

  /// Runs both checks and returns the first threat found, or null if all clear.
  /// Returns a [SecurityThreat] describing which attack type was detected.
  static Future<SecurityThreat?> runPrePaymentChecks() async {
    if (await isOverlayActive()) return SecurityThreat.overlay;
    if (await isSuspiciousAccessibilityActive())
      return SecurityThreat.accessibility;
    return null;
  }
}

enum SecurityThreat {
  /// SYSTEM_ALERT_WINDOW — fake screen on top of your app
  overlay,

  /// Unknown accessibility service silently reading screen data
  accessibility,
}

extension SecurityThreatUI on SecurityThreat {
  String get title {
    switch (this) {
      case SecurityThreat.overlay:
        return 'Overlay Attack Detected';
      case SecurityThreat.accessibility:
        return 'Screen Reading Risk Detected';
    }
  }

  String get description {
    switch (this) {
      case SecurityThreat.overlay:
        return 'Another app is displaying a screen over Sentra Pay. '
            'This is a known method used to steal UPI PINs.\n\n'
            'Close all other apps and try again.';
      case SecurityThreat.accessibility:
        return 'An unknown background service has permission to read '
            'your screen. It can silently capture your UPI ID, amount, '
            'and receiver details.\n\n'
            'Go to Settings → Accessibility and disable unused services, '
            'then try again.';
    }
  }

  String get icon {
    switch (this) {
      case SecurityThreat.overlay:
        return '🛡️';
      case SecurityThreat.accessibility:
        return '👁️';
    }
  }
}
