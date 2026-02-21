import 'package:flutter/material.dart';
import 'package:google_sign_in/google_sign_in.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'user_profile.dart';
import '../services/api_service.dart';
import '../services/firebase_auth_service.dart';
import 'package:upi_risk_app/services/phone_auth_service.dart';

class AuthProvider extends ChangeNotifier {
  UserProfile? _currentUser;
  String? _token; // Added token management
  bool _isAuthenticated = false;
  bool _isBiometricEnabled = true;
  String? _errorMessage;
  bool _isLoading = false;

  // Firebase service
  final FirebaseAuthService _firebaseAuth = FirebaseAuthService();

  // Phone-number Firestore auth (no fake email)
  final PhoneAuthService _phoneAuth = PhoneAuthService();

  // Google Sign-In & Secure Storage
  final GoogleSignIn _googleSignIn = GoogleSignIn(scopes: ['email', 'profile']);
  final _storage = const FlutterSecureStorage();

  UserProfile? get currentUser => _currentUser;
  String? get token => _token;
  bool get isAuthenticated => _isAuthenticated;
  bool get isBiometricEnabled => _isBiometricEnabled;
  String? get errorMessage => _errorMessage;
  bool get isLoading => _isLoading;
  String? get userId => _firebaseAuth.currentUserId;

  /// Sign In with Google
  Future<bool> signInWithGoogle() async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      // 1. Sign in with Google
      final GoogleSignInAccount? googleUser = await _googleSignIn.signIn();
      if (googleUser == null) {
        _isLoading = false;
        notifyListeners();
        return false; // User cancelled
      }

      // 2. Get authentication details
      final GoogleSignInAuthentication googleAuth =
          await googleUser.authentication;
      final String? idToken = googleAuth.idToken;

      if (idToken == null) {
        _errorMessage = "Could not retrieve Google ID Token";
        _isLoading = false;
        notifyListeners();
        return false;
      }

      // 3. Send idToken to our Backend
      final authData = await ApiService.googleLogin(idToken);

      if (authData != null) {
        // 4. Store JWT securely
        _token = authData['token'];
        await _storage.write(key: 'jwt_token', value: _token);

        // 5. Update user profile
        _currentUser = UserProfile.fromJson(authData);
        _isAuthenticated = true;
        _isLoading = false;
        notifyListeners();
        return true;
      } else {
        _errorMessage = "Backend authentication failed";
        _isLoading = false;
        notifyListeners();
        return false;
      }
    } catch (e) {
      print('Google Sign-In Error: $e');
      _errorMessage = "Google login failed: $e";
      _isLoading = false;
      notifyListeners();
      return false;
    }
  }

  void toggleBiometric(bool value) {
    _isBiometricEnabled = value;
    notifyListeners();
  }

  Future<bool> authenticateBiometric() async {
    // Simulate biometric delay
    await Future.delayed(const Duration(milliseconds: 1500));

    // Auto-login with demo account (now using Firebase in background)
    if (_users.containsKey('gopal@gmail.com')) {
      final demoUser = _users['gopal@gmail.com']!;
      _currentUser = UserProfile.fromJson(demoUser['profile']);
      _token = "demo-token"; // Set demo token
      _isAuthenticated = true;
      notifyListeners();
      return true;
    }
    return false;
  }

  // Simulated user database (for demo purposes)
  final Map<String, Map<String, dynamic>> _users = {
    'gopal@gmail.com': {
      'password': 'Gopal789',
      'profile': {
        'userId': 'UID-DEMO-001',
        'securityId': 'USER-12345',
        'fullName': 'Gopal',
        'email': 'gopal@gmail.com',
        'mobile': '9876543210',
        'profilePhotoUrl': null,
        'createdAt': null,
        'transactionCount': 5,
        'trustScore': 98.0,
        'deviceId': 'DEV-SHIELD-001X',
        'loginCount': 12,
        'commonVPAs': ['merchant@upi', 'friend@okaxis'],
      },
    },
  };

  // Phone+PIN demo mapping
  final Map<String, Map<String, dynamic>> _phoneUsers = {
    '9876543210': {
      'pin': '1234',
      'profile': {
        'userId': 'UID-DEMO-001',
        'securityId': 'USER-12345',
        'fullName': 'Gopal',
        'email': 'gopal@gmail.com',
        'mobile': '9876543210',
        'profilePhotoUrl': null,
        'createdAt': null,
        'transactionCount': 5,
        'trustScore': 98.0,
        'deviceId': 'DEV-SHIELD-001X',
        'loginCount': 12,
        'commonVPAs': ['merchant@upi', 'friend@okaxis'],
      },
    },
  };

  /// Sign in with Firebase
  Future<bool> signIn(String emailOrPhone, String password) async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    // Determine if the input is a phone number (digits only / +91xxxx format)
    final digitsOnly = emailOrPhone.replaceAll(RegExp(r'[^0-9]'), '');
    final isPhone = digitsOnly.length >= 10 && !emailOrPhone.contains('@');

    try {
      // ── Phone login → PostgreSQL backend ─────────────────────────────────
      if (isPhone) {
        final result = await _phoneAuth
            .signIn(phone: emailOrPhone, password: password)
            .timeout(
              const Duration(seconds: 10),
              onTimeout: () => {
                'success': false,
                'error': 'Connection timed out. Is the backend running?',
              },
            );

        if (result['success'] == true) {
          final data = result['data'] as Map<String, dynamic>;
          _currentUser = UserProfile.fromJson(data);
          _token = data['token'];
          _isAuthenticated = true;
          _isLoading = false;
          notifyListeners();
          return true;
        }

        // Phone auth failed — show the actual error from backend
        _errorMessage =
            result['error'] ?? 'Invalid credentials. Please try again.';
        _isLoading = false;
        notifyListeners();
        return false;
      }

      // ── Email login → Firebase Auth (Google Sign-In users) ───────────────
      print('AuthProvider: Starting Firebase email signin for $emailOrPhone');
      try {
        final result = await _firebaseAuth
            .signIn(email: emailOrPhone, password: password)
            .timeout(
              const Duration(seconds: 5),
              onTimeout: () {
                print('AuthProvider: Firebase signin timed out');
                return {'success': false, 'error': 'timeout'};
              },
            );

        print(
          'AuthProvider: Firebase result - success: ${result['success']}, error: ${result['error']}',
        );

        if (result['success']) {
          // Get user profile from Firestore
          var profile = await _firebaseAuth
              .getUserProfile(result['userId'])
              .timeout(const Duration(seconds: 3), onTimeout: () => null);

          if (profile != null) {
            // Convert Firestore Timestamp to DateTime
            DateTime createdAt;
            try {
              if (profile['createdAt'] != null) {
                createdAt = profile['createdAt'].toDate();
              } else {
                createdAt = DateTime.now();
              }
            } catch (e) {
              print('Error parsing createdAt: $e');
              createdAt = DateTime.now();
            }

            _currentUser = UserProfile(
              userId: profile['userId'] ?? result['userId'],
              securityId: (profile['userId'] ?? result['userId']).substring(
                0,
                12,
              ),
              fullName: profile['name'] ?? 'User',
              email: profile['email'] ?? emailOrPhone,
              mobile: profile['phone'],
              profilePhotoUrl: null,
              createdAt: createdAt,
              transactionCount: profile['totalTransactions'] ?? 0,
              trustScore: (profile['trustScore'] ?? 100).toDouble(),
              deviceId: profile['deviceId'] ?? '',
              loginCount: profile['loginCount'] ?? 1,
              commonVPAs: List<String>.from(profile['commonVPAs'] ?? []),
            );

            _isAuthenticated = true;
            _isLoading = false;
            notifyListeners();
            return true;
          } else {
            // Profile not found in Firestore, but auth succeeded
            // Create a basic profile from auth result
            print('Profile not found in Firestore, creating basic profile');
            _currentUser = UserProfile(
              userId: result['userId'],
              securityId: result['userId'].substring(0, 12),
              fullName: emailOrPhone.split('@')[0], // Use email prefix as name
              email: emailOrPhone,
              mobile: null,
              profilePhotoUrl: null,
              createdAt: DateTime.now(),
              transactionCount: 0,
              trustScore: 100.0,
              deviceId: '',
              loginCount: 1,
              commonVPAs: [],
            );

            _isAuthenticated = true;
            _isLoading = false;
            notifyListeners();
            return true;
          }
        }
      } catch (e) {
        print('Firebase login threw an exception. Falling back to API... $e');
      }

      // Fallback to legacy API service (with timeout)
      final authData = await ApiService.login(
        emailOrPhone,
        password,
      ).timeout(const Duration(seconds: 2), onTimeout: () => null);

      if (authData != null) {
        _currentUser = UserProfile.fromJson(authData);
        _token = authData['token'];
        _isAuthenticated = true;
        _isLoading = false;
        notifyListeners();
        return true;
      }

      // Check phone+PIN demo users first
      if (_phoneUsers.containsKey(emailOrPhone)) {
        final userData = _phoneUsers[emailOrPhone]!;
        if (userData['pin'] == password) {
          _currentUser = UserProfile.fromJson(userData['profile']);
          _token = "demo-token";
          _isAuthenticated = true;
          _isLoading = false;
          notifyListeners();
          return true;
        }
      }

      // Fallback: email+password demo users
      if (_users.containsKey(emailOrPhone)) {
        final userData = _users[emailOrPhone]!;
        if (userData['password'] == password) {
          _currentUser = UserProfile.fromJson(userData['profile']);
          _token = "demo-token";
          _isAuthenticated = true;
          _isLoading = false;
          notifyListeners();
          return true;
        }
      }

      _errorMessage = 'Invalid credentials. Please try again.';
      _isLoading = false;
      notifyListeners();
      return false;
    } catch (e) {
      print('Login error: $e');
      // Fallback: check phone+PIN demo
      if (_phoneUsers.containsKey(emailOrPhone)) {
        final userData = _phoneUsers[emailOrPhone]!;
        if (userData['pin'] == password) {
          _currentUser = UserProfile.fromJson(userData['profile']);
          _token = "demo-token";
          _isAuthenticated = true;
          _isLoading = false;
          notifyListeners();
          return true;
        }
      }
      // Or check email+password demo
      if (_users.containsKey(emailOrPhone)) {
        final userData = _users[emailOrPhone]!;
        if (userData['password'] == password) {
          _currentUser = UserProfile.fromJson(userData['profile']);
          _token = "demo-token";
          _isAuthenticated = true;
          _isLoading = false;
          notifyListeners();
          return true;
        }
      }

      _errorMessage = 'Invalid credentials. Please try again.';
      _isLoading = false;
      notifyListeners();
      return false;
    }
  }

  /// Sign up with Firebase
  Future<bool> signUp({
    required String fullName,
    String? email,
    required String mobile,
    required String password,
    String? profilePhotoUrl,
    String? upiId,
  }) async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      try {
        // Create account with Firebase (with timeout)
        // Normalise mobile → last-10-digits for the Firestore document ID
        final mobileDigits = mobile.replaceAll(RegExp(r'[^0-9]'), '');
        final mobile10 = mobileDigits.length >= 10
            ? mobileDigits.substring(mobileDigits.length - 10)
            : mobileDigits;

        // Use PhoneAuthService — stores via PostgreSQL backend, no Firebase
        final result = await _phoneAuth
            .signUp(
              phone: mobile10,
              password: password,
              name: fullName.isEmpty ? 'Sentra User' : fullName,
              email: email,
              upiId: upiId,
            )
            .timeout(
              const Duration(seconds: 10),
              onTimeout: () => {
                'success': false,
                'error': 'Connection timed out. Is the backend running?',
              },
            );

        if (result['success'] == true) {
          final data = result['data'] as Map<String, dynamic>;
          _currentUser = UserProfile.fromJson(data);
          _token = data['token'];
          _isAuthenticated = true;
          _isLoading = false;
          notifyListeners();
          return true;
        } else {
          _errorMessage = result['error'] ?? 'Signup failed.';
          _isLoading = false;
          notifyListeners();
          return false;
        }
      } catch (e) {
        print('PhoneAuthService signup error: $e');
        _errorMessage = 'Signup failed. Please try again.';
        _isLoading = false;
        notifyListeners();
        return false;
      }

      // Fallback to legacy API (with timeout)
      final authData = await ApiService.signup(
        fullName.isEmpty ? 'Sentra User' : fullName,
        mobile,
        password,
        email: email,
        upiId: upiId,
      ).timeout(const Duration(seconds: 2), onTimeout: () => null);

      if (authData != null) {
        _currentUser = UserProfile.fromJson(authData);
        _token = authData['token'];
        _isAuthenticated = true;
        _isLoading = false;
        notifyListeners();
        return true;
      }

      // If backend API fails too, fall back to Demo mode
      final newUserId = 'UID-${DateTime.now().millisecondsSinceEpoch}';
      _currentUser = UserProfile(
        userId: newUserId,
        securityId: newUserId.substring(0, 12),
        fullName: fullName.isEmpty ? 'Sentra User' : fullName,
        email: email ?? '',
        mobile: mobile,
        profilePhotoUrl: profilePhotoUrl,
        createdAt: DateTime.now(),
        transactionCount: 0,
        trustScore: 100.0,
        deviceId: 'DEV-DEMO-${DateTime.now().millisecondsSinceEpoch}',
        loginCount: 1,
        commonVPAs: [],
      );

      _token = "demo-token";
      _isAuthenticated = true;
      _isLoading = false;
      notifyListeners();
      return true;
    } catch (e) {
      // If all else fails, create demo account
      final newUserId = 'UID-${DateTime.now().millisecondsSinceEpoch}';
      _currentUser = UserProfile(
        userId: newUserId,
        securityId: newUserId.substring(0, 12),
        fullName: fullName.isEmpty ? 'Sentra User' : fullName,
        email: email ?? '',
        mobile: mobile,
        profilePhotoUrl: profilePhotoUrl,
        createdAt: DateTime.now(),
        transactionCount: 0,
        trustScore: 100.0,
        deviceId: 'DEV-DEMO-${DateTime.now().millisecondsSinceEpoch}',
        loginCount: 1,
        commonVPAs: [],
      );

      _isAuthenticated = true;
      _isLoading = false;
      notifyListeners();
      return true;
    }
  }

  Future<void> updateProfile({
    String? fullName,
    String? email,
    String? mobile,
    String? profilePhotoUrl,
    String? upiId,
  }) async {
    if (_currentUser == null) return;

    await Future.delayed(const Duration(milliseconds: 200));

    // Persist UPI ID to PostgreSQL backend
    if (upiId != null && upiId.isNotEmpty && _token != null) {
      await ApiService.updateUpi(upiId, _token!);
    }

    _currentUser = _currentUser!.copyWith(
      fullName: fullName,
      email: email,
      mobile: mobile,
      profilePhotoUrl: profilePhotoUrl,
      upiId: upiId,
    );

    notifyListeners();
  }

  Future<void> signOut() async {
    await _firebaseAuth.signOut();
    _currentUser = null;
    _isAuthenticated = false;
    notifyListeners();
  }

  void updateTransactionStats(int count, double trustScore) {
    if (_currentUser == null) return;

    _currentUser = _currentUser!.copyWith(
      transactionCount: count,
      trustScore: trustScore,
    );
    notifyListeners();
  }

  /// Refresh user profile from Firebase
  Future<void> refreshProfile() async {
    if (_firebaseAuth.currentUserId == null) return;

    var profile = await _firebaseAuth.getUserProfile(
      _firebaseAuth.currentUserId!,
    );
    if (profile != null) {
      _currentUser = _currentUser?.copyWith(
        transactionCount:
            profile['totalTransactions'] ?? _currentUser?.transactionCount,
        trustScore: (profile['trustScore'] ?? _currentUser?.trustScore)
            .toDouble(),
      );
      notifyListeners();
    }
  }
}
