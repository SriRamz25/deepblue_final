import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';
import 'premium_styles.dart';
import 'premium_password_screen.dart';

// ─────────────────────────────────────────
// Country model
// ─────────────────────────────────────────
class CountryCode {
  final String name;
  final String dialCode;
  const CountryCode(this.name, this.dialCode);
}

const List<CountryCode> countryCodes = [
  CountryCode('India', '+91'),
  CountryCode('United States', '+1'),
  CountryCode('United Kingdom', '+44'),
  CountryCode('Australia', '+61'),
  CountryCode('Canada', '+1'),
  CountryCode('Germany', '+49'),
  CountryCode('France', '+33'),
  CountryCode('Japan', '+81'),
  CountryCode('Singapore', '+65'),
  CountryCode('UAE', '+971'),
  CountryCode('Saudi Arabia', '+966'),
  CountryCode('Bangladesh', '+880'),
  CountryCode('Sri Lanka', '+94'),
  CountryCode('Nepal', '+977'),
  CountryCode('Malaysia', '+60'),
  CountryCode('South Korea', '+82'),
  CountryCode('Brazil', '+55'),
  CountryCode('South Africa', '+27'),
  CountryCode('Nigeria', '+234'),
  CountryCode('Indonesia', '+62'),
];

class PremiumSignupScreen extends StatefulWidget {
  const PremiumSignupScreen({super.key});

  @override
  State<PremiumSignupScreen> createState() => _PremiumSignupScreenState();
}

class _PremiumSignupScreenState extends State<PremiumSignupScreen>
    with SingleTickerProviderStateMixin {
  final TextEditingController _phoneController = TextEditingController();
  final List<TextEditingController> _otpControllers =
      List.generate(6, (_) => TextEditingController());
  final List<FocusNode> _otpFocusNodes = List.generate(6, (_) => FocusNode());

  CountryCode _selectedCountry = countryCodes[0]; // India default
  bool _otpSent = false;
  bool _otpVerified = false;
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
    _phoneController.dispose();
    for (var c in _otpControllers) {
      c.dispose();
    }
    for (var f in _otpFocusNodes) {
      f.dispose();
    }
    super.dispose();
  }

  // ── OTP field navigation ──────────────────
  void _onOtpChanged(String value, int index) {
    if (value.isNotEmpty) {
      if (index < 5) {
        _otpFocusNodes[index + 1].requestFocus();
      } else {
        _otpFocusNodes[index].unfocus();
      }
    } else if (index > 0) {
      _otpFocusNodes[index - 1].requestFocus();
    }
    setState(() => _errorMessage = null);
  }

  String _getOtp() => _otpControllers.map((c) => c.text).join();

  // ── Send OTP ──────────────────────────────
  void _sendOtp() {
    final phone = _phoneController.text.trim();
    if (phone.length < 10) {
      setState(() => _errorMessage = 'Please enter a valid mobile number');
      return;
    }
    setState(() {
      _otpSent = true;
      _errorMessage = null;
    });
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content:
            Text('OTP sent to ${_selectedCountry.dialCode} $phone'),
        backgroundColor: PremiumStyle.accentColor,
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      ),
    );
  }

  // ── Verify OTP → go to password page ──────
  void _verifyOtp() {
    final otp = _getOtp();
    if (otp.length < 6) {
      setState(() => _errorMessage = 'Please enter the complete 6-digit OTP');
      return;
    }
    setState(() {
      _otpVerified = true;
      _errorMessage = null;
    });

    final phone = _phoneController.text.trim();
    final fullPhone = '${_selectedCountry.dialCode}$phone';

    Navigator.of(context).push(PageRouteBuilder(
      pageBuilder: (context, animation, secondaryAnimation) =>
          PremiumPasswordScreen(phone: fullPhone),
      transitionsBuilder: (context, animation, secondaryAnimation, child) {
        return FadeTransition(opacity: animation, child: child);
      },
    ));
  }

  // ── Country picker bottom sheet ───────────
  void _showCountryPicker() {
    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (context) {
        return SafeArea(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const SizedBox(height: 12),
              Container(
                width: 40,
                height: 4,
                decoration: BoxDecoration(
                  color: Colors.grey.shade300,
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
              const SizedBox(height: 16),
              Text(
                'SELECT COUNTRY',
                style: GoogleFonts.manrope(
                  fontSize: 12,
                  letterSpacing: 1.5,
                  fontWeight: FontWeight.w600,
                  color: Colors.grey,
                ),
              ),
              const SizedBox(height: 8),
              Flexible(
                child: ListView.builder(
                  shrinkWrap: true,
                  itemCount: countryCodes.length,
                  itemBuilder: (context, index) {
                    final country = countryCodes[index];
                    final isSelected =
                        country.dialCode == _selectedCountry.dialCode &&
                            country.name == _selectedCountry.name;
                    return ListTile(
                      leading: Container(
                          width: 36,
                          height: 36,
                          decoration: BoxDecoration(
                            color: const Color(0xFFF1F5F9),
                            borderRadius: BorderRadius.circular(8),
                          ),
                          child: Center(
                            child: Text(
                              country.dialCode,
                              style: GoogleFonts.manrope(
                                fontSize: 13,
                                fontWeight: FontWeight.w700,
                                color: PremiumStyle.primaryText,
                              ),
                            ),
                          ),
                        ),
                      title: Text(
                        country.name,
                        style: GoogleFonts.manrope(
                          fontWeight:
                              isSelected ? FontWeight.w700 : FontWeight.w500,
                          color: isSelected
                              ? PremiumStyle.accentColor
                              : PremiumStyle.primaryText,
                        ),
                      ),
                      trailing: Text(
                        country.dialCode,
                        style: GoogleFonts.manrope(
                          fontSize: 16,
                          fontWeight: FontWeight.w600,
                          color: isSelected
                              ? PremiumStyle.accentColor
                              : PremiumStyle.secondaryText,
                        ),
                      ),
                      onTap: () {
                        setState(() => _selectedCountry = country);
                        Navigator.pop(context);
                      },
                    );
                  },
                ),
              ),
              const SizedBox(height: 16),
            ],
          ),
        );
      },
    );
  }

  // ─────────────────────────────────────────
  // BUILD
  // ─────────────────────────────────────────
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

                      // Title
                      Text(
                        "create your\naccount.",
                        style: PremiumStyle.headingLarge,
                      ),
                      const SizedBox(height: 8),
                      Text(
                        "Enter your mobile number to get started",
                        style: PremiumStyle.subHeading,
                      ),

                      const SizedBox(height: 40),

                      // ═══════════════════════════════════
                      // PHONE NUMBER CARD
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
                              'YOUR MOBILE NUMBER',
                              style: GoogleFonts.manrope(
                                fontSize: 12,
                                letterSpacing: 1.5,
                                fontWeight: FontWeight.w500,
                                color: Colors.grey,
                              ),
                            ),
                            const SizedBox(height: 20),

                            // Country code + phone input row
                            Row(
                              children: [
                                // Country code button
                                GestureDetector(
                                  onTap: _otpSent ? null : _showCountryPicker,
                                  child: Container(
                                    padding: const EdgeInsets.symmetric(
                                        horizontal: 14, vertical: 14),
                                    decoration: BoxDecoration(
                                      color: const Color(0xFFF1F5F9),
                                      borderRadius: BorderRadius.circular(14),
                                    ),
                                    child: Row(
                                      mainAxisSize: MainAxisSize.min,
                                      children: [
                                        Text(
                                          _selectedCountry.dialCode,
                                          style: GoogleFonts.manrope(
                                            fontSize: 18,
                                            fontWeight: FontWeight.w700,
                                            color: PremiumStyle.primaryText,
                                          ),
                                        ),
                                        if (!_otpSent) ...[
                                          const SizedBox(width: 4),
                                          Icon(
                                              Icons
                                                  .keyboard_arrow_down_rounded,
                                              size: 20,
                                              color:
                                                  PremiumStyle.secondaryText),
                                        ],
                                      ],
                                    ),
                                  ),
                                ),

                                const SizedBox(width: 12),

                                // Phone input
                                Expanded(
                                  child: TextField(
                                    controller: _phoneController,
                                    keyboardType: TextInputType.phone,
                                    enabled: !_otpSent,
                                    cursorColor: Colors.black,
                                    style: GoogleFonts.manrope(
                                      fontSize: 22,
                                      fontWeight: FontWeight.w600,
                                      color: PremiumStyle.primaryText,
                                      letterSpacing: 1.5,
                                    ),
                                    inputFormatters: [
                                      FilteringTextInputFormatter.digitsOnly,
                                      LengthLimitingTextInputFormatter(10),
                                    ],
                                    decoration: InputDecoration(
                                      hintText: '99629 74097',
                                      hintStyle: GoogleFonts.manrope(
                                        fontSize: 22,
                                        fontWeight: FontWeight.w600,
                                        color: Colors.black.withOpacity(0.12),
                                        letterSpacing: 1.5,
                                      ),
                                      border: InputBorder.none,
                                    ),
                                    onSubmitted: (_) {
                                      if (!_otpSent) _sendOtp();
                                    },
                                  ),
                                ),
                              ],
                            ),

                            // Confirmed badge
                            if (_otpSent)
                              Padding(
                                padding: const EdgeInsets.only(top: 12),
                                child: Row(
                                  mainAxisAlignment: MainAxisAlignment.center,
                                  children: [
                                    Icon(Icons.check_circle_rounded,
                                        size: 16,
                                        color: Colors.green.shade500),
                                    const SizedBox(width: 6),
                                    Text(
                                      'Number confirmed',
                                      style: GoogleFonts.manrope(
                                        fontSize: 12,
                                        fontWeight: FontWeight.w500,
                                        color: Colors.green.shade600,
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                          ],
                        ),
                      ),

                      // ═══════════════════════════════════
                      // OTP CARD (shown after send)
                      // ═══════════════════════════════════
                      if (_otpSent) ...[
                        const SizedBox(height: 24),
                        AnimatedOpacity(
                          opacity: 1.0,
                          duration: const Duration(milliseconds: 400),
                          child: Container(
                            width: double.infinity,
                            padding: const EdgeInsets.symmetric(
                              horizontal: PremiumStyle.cardPaddingHorizontal,
                              vertical: PremiumStyle.cardPaddingVertical,
                            ),
                            decoration: BoxDecoration(
                              color: Colors.white,
                              borderRadius: BorderRadius.circular(
                                  PremiumStyle.cardRadius),
                              boxShadow: PremiumStyle.cardShadow,
                            ),
                            child: Column(
                              children: [
                                Text(
                                  'ENTER 6-DIGIT OTP',
                                  style: GoogleFonts.manrope(
                                    fontSize: 12,
                                    letterSpacing: 1.5,
                                    fontWeight: FontWeight.w500,
                                    color: Colors.grey,
                                  ),
                                ),
                                const SizedBox(height: 8),
                                Text(
                                  'Sent to ${_selectedCountry.dialCode} ${_phoneController.text}',
                                  style: GoogleFonts.manrope(
                                    fontSize: 12,
                                    color: PremiumStyle.secondaryText,
                                  ),
                                ),
                                const SizedBox(height: 24),
                                Row(
                                  mainAxisAlignment:
                                      MainAxisAlignment.spaceBetween,
                                  children: List.generate(
                                      6, (i) => _buildOtpBox(i)),
                                ),
                                const SizedBox(height: 16),
                                GestureDetector(
                                  onTap: _sendOtp,
                                  child: Text(
                                    'Resend OTP',
                                    style: GoogleFonts.manrope(
                                      fontSize: 13,
                                      fontWeight: FontWeight.w600,
                                      color: PremiumStyle.accentColor,
                                      decoration: TextDecoration.underline,
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                      ],

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
                                  style: GoogleFonts.manrope(
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
                    onPressed: _otpSent ? _verifyOtp : _sendOtp,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: PremiumStyle.buttonColor,
                      foregroundColor: Colors.white,
                      minimumSize: const Size(double.infinity, 56),
                      padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 20),
                      shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(
                              PremiumStyle.cardRadius)),
                      elevation: 0,
                    ),
                    child: Text(
                      _otpSent ? 'Verify' : 'Send OTP',
                      style: PremiumStyle.buttonText.copyWith(fontSize: 16),
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildOtpBox(int index) {
    return Container(
      width: 46,
      height: 58,
      decoration: BoxDecoration(
        color: const Color(0xFFF1F5F9),
        borderRadius: BorderRadius.circular(14),
        border: _otpControllers[index].text.isNotEmpty
            ? Border.all(
                color: PremiumStyle.accentColor.withOpacity(0.5),
                width: 1.5)
            : null,
      ),
      child: Center(
        child: TextField(
          controller: _otpControllers[index],
          focusNode: _otpFocusNodes[index],
          textAlign: TextAlign.center,
          style: const TextStyle(
            fontFamily: 'Manrope',
            fontSize: 22,
            fontWeight: FontWeight.w700,
            color: PremiumStyle.primaryText,
          ),
          keyboardType: TextInputType.number,
          inputFormatters: [
            LengthLimitingTextInputFormatter(1),
            FilteringTextInputFormatter.digitsOnly,
          ],
          onChanged: (val) => _onOtpChanged(val, index),
          decoration:
              const InputDecoration(border: InputBorder.none, counterText: ''),
        ),
      ),
    );
  }
}
