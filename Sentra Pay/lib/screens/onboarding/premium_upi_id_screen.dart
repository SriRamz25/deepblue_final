import 'package:flutter/material.dart';
import 'premium_styles.dart';
import 'package:provider/provider.dart';
import '../../models/auth_provider.dart';
import '../signin_screen.dart';

class PremiumUpiIdScreen extends StatefulWidget {
  final String phone;
  final String password;
  const PremiumUpiIdScreen({
    super.key,
    required this.phone,
    required this.password,
  });

  @override
  State<PremiumUpiIdScreen> createState() => _PremiumUpiIdScreenState();
}

class _PremiumUpiIdScreenState extends State<PremiumUpiIdScreen>
    with SingleTickerProviderStateMixin {
  final TextEditingController _upiController = TextEditingController();
  bool _isLoading = false;
  String? _errorMessage;

  late AnimationController _fadeController;
  late Animation<double> _fadeAnimation;

  @override
  void initState() {
    super.initState();
    _fadeController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 600),
    );
    _fadeAnimation =
        CurvedAnimation(parent: _fadeController, curve: Curves.easeOut);
    _fadeController.forward();
  }

  @override
  void dispose() {
    _fadeController.dispose();
    _upiController.dispose();
    super.dispose();
  }

  Future<void> _createAccount() async {
    final upi = _upiController.text.trim();
    if (upi.isEmpty) {
      setState(() => _errorMessage = 'Please enter your UPI ID');
      return;
    }

    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    final authProvider = Provider.of<AuthProvider>(context, listen: false);

    final success = await authProvider.signUp(
      fullName: 'Sentra User',
      mobile: widget.phone,
      password: widget.password,
      upiId: upi,
    );

    if (success && mounted) {
      // Update UPI ID on profile
      await authProvider.updateProfile(upiId: upi);

      // Sign out so user can sign in fresh
      await authProvider.signOut();

      if (mounted) {
        // Show success snackbar
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: const Text('Account created! Please sign in.'),
            backgroundColor: Colors.green.shade600,
            behavior: SnackBarBehavior.floating,
            shape:
                RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          ),
        );

        // Navigate to sign in, clearing all previous routes
        Navigator.of(context).pushAndRemoveUntil(
          MaterialPageRoute(builder: (_) => const SignInScreen()),
          (route) => false,
        );
      }
    } else {
      if (mounted) {
        setState(() {
          _isLoading = false;
          _errorMessage = authProvider.errorMessage ?? 'Signup failed. Please try again.';
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: PremiumStyle.background,
      body: SafeArea(
        child: FadeTransition(
          opacity: _fadeAnimation,
          child: Column(
            children: [
              Expanded(
                child: SingleChildScrollView(
                  padding: const EdgeInsets.symmetric(
                      horizontal: PremiumStyle.spacing),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      const SizedBox(height: 40),

                      // Back button
                      Align(
                        alignment: Alignment.centerLeft,
                        child: GestureDetector(
                          onTap: () => Navigator.of(context).pop(),
                          child: Container(
                            padding: const EdgeInsets.all(10),
                            decoration: BoxDecoration(
                              color: Colors.white,
                              borderRadius: BorderRadius.circular(12),
                              boxShadow: [
                                BoxShadow(
                                  color: Colors.black.withOpacity(0.05),
                                  blurRadius: 8,
                                  offset: const Offset(0, 2),
                                ),
                              ],
                            ),
                            child: const Icon(Icons.arrow_back_rounded,
                                size: 20, color: PremiumStyle.primaryText),
                          ),
                        ),
                      ),

                      const SizedBox(height: 32),

                      Text(
                        "your unique\nUPI ID.",
                        style: PremiumStyle.headingLarge,
                      ),
                      const SizedBox(height: 8),
                      Text(
                        "Enter your UPI ID to complete setup",
                        style: PremiumStyle.subHeading,
                      ),

                      const SizedBox(height: 40),

                      // ═══════════════════════════════════
                      // UPI ID CARD
                      // ═══════════════════════════════════
                      Container(
                        width: double.infinity,
                        padding: const EdgeInsets.symmetric(
                          horizontal: PremiumStyle.cardPaddingHorizontal,
                          vertical: PremiumStyle.cardPaddingVertical,
                        ),
                        decoration: BoxDecoration(
                          color: Colors.white,
                          borderRadius:
                              BorderRadius.circular(PremiumStyle.cardRadius),
                          boxShadow: PremiumStyle.cardShadow,
                        ),
                        child: Column(
                          children: [
                            Text(
                              'YOUR UPI ID',
                              style: TextStyle(fontFamily: 'Manrope', 
                                fontSize: 12,
                                letterSpacing: 1.5,
                                fontWeight: FontWeight.w500,
                                color: Colors.grey,
                              ),
                            ),
                            const SizedBox(height: 20),
                            Container(
                              decoration: BoxDecoration(
                                color: const Color(0xFFF1F5F9),
                                borderRadius: BorderRadius.circular(14),
                              ),
                              child: TextField(
                                controller: _upiController,
                                cursorColor: Colors.black,
                                style: TextStyle(fontFamily: 'Manrope', 
                                  fontSize: 22,
                                  fontWeight: FontWeight.w600,
                                  color: PremiumStyle.primaryText,
                                  letterSpacing: 0.5,
                                ),
                                decoration: InputDecoration(
                                  hintText: 'yourname@oksbi',
                                  hintStyle: TextStyle(fontFamily: 'Manrope', 
                                    fontSize: 22,
                                    fontWeight: FontWeight.w600,
                                    color: Colors.black.withOpacity(0.12),
                                    letterSpacing: 0.5,
                                  ),
                                  prefixIcon: const Icon(
                                      Icons.account_balance_wallet_rounded,
                                      color: PremiumStyle.secondaryText,
                                      size: 22),
                                  border: InputBorder.none,
                                  contentPadding: const EdgeInsets.all(16),
                                ),
                                onSubmitted: (_) => _createAccount(),
                              ),
                            ),
                            const SizedBox(height: 14),
                            Row(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                Icon(Icons.info_outline_rounded,
                                    size: 14,
                                    color: PremiumStyle.secondaryText),
                                const SizedBox(width: 6),
                                Text(
                                  'Numbers, letters & special symbols allowed',
                                  style: TextStyle(fontFamily: 'Manrope', 
                                    fontSize: 12,
                                    color: PremiumStyle.secondaryText,
                                  ),
                                ),
                              ],
                            ),
                          ],
                        ),
                      ),

                      // Error message
                      if (_errorMessage != null) ...[
                        const SizedBox(height: 16),
                        Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 16, vertical: 12),
                          decoration: BoxDecoration(
                            color: Colors.red.shade50,
                            borderRadius: BorderRadius.circular(12),
                            border: Border.all(
                                color: Colors.red.shade200, width: 1),
                          ),
                          child: Row(
                            children: [
                              Icon(Icons.error_outline_rounded,
                                  color: Colors.red.shade400, size: 20),
                              const SizedBox(width: 10),
                              Expanded(
                                child: Text(
                                  _errorMessage!,
                                  style: TextStyle(fontFamily: 'Manrope', 
                                    fontSize: 13,
                                    fontWeight: FontWeight.w500,
                                    color: Colors.red.shade700,
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],

                      const SizedBox(height: 32),
                    ],
                  ),
                ),
              ),

              // ── Bottom button ─────────────────
              Padding(
                padding: const EdgeInsets.fromLTRB(
                    PremiumStyle.spacing, 0, PremiumStyle.spacing, 32),
                child: Container(
                  decoration: BoxDecoration(
                    borderRadius:
                        BorderRadius.circular(PremiumStyle.cardRadius),
                    boxShadow: [
                      BoxShadow(
                        color: PremiumStyle.accentColor.withOpacity(0.3),
                        blurRadius: 16,
                        offset: const Offset(0, 6),
                      ),
                    ],
                  ),
                  child: ElevatedButton(
                    onPressed: _isLoading ? null : _createAccount,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: PremiumStyle.buttonColor,
                      disabledBackgroundColor: Colors.grey.shade300,
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(vertical: 20),
                      shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(
                              PremiumStyle.cardRadius)),
                      elevation: 0,
                    ),
                    child: _isLoading
                        ? const SizedBox(
                            width: 22,
                            height: 22,
                            child: CircularProgressIndicator(
                                strokeWidth: 2.5, color: Colors.white),
                          )
                        : Text('Create Account',
                            style: PremiumStyle.buttonText),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
