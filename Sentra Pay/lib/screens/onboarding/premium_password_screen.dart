import 'package:flutter/material.dart';
import 'premium_styles.dart';
import 'premium_upi_id_screen.dart';

class PremiumPasswordScreen extends StatefulWidget {
  final String phone;
  const PremiumPasswordScreen({super.key, required this.phone});

  @override
  State<PremiumPasswordScreen> createState() => _PremiumPasswordScreenState();
}

class _PremiumPasswordScreenState extends State<PremiumPasswordScreen>
    with SingleTickerProviderStateMixin {
  final TextEditingController _passwordController = TextEditingController();
  final TextEditingController _confirmController = TextEditingController();

  bool _obscurePassword = true;
  bool _obscureConfirm = true;
  String? _errorMessage;

  // Validation state
  bool _hasUppercase = false;
  bool _hasDigit = false;
  bool _hasSpecial = false;
  bool _hasMinLength = false;
  bool _passwordsMatch = false;

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

    _passwordController.addListener(_validate);
    _confirmController.addListener(_validate);
  }

  @override
  void dispose() {
    _fadeController.dispose();
    _passwordController.dispose();
    _confirmController.dispose();
    super.dispose();
  }

  void _validate() {
    final pw = _passwordController.text;
    final cf = _confirmController.text;
    setState(() {
      _hasUppercase = pw.contains(RegExp(r'[A-Z]'));
      _hasDigit = pw.contains(RegExp(r'[0-9]'));
      _hasSpecial =
          pw.contains(RegExp(r'[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\\/~`]'));
      _hasMinLength = pw.length >= 8;
      _passwordsMatch = pw.isNotEmpty && pw == cf;
    });
  }

  bool get _isPasswordValid =>
      _hasUppercase && _hasDigit && _hasSpecial && _hasMinLength;

  void _onNext() {
    if (!_isPasswordValid) {
      setState(
          () => _errorMessage = 'Password does not meet all requirements');
      return;
    }
    if (!_passwordsMatch) {
      setState(() => _errorMessage = 'Passwords do not match');
      return;
    }
    setState(() => _errorMessage = null);

    Navigator.of(context).push(PageRouteBuilder(
      pageBuilder: (context, animation, secondaryAnimation) =>
          PremiumUpiIdScreen(
        phone: widget.phone,
        password: _passwordController.text,
      ),
      transitionsBuilder: (context, animation, secondaryAnimation, child) {
        return FadeTransition(opacity: animation, child: child);
      },
    ));
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
                        "set your\npassword.",
                        style: PremiumStyle.headingLarge,
                      ),
                      const SizedBox(height: 8),
                      Text(
                        "Create a strong password for your account",
                        style: PremiumStyle.subHeading,
                      ),

                      const SizedBox(height: 40),

                      // ═══════════════════════════════════
                      // PASSWORD CARD
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
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Center(
                              child: Text(
                                'SET YOUR PASSWORD',
                                style: TextStyle(fontFamily: 'Manrope', 
                                  fontSize: 12,
                                  letterSpacing: 1.5,
                                  fontWeight: FontWeight.w500,
                                  color: Colors.grey,
                                ),
                              ),
                            ),
                            const SizedBox(height: 20),

                            // Password field
                            Container(
                              decoration: BoxDecoration(
                                color: const Color(0xFFF1F5F9),
                                borderRadius: BorderRadius.circular(14),
                              ),
                              child: TextField(
                                controller: _passwordController,
                                obscureText: _obscurePassword,
                                cursorColor: Colors.black,
                                style: const TextStyle(fontFamily: 'Manrope', 
                                  fontSize: 16,
                                  fontWeight: FontWeight.w600,
                                  color: Color(0xFF0F172A),
                                ),
                                decoration: InputDecoration(
                                  hintText: 'Enter password',
                                  hintStyle: TextStyle(fontFamily: 'Manrope', 
                                    fontSize: 16,
                                    color: Colors.black.withOpacity(0.2),
                                  ),
                                  prefixIcon: const Icon(
                                      Icons.lock_outline_rounded,
                                      color: PremiumStyle.secondaryText,
                                      size: 22),
                                  suffixIcon: IconButton(
                                    icon: Icon(
                                      _obscurePassword
                                          ? Icons.visibility_off_rounded
                                          : Icons.visibility_rounded,
                                      color: PremiumStyle.secondaryText,
                                      size: 22,
                                    ),
                                    onPressed: () => setState(() =>
                                        _obscurePassword = !_obscurePassword),
                                  ),
                                  border: InputBorder.none,
                                  contentPadding: const EdgeInsets.all(16),
                                ),
                              ),
                            ),

                            const SizedBox(height: 20),

                            // Validation rules
                            _buildRule('At least 8 characters', _hasMinLength),
                            const SizedBox(height: 8),
                            _buildRule(
                                'One uppercase letter (A-Z)', _hasUppercase),
                            const SizedBox(height: 8),
                            _buildRule('One number (0-9)', _hasDigit),
                            const SizedBox(height: 8),
                            _buildRule(
                                'One special symbol (!@#\$...)', _hasSpecial),
                          ],
                        ),
                      ),

                      const SizedBox(height: 24),

                      // ═══════════════════════════════════
                      // CONFIRM PASSWORD CARD
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
                          border: _confirmController.text.isNotEmpty
                              ? Border.all(
                                  color: _passwordsMatch
                                      ? Colors.green.shade300
                                      : Colors.red.shade300,
                                  width: 1.5)
                              : null,
                        ),
                        child: Column(
                          children: [
                            Text(
                              'CONFIRM PASSWORD',
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
                                controller: _confirmController,
                                obscureText: _obscureConfirm,
                                cursorColor: Colors.black,
                                style: const TextStyle(fontFamily: 'Manrope', 
                                  fontSize: 16,
                                  fontWeight: FontWeight.w600,
                                  color: Color(0xFF0F172A),
                                ),
                                decoration: InputDecoration(
                                  hintText: 'Re-enter password',
                                  hintStyle: TextStyle(fontFamily: 'Manrope', 
                                    fontSize: 16,
                                    color: Colors.black.withOpacity(0.2),
                                  ),
                                  prefixIcon: const Icon(
                                      Icons.lock_outline_rounded,
                                      color: PremiumStyle.secondaryText,
                                      size: 22),
                                  suffixIcon: IconButton(
                                    icon: Icon(
                                      _obscureConfirm
                                          ? Icons.visibility_off_rounded
                                          : Icons.visibility_rounded,
                                      color: PremiumStyle.secondaryText,
                                      size: 22,
                                    ),
                                    onPressed: () => setState(() =>
                                        _obscureConfirm = !_obscureConfirm),
                                  ),
                                  border: InputBorder.none,
                                  contentPadding: const EdgeInsets.all(16),
                                ),
                              ),
                            ),

                            // Match indicator
                            if (_confirmController.text.isNotEmpty) ...[
                              const SizedBox(height: 14),
                              Row(
                                mainAxisAlignment: MainAxisAlignment.center,
                                children: [
                                  Icon(
                                    _passwordsMatch
                                        ? Icons.check_circle_rounded
                                        : Icons.cancel_rounded,
                                    size: 16,
                                    color: _passwordsMatch
                                        ? Colors.green.shade500
                                        : Colors.red.shade400,
                                  ),
                                  const SizedBox(width: 6),
                                  Text(
                                    _passwordsMatch
                                        ? 'Passwords match'
                                        : 'Passwords do not match',
                                    style: TextStyle(fontFamily: 'Manrope', 
                                      fontSize: 12,
                                      fontWeight: FontWeight.w600,
                                      color: _passwordsMatch
                                          ? Colors.green.shade600
                                          : Colors.red.shade500,
                                    ),
                                  ),
                                ],
                              ),
                            ],
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
                    onPressed: _onNext,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: PremiumStyle.buttonColor,
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(vertical: 20),
                      shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(
                              PremiumStyle.cardRadius)),
                      elevation: 0,
                    ),
                    child: Text('Next', style: PremiumStyle.buttonText),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildRule(String text, bool isValid) {
    return Row(
      children: [
        AnimatedContainer(
          duration: const Duration(milliseconds: 300),
          width: 20,
          height: 20,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color:
                isValid ? Colors.green.shade500 : const Color(0xFFE2E8F0),
          ),
          child: Center(
            child: Icon(
              isValid ? Icons.check_rounded : Icons.close_rounded,
              size: 14,
              color: isValid ? Colors.white : Colors.grey.shade400,
            ),
          ),
        ),
        const SizedBox(width: 10),
        Text(
          text,
          style: TextStyle(fontFamily: 'Manrope', 
            fontSize: 13,
            fontWeight: FontWeight.w500,
            color: isValid
                ? Colors.green.shade700
                : PremiumStyle.secondaryText,
          ),
        ),
      ],
    );
  }
}
