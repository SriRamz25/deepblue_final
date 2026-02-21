import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'premium_styles.dart';
import 'premium_upi_id_screen.dart';

class PremiumSetPinScreen extends StatefulWidget {
  final String name;
  final String phone;
  const PremiumSetPinScreen({super.key, required this.name, required this.phone});

  @override
  State<PremiumSetPinScreen> createState() => _PremiumSetPinScreenState();
}

class _PremiumSetPinScreenState extends State<PremiumSetPinScreen> {
  final List<TextEditingController> _pinControllers = List.generate(4, (_) => TextEditingController());
  final List<FocusNode> _pinFocusNodes = List.generate(4, (_) => FocusNode());
  bool _isFilled = false;

  void _onChanged(String value, int index) {
    if (value.isNotEmpty) {
      if (index < 3) {
        _pinFocusNodes[index + 1].requestFocus();
      } else {
        _pinFocusNodes[index].unfocus();
        setState(() => _isFilled = true);
      }
    } else if (index > 0) {
      _pinFocusNodes[index - 1].requestFocus();
      setState(() => _isFilled = false);
    }
  }

  void _onContinue() {
    final pin = _pinControllers.map((c) => c.text).join();
    if (pin.length == 4) {
      Navigator.of(context).push(PageRouteBuilder(
        pageBuilder: (context, animation, secondaryAnimation) =>
            PremiumUpiIdScreen(name: widget.name, phone: widget.phone, pin: pin),
        transitionsBuilder: (context, animation, secondaryAnimation, child) {
          return FadeTransition(opacity: animation, child: child);
        },
      ));
    }
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
              Text(
                "set your\nPIN.",
                style: PremiumStyle.headingLarge,
              ),
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
                      'CREATE 4-DIGIT PIN',
                      style: TextStyle(fontFamily: 'Manrope', 
                        fontSize: 12,
                        letterSpacing: 1.5,
                        fontWeight: FontWeight.w500,
                        color: Colors.grey,
                      ),
                    ),
                    const SizedBox(height: 32),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: List.generate(4, (index) => _buildPinBox(index)),
                    ),
                  ],
                ),
              ),

              const Spacer(),
              ElevatedButton(
                onPressed: _isFilled ? _onContinue : null,
                style: ElevatedButton.styleFrom(
                  backgroundColor: PremiumStyle.buttonColor,
                  disabledBackgroundColor: Colors.grey.withOpacity(0.1),
                  padding: const EdgeInsets.symmetric(vertical: 20),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(PremiumStyle.cardRadius)),
                ),
                child: const Text("Continue", style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold)),
              ),
              const SizedBox(height: 40),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildPinBox(int index) {
    return Container(
      width: 56,
      height: 64,
      margin: const EdgeInsets.symmetric(horizontal: 8),
      decoration: BoxDecoration(
        color: const Color(0xFFF1F5F9),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Center(
        child: TextField(
          controller: _pinControllers[index],
          focusNode: _pinFocusNodes[index],
          textAlign: TextAlign.center,
          style: PremiumStyle.primaryInputStyle.copyWith(fontSize: 28, letterSpacing: 0),
          keyboardType: TextInputType.number,
          inputFormatters: [LengthLimitingTextInputFormatter(1), FilteringTextInputFormatter.digitsOnly],
          onChanged: (val) => _onChanged(val, index),
          decoration: const InputDecoration(border: InputBorder.none, counterText: ""),
        ),
      ),
    );
  }
}
