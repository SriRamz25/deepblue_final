/// API configuration — set via --dart-define at build time.
///
/// Dev (Chrome/emulator): no flag needed, uses localhost defaults
/// Production build:
///   flutter build web --dart-define=API_URL=https://sentra-pay-backend.onrender.com
class ApiConfig {
  /// Base URL of the FastAPI backend (no trailing slash).
  static const String baseUrl = String.fromEnvironment(
    'API_URL',
    defaultValue: 'http://localhost:8000',
  );

  /// Timeout for API calls in milliseconds.
  static const int timeoutMs = 30000;

  /// Max retry attempts for cold-start handling (Render free tier).
  static const int maxRetries = 3;
}
