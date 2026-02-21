import 'dart:convert';
import 'package:http/http.dart' as http;
import 'firebase_auth_service.dart';
import '../config/api_config.dart';

/// Backend API Service
/// Handles communication with your FastAPI backend for ML-based fraud detection
class BackendApiService {
  static String get baseUrl => ApiConfig.baseUrl;

  final FirebaseAuthService _authService = FirebaseAuthService();

  /// Get authorization headers with Firebase ID token
  Future<Map<String, String>> _getHeaders() async {
    String? token = await _authService.getIdToken();
    return {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      if (token != null) 'Authorization': 'Bearer $token',
    };
  }

  // ========== AUTHENTICATION ENDPOINTS ==========

  /// Register user with backend (after Firebase signup)
  Future<Map<String, dynamic>> registerUserWithBackend({
    required String firebaseUserId,
    required String email,
    required String name,
    required String phone,
  }) async {
    try {
      final headers = await _getHeaders();
      final response = await http
          .post(
            Uri.parse('$baseUrl/api/auth/signup'),
            headers: headers,
            body: jsonEncode({
              'firebase_user_id': firebaseUserId,
              'email': email,
              'name': name,
              'phone': phone,
            }),
          )
          .timeout(const Duration(seconds: 10));

      if (response.statusCode == 200 || response.statusCode == 201) {
        return {'success': true, 'data': jsonDecode(response.body)};
      } else {
        return {
          'success': false,
          'error': 'Backend registration failed: ${response.body}',
        };
      }
    } catch (e) {
      print('Error registering with backend: $e');
      return {'success': false, 'error': 'Network error: ${e.toString()}'};
    }
  }

  // ========== FRAUD DETECTION ENDPOINTS ==========

  /// Analyze transaction risk using ML backend
  Future<Map<String, dynamic>> analyzeTransaction({
    required String userId,
    required String recipientVPA,
    required double amount,
    required String deviceId,
    Map<String, dynamic>? userProfile,
  }) async {
    try {
      final headers = await _getHeaders();

      // Fix: Backend expects 'receiver' not 'recipient_vpa'
      // Backend fetches user profile internally, no need to send it
      final requestBody = {
        'amount': amount,
        'receiver': recipientVPA,
        'note': 'Transaction analysis',
        'device_id': deviceId,
      };

      print('Sending transaction analysis request to backend: $requestBody');
      final response = await http
          .post(
            Uri.parse('$baseUrl/api/payment/intent'),
            headers: headers,
            body: jsonEncode(requestBody),
          )
          .timeout(const Duration(seconds: 15));

      if (response.statusCode == 200) {
        var data = jsonDecode(response.body);

        // Map backend response to frontend expected format
        List<String> factors = [];
        if (data['risk_factors'] != null) {
          for (var f in data['risk_factors']) {
            if (f is Map) {
              factors.add("${f['factor']} (${f['severity']})");
            } else {
              factors.add(f.toString());
            }
          }
        }

        return {
          'success': true,
          'riskScore': data['risk_score'] ?? 0.0, // 0.0 - 1.0 (normalized)
          'riskLevel': data['risk_level'] ?? 'UNKNOWN',
          'decision':
              data['action'] ?? 'BLOCK', // 'action' mapped to 'decision'
          'riskBreakdown': data['risk_breakdown'] ?? {},
          'analysisFactors': factors,
          'mlPrediction': data['risk_percentage'], // Use percentage for display
          'backendUsed': true,
          'transactionId': data['transaction_id'],
        };
      } else {
        print(
          'Backend returned error: ${response.statusCode} - ${response.body}',
        );
        return {
          'success': false,
          'error': 'Backend analysis failed: ${response.body}',
          'backendUsed': false,
        };
      }
    } catch (e) {
      print('Error analyzing transaction with backend: $e');
      return {
        'success': false,
        'error': 'Network error: ${e.toString()}',
        'backendUsed': false,
      };
    }
  }

  /// Verify OTP for high-risk transaction
  Future<Map<String, dynamic>> verifyOTP({
    required String transactionId,
    required String otp,
  }) async {
    try {
      final headers = await _getHeaders();
      final response = await http
          .post(
            Uri.parse('$baseUrl/api/payment/verify-otp'),
            headers: headers,
            body: jsonEncode({'transaction_id': transactionId, 'otp': otp}),
          )
          .timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        var data = jsonDecode(response.body);
        return {
          'success': true,
          'verified': data['verified'] ?? false,
          'message': data['message'],
        };
      } else {
        return {'success': false, 'error': 'OTP verification failed'};
      }
    } catch (e) {
      return {'success': false, 'error': 'Network error: ${e.toString()}'};
    }
  }

  // ========== USER PROFILE ENDPOINTS ==========

  /// Get user profile from backend
  Future<Map<String, dynamic>> getUserProfile(String userId) async {
    try {
      final headers = await _getHeaders();
      final response = await http
          .get(Uri.parse('$baseUrl/api/user/$userId/profile'), headers: headers)
          .timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        return {'success': true, 'data': jsonDecode(response.body)};
      } else {
        return {'success': false, 'error': 'Failed to get user profile'};
      }
    } catch (e) {
      return {'success': false, 'error': 'Network error: ${e.toString()}'};
    }
  }

  /// Update user profile
  Future<Map<String, dynamic>> updateUserProfile({
    required String userId,
    required Map<String, dynamic> updates,
  }) async {
    try {
      final headers = await _getHeaders();
      final response = await http
          .put(
            Uri.parse('$baseUrl/api/user/$userId/profile'),
            headers: headers,
            body: jsonEncode(updates),
          )
          .timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        return {'success': true, 'data': jsonDecode(response.body)};
      } else {
        return {'success': false, 'error': 'Failed to update user profile'};
      }
    } catch (e) {
      return {'success': false, 'error': 'Network error: ${e.toString()}'};
    }
  }

  // ========== ANALYTICS ENDPOINTS ==========

  /// Get user transaction history from backend
  Future<Map<String, dynamic>> getTransactionHistory(String userId) async {
    try {
      final headers = await _getHeaders();
      final response = await http
          .get(
            Uri.parse('$baseUrl/api/user/$userId/transactions'),
            headers: headers,
          )
          .timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        return {'success': true, 'transactions': jsonDecode(response.body)};
      } else {
        return {'success': false, 'error': 'Failed to get transaction history'};
      }
    } catch (e) {
      return {'success': false, 'error': 'Network error: ${e.toString()}'};
    }
  }

  /// Get risk analytics
  Future<Map<String, dynamic>> getRiskAnalytics(String userId) async {
    try {
      final headers = await _getHeaders();
      final response = await http
          .get(
            Uri.parse('$baseUrl/api/analytics/risk/$userId'),
            headers: headers,
          )
          .timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        return {'success': true, 'analytics': jsonDecode(response.body)};
      } else {
        return {'success': false, 'error': 'Failed to get analytics'};
      }
    } catch (e) {
      return {'success': false, 'error': 'Network error: ${e.toString()}'};
    }
  }

  // ========== HEALTH CHECK ==========

  /// Check if backend is available
  Future<bool> isBackendAvailable() async {
    try {
      final response = await http
          .get(Uri.parse('$baseUrl/health'))
          .timeout(const Duration(seconds: 5));

      return response.statusCode == 200;
    } catch (e) {
      print('Backend not available: $e');
      return false;
    }
  }

  /// Get backend status
  Future<Map<String, dynamic>> getBackendStatus() async {
    try {
      final response = await http
          .get(Uri.parse('$baseUrl/health'))
          .timeout(const Duration(seconds: 5));

      if (response.statusCode == 200) {
        return {'available': true, 'status': jsonDecode(response.body)};
      } else {
        return {
          'available': false,
          'error': 'Backend returned ${response.statusCode}',
        };
      }
    } catch (e) {
      return {'available': false, 'error': e.toString()};
    }
  }
}
