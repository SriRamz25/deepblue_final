import 'package:flutter/material.dart';

class PremiumStyle {
  static const Color background = Color(0xFFF8FAFC);
  static const Color cardBackground = Colors.white;
  static const Color primaryText = Color(0xFF0F172A);
  static const Color secondaryText = Color(0xFF64748B); // Slate 500
  static const Color accentColor = Color(0xFF2563EB); // Royal Blue
  static const Color inputBorder = Color(0xFFE2E8F0); // Lighter border
  static const Color buttonColor = Color(0xFF2563EB); // Royal Blue

  static const TextStyle headingLarge = TextStyle(
    fontFamily: 'Manrope',
    fontSize: 32,
    fontWeight: FontWeight.bold,
    color: primaryText,
    letterSpacing: -1.0,
    height: 1.1,
  );

  static const TextStyle subHeading = TextStyle(
    fontFamily: 'Manrope',
    fontSize: 14,
    fontWeight: FontWeight.w400,
    color: secondaryText,
    letterSpacing: 0.2,
  );

  static const TextStyle inputLabel = TextStyle(
    fontFamily: 'Manrope',
    fontSize: 14,
    fontWeight: FontWeight.w500,
    color: secondaryText,
  );

  static const TextStyle buttonText = TextStyle(
    fontFamily: 'Manrope',
    fontSize: 16,
    fontWeight: FontWeight.w600,
    color: Colors.white,
    letterSpacing: 0.5,
  );

  static const TextStyle primaryInputStyle = TextStyle(
    fontFamily: 'Manrope',
    fontSize: 38,
    fontWeight: FontWeight.w600,
    color: primaryText,
    letterSpacing: 1.2,
  );

  static List<BoxShadow> get cardShadow => [
    BoxShadow(
      color: Colors.black.withOpacity(0.08),
      blurRadius: 30,
      offset: const Offset(0, 10),
    ),
  ];

  static const double cardRadius = 24.0;
  static const double cardPaddingVertical = 28.0;
  static const double cardPaddingHorizontal = 24.0;
  static const double spacing = 24.0;
}
