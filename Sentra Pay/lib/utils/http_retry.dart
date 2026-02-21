import 'dart:io';
import 'package:http/http.dart' as http;
import 'package:retry/retry.dart';

/// Retry options tuned for Render free-tier cold starts (~30 s wake-up).
const RetryOptions kColdStartRetry = RetryOptions(
  maxAttempts: 5,
  delayFactor: Duration(seconds: 2),
  maxDelay: Duration(seconds: 20),
  randomizationFactor: 0.25,
);

/// Retries an HTTP GET that may fail while the Render backend cold-starts.
Future<http.Response> getWithRetry(Uri uri, {Map<String, String>? headers}) =>
    kColdStartRetry.retry(
      () async {
        final res = await http
            .get(uri, headers: headers)
            .timeout(const Duration(seconds: 30));
        if (res.statusCode >= 500) {
          throw HttpException('Server error ${res.statusCode}', uri: uri);
        }
        return res;
      },
      retryIf: (e) =>
          e is SocketException ||
          e is HttpException ||
          e is http.ClientException,
    );

/// Retries an HTTP POST that may fail while the Render backend cold-starts.
Future<http.Response> postWithRetry(
  Uri uri, {
  Map<String, String>? headers,
  Object? body,
}) => kColdStartRetry.retry(
  () async {
    final res = await http
        .post(uri, headers: headers, body: body)
        .timeout(const Duration(seconds: 30));
    if (res.statusCode >= 500) {
      throw HttpException('Server error ${res.statusCode}', uri: uri);
    }
    return res;
  },
  retryIf: (e) =>
      e is SocketException || e is HttpException || e is http.ClientException,
);
