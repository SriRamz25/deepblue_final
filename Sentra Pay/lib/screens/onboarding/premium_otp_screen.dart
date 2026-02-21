import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'premium_styles.dart';
import 'premium_name_screen.dart';

class PremiumOTPScreen extends StatefulWidget {
  final String name;
  final String phone;
  const PremiumOTPScreen({super.key, required this.name, required this.phone});

  @override
  State<PremiumOTPScreen> createState() => _PremiumOTPScreenState();
}

class _PremiumOTPScreenState extends State<PremiumOTPScreen> {
  final List<TextEditingController> _controllers = List.generate(
    6,
    (_) => TextEditingController(),
  );
  final List<FocusNode> _focusNodes = List.generate(6, (_) => FocusNode());
  bool _isFilled = false;

  void _onChanged(String value, int index) {
    if (value.isNotEmpty) {
      if (index < 5) {
        _focusNodes[index + 1].requestFocus();
      } else {
        _focusNodes[index].unfocus();
        setState(() => _isFilled = true);
      }
    } else if (index > 0) {
      _focusNodes[index - 1].requestFocus();
      setState(() => _isFilled = false);
    }
  }

  void _onVerify() {
    Navigator.of(context).push(
      PageRouteBuilder(
        pageBuilder: (context, animation, secondaryAnimation) =>
            PremiumNameScreen(phone: widget.phone),
        transitionsBuilder: (context, animation, secondaryAnimation, child) {
          return FadeTransition(opacity: animation, child: child);
        },
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: PremiumStyle.background,
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: PremiumStyle.spacing),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const SizedBox(height: 60),
              Text("verify your\nnumber.", style: PremiumStyle.headingLarge),
              const SizedBox(height: 60),

              Container(
                width: double.infinity,
                padding: const EdgeInsets.symmetric(
                  horizontal: PremiumStyle.cardPaddingHorizontal,
                  vertical: PremiumStyle.cardPaddingVertical,
                ),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(PremiumStyle.cardRadius),
                  boxShadow: PremiumStyle.cardShadow,
                ),
                child: Column(
                  children: [
                    Text(
                      'ENTER 6-DIGIT CODE',
                      style: TextStyle(
                        fontFamily: 'Manrope',
                        fontSize: 12,
                        letterSpacing: 1.5,
                        fontWeight: FontWeight.w500,
                        color: Colors.grey,
                      ),
                    ),
                    const SizedBox(height: 32),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: List.generate(
                        6,
                        (index) => _buildOTPBox(index),
                      ),
                    ),
                  ],
                ),
              ),

              const Spacer(),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton(
                  onPressed: _isFilled ? _onVerify : null,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: PremiumStyle.buttonColor,
                    disabledBackgroundColor: Colors.grey.withOpacity(0.1),
                    minimumSize: const Size(double.infinity, 56),
                    padding: const EdgeInsets.symmetric(
                      horizontal: 32,
                      vertical: 20,
                    ),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(
                        PremiumStyle.cardRadius,
                      ),
                    ),
                  ),
                  child: const Text(
                    "Verify",
                    style: TextStyle(
                      fontFamily: 'Manrope',
                      color: Colors.white,
                      fontSize: 16,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 40),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildOTPBox(int index) {
    return Container(
      width: 42,
      height: 56,
      decoration: BoxDecoration(
        color: const Color(0xFFF1F5F9),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Center(
        child: TextField(
          controller: _controllers[index],
          focusNode: _focusNodes[index],
          textAlign: TextAlign.center,
          style: PremiumStyle.primaryInputStyle.copyWith(
            fontSize: 22,
            letterSpacing: 0,
          ),
          keyboardType: TextInputType.number,
          inputFormatters: [
            LengthLimitingTextInputFormatter(1),
            FilteringTextInputFormatter.digitsOnly,
          ],
          onChanged: (val) => _onChanged(val, index),
          decoration: const InputDecoration(
            border: InputBorder.none,
            counterText: "",
          ),
        ),
      ),
    );
  }
}
