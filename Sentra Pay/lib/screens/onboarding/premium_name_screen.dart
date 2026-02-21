import 'package:flutter/material.dart';
import 'premium_styles.dart';
import 'premium_set_pin_screen.dart';

class PremiumNameScreen extends StatefulWidget {
  final String phone;
  const PremiumNameScreen({super.key, required this.phone});

  @override
  State<PremiumNameScreen> createState() => _PremiumNameScreenState();
}

class _PremiumNameScreenState extends State<PremiumNameScreen> {
  final TextEditingController _nameController = TextEditingController();

  void _onContinue() {
    if (_nameController.text.trim().isNotEmpty) {
      Navigator.of(context).push(PageRouteBuilder(
        pageBuilder: (context, animation, secondaryAnimation) =>
            PremiumSetPinScreen(name: _nameController.text.trim(), phone: widget.phone),
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
                "what's your\nname.",
                style: PremiumStyle.headingLarge,
              ),
              const SizedBox(height: 60),

              // Standard Premium Card
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
                      'YOUR FULL NAME',
                      style: TextStyle(fontFamily: 'Manrope', 
                        fontSize: 12,
                        letterSpacing: 1.5,
                        fontWeight: FontWeight.w500,
                        color: Colors.grey,
                      ),
                    ),
                    const SizedBox(height: 20),
                    TextField(
                      controller: _nameController,
                      textAlign: TextAlign.center,
                      cursorColor: Colors.black,
                      style: PremiumStyle.primaryInputStyle,
                      textCapitalization: TextCapitalization.words,
                      decoration: InputDecoration(
                        hintText: 'John Doe',
                        hintStyle: PremiumStyle.primaryInputStyle.copyWith(
                          color: Colors.black.withOpacity(0.1),
                        ),
                        border: InputBorder.none,
                      ),
                      onSubmitted: (_) => _onContinue(),
                    ),
                  ],
                ),
              ),

              const Spacer(),
              ElevatedButton(
                onPressed: _onContinue,
                style: ElevatedButton.styleFrom(
                  backgroundColor: PremiumStyle.buttonColor,
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
}
