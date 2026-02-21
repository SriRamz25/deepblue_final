import 'package:upi_risk_app/services/api_service.dart';

/// Phone-number based authentication backed by the FastAPI + PostgreSQL backend.
///
/// Replaces the previous Firestore implementation � no Firebase dependency.
/// All user data is persisted in the PostgreSQL `users` table via the backend.
class PhoneAuthService {
  //  Helpers

  /// Normalise any phone input to last-10-digits.
  String _normalise(String phone) {
    final digits = phone.replaceAll(RegExp(r'[^0-9]'), '');
    return digits.length >= 10 ? digits.substring(digits.length - 10) : digits;
  }

  //  Sign Up

  /// Creates a new user in PostgreSQL via POST /api/auth/signup.
  /// Returns `{'success': true, 'data': {...AuthResponse...}}` on success.
  Future<Map<String, dynamic>> signUp({
    required String phone,
    required String password,
    required String name,
    String? email,
    String? upiId,
  }) async {
    final phone10 = _normalise(phone);
    if (phone10.isEmpty) {
      return {'success': false, 'error': 'Invalid phone number'};
    }

    try {
      final data = await ApiService.signup(
        name,
        phone10,
        password,
        email: email,
        upiId: upiId,
      );

      if (data != null) {
        return {'success': true, 'data': data};
      }
      return {
        'success': false,
        'error': 'Phone number may already be registered.',
      };
    } catch (e) {
      return {'success': false, 'error': 'Signup failed: $e'};
    }
  }

  //  Sign In

  /// Authenticates via POST /api/auth/login (PostgreSQL lookup + bcrypt verify).
  /// Returns `{'success': true, 'data': {...AuthResponse...}}` on success.
  Future<Map<String, dynamic>> signIn({
    required String phone,
    required String password,
  }) async {
    final phone10 = _normalise(phone);
    if (phone10.isEmpty) {
      return {'success': false, 'error': 'Invalid phone number'};
    }

    try {
      final data = await ApiService.login(phone10, password);

      if (data != null) {
        return {'success': true, 'data': data};
      }
      return {'success': false, 'error': 'Incorrect phone number or password.'};
    } catch (e) {
      return {'success': false, 'error': 'Login failed: $e'};
    }
  }
}
