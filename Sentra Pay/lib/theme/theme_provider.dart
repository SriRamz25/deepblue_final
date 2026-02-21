import 'package:flutter/material.dart';

class ThemeProvider extends ChangeNotifier {
  // changed to light mode for premium clean look
  final bool _isDarkMode = false;

  bool get isDarkMode => _isDarkMode;

  void toggleTheme() {
    // Theme is fixed to Light Mode
  }
}
