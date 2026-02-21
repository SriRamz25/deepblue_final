import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:url_launcher/url_launcher.dart';
import 'dart:io' show Platform;

class UpiApp {
  final String name;
  final String shortName;
  final Color primaryColor;
  final Color textColor;
  final String logoLetter;
  final String assetPath;
  final String checkScheme;
  final String upiScheme;

  const UpiApp({
    required this.name,
    required this.shortName,
    required this.primaryColor,
    required this.logoLetter,
    required this.assetPath,
    required this.checkScheme,
    this.textColor = Colors.white,
    this.upiScheme = 'upi',
  });

  Uri buildUri({
    required String receiverUpi,
    required double amount,
    String payeeName = '',
  }) {
    final params = [
      'pa=${Uri.encodeComponent(receiverUpi)}',
      if (payeeName.isNotEmpty) 'pn=${Uri.encodeComponent(payeeName)}',
      'am=${amount.toStringAsFixed(2)}',
      'cu=INR',
      'tn=${Uri.encodeComponent("Payment via SentraPay")}',
    ].join('&');
    return Uri.parse('$upiScheme://pay?$params');
  }
}

const List<UpiApp> kAllUpiApps = [
  UpiApp(
    name: 'Google Pay',
    shortName: 'GPay',
    logoLetter: 'G',
    primaryColor: Color(0xFF4285F4),
    assetPath: 'assets/logos/gpay.png',
    checkScheme: 'tez://upi/pay',
    upiScheme: 'tez',
  ),
  UpiApp(
    name: 'PhonePe',
    shortName: 'PhonePe',
    logoLetter: 'P',
    primaryColor: Color(0xFF5F259F),
    assetPath: 'assets/logos/phonepe.png',
    checkScheme: 'phonepe://pay',
    upiScheme: 'phonepe',
  ),
  UpiApp(
    name: 'Paytm',
    shortName: 'Paytm',
    logoLetter: 'T',
    primaryColor: Color(0xFF002970),
    assetPath: 'assets/logos/paytm.png',
    checkScheme: 'paytmmp://pay',
    upiScheme: 'paytmmp',
  ),
  UpiApp(
    name: 'BHIM',
    shortName: 'BHIM',
    logoLetter: 'B',
    primaryColor: Color(0xFF00938B),
    assetPath: 'assets/logos/bhim.png',
    checkScheme: 'bhim://pay',
    upiScheme: 'bhim',
  ),
  UpiApp(
    name: 'Amazon Pay',
    shortName: 'Amazon',
    logoLetter: 'A',
    primaryColor: Color(0xFFFF9900),
    textColor: Color(0xFF1A1A1A),
    assetPath: 'assets/logos/amazon.png',
    checkScheme: 'amazonpay://pay',
    upiScheme: 'amazonpay',
  ),
  UpiApp(
    name: 'Cred',
    shortName: 'Cred',
    logoLetter: 'C',
    primaryColor: Color(0xFF1C3557),
    assetPath: 'assets/logos/cred.png',
    checkScheme: 'credpay://pay',
    upiScheme: 'credpay',
  ),
];

Future<UpiApp?> showUpiAppSelector(
  BuildContext context, {
  required double amount,
  required String receiverUpi,
}) {
  return showModalBottomSheet<UpiApp>(
    context: context,
    isScrollControlled: true,
    backgroundColor: Colors.transparent,
    builder: (_) =>
        UpiAppSelectorSheet(amount: amount, receiverUpi: receiverUpi),
  );
}

class UpiAppSelectorSheet extends StatefulWidget {
  final double amount;
  final String receiverUpi;
  const UpiAppSelectorSheet({
    super.key,
    required this.amount,
    required this.receiverUpi,
  });

  @override
  State<UpiAppSelectorSheet> createState() => _UpiAppSelectorSheetState();
}

class _UpiAppSelectorSheetState extends State<UpiAppSelectorSheet>
    with SingleTickerProviderStateMixin {
  late AnimationController _slideCtrl;
  late Animation<Offset> _slideAnim;

  List<UpiApp> _availableApps = [];
  bool _loadingApps = true;
  UpiApp? _selectedApp;
  bool _redirecting = false;

  @override
  void initState() {
    super.initState();
    _slideCtrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 350),
    );
    _slideAnim = Tween<Offset>(
      begin: const Offset(0, 1),
      end: Offset.zero,
    ).animate(CurvedAnimation(parent: _slideCtrl, curve: Curves.easeOutCubic));
    _slideCtrl.forward();
    _loadAvailableApps();
  }

  @override
  void dispose() {
    _slideCtrl.dispose();
    super.dispose();
  }

  Future<void> _loadAvailableApps() async {
    final bool isMobile = !kIsWeb && (Platform.isAndroid || Platform.isIOS);
    if (!isMobile) {
      if (mounted)
        setState(() {
          _availableApps = kAllUpiApps;
          _loadingApps = false;
        });
      return;
    }
    final List<UpiApp> found = [];
    for (final app in kAllUpiApps) {
      try {
        if (await canLaunchUrl(Uri.parse(app.checkScheme))) found.add(app);
      } catch (_) {}
    }
    if (mounted) {
      setState(() {
        _availableApps = found.isNotEmpty ? found : kAllUpiApps;
        _loadingApps = false;
      });
    }
  }

  void _onAppTapped(UpiApp app) async {
    setState(() {
      _selectedApp = app;
      _redirecting = true;
    });
    await Future.delayed(const Duration(milliseconds: 1200));
    if (mounted) Navigator.of(context).pop(app);
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final bgColor = isDark ? const Color(0xFF1E2433) : Colors.white;
    final textPrimary = isDark ? Colors.white : const Color(0xFF1A1A2E);
    final textSub = isDark ? Colors.white60 : Colors.black45;

    return SlideTransition(
      position: _slideAnim,
      child: Container(
        decoration: BoxDecoration(
          color: bgColor,
          borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.15),
              blurRadius: 20,
              spreadRadius: 2,
            ),
          ],
        ),
        child: SafeArea(
          child: _redirecting
              ? _buildRedirecting(textPrimary, textSub)
              : _loadingApps
              ? _buildLoading(textPrimary)
              : _buildSelector(isDark, textPrimary, textSub),
        ),
      ),
    );
  }

  Widget _buildLoading(Color textPrimary) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 48),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const CircularProgressIndicator(),
          const SizedBox(height: 16),
          Text(
            'Checking available payment apps�',
            style: TextStyle(color: textPrimary, fontSize: 14),
          ),
        ],
      ),
    );
  }

  Widget _buildSelector(bool isDark, Color textPrimary, Color textSub) {
    final payeeName = widget.receiverUpi.split('@').first;
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        const SizedBox(height: 12),
        Container(
          width: 40,
          height: 4,
          decoration: BoxDecoration(
            color: Colors.grey.withValues(alpha: 0.4),
            borderRadius: BorderRadius.circular(2),
          ),
        ),
        const SizedBox(height: 20),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 20),
          child: Row(
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Pay Using',
                    style: TextStyle(
                      fontSize: 20,
                      fontWeight: FontWeight.bold,
                      color: textPrimary,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Row(
                    children: [
                      Icon(
                        Icons.account_circle_outlined,
                        size: 14,
                        color: textSub,
                      ),
                      const SizedBox(width: 4),
                      Text(
                        payeeName,
                        style: TextStyle(fontSize: 13, color: textSub),
                      ),
                    ],
                  ),
                ],
              ),
              const Spacer(),
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 14,
                  vertical: 8,
                ),
                decoration: BoxDecoration(
                  color: const Color(0xFF4CAF50).withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(20),
                ),
                child: Text(
                  'Rs.${widget.amount.toStringAsFixed(0)}',
                  style: const TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                    color: Color(0xFF2E7D32),
                  ),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 8),
        Divider(color: Colors.grey.withValues(alpha: 0.15)),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 4),
          child: Row(
            children: [
              Icon(Icons.send_outlined, size: 14, color: textSub),
              const SizedBox(width: 6),
              Text(
                'To: ${widget.receiverUpi}',
                style: TextStyle(fontSize: 13, color: textSub),
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: GridView.builder(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
              crossAxisCount: 3,
              childAspectRatio: 0.9,
              crossAxisSpacing: 12,
              mainAxisSpacing: 12,
            ),
            itemCount: _availableApps.length,
            itemBuilder: (_, i) => _AppTile(
              app: _availableApps[i],
              onTap: () => _onAppTapped(_availableApps[i]),
            ),
          ),
        ),
        const SizedBox(height: 16),
        Padding(
          padding: const EdgeInsets.only(bottom: 20),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.lock_outline, size: 13, color: textSub),
              const SizedBox(width: 4),
              Text(
                'Secured by SentraPay � 256-bit encrypted',
                style: TextStyle(fontSize: 11, color: textSub),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildRedirecting(Color textPrimary, Color textSub) {
    final app = _selectedApp!;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 48, horizontal: 24),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          TweenAnimationBuilder<double>(
            tween: Tween(begin: 0.8, end: 1.0),
            duration: const Duration(milliseconds: 600),
            curve: Curves.easeInOut,
            builder: (_, v, child) => Transform.scale(scale: v, child: child),
            child: _AppLogoCircle(app: app, size: 80, fontSize: 36),
          ),
          const SizedBox(height: 24),
          Text(
            'Redirecting to ${app.name}',
            style: TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.bold,
              color: textPrimary,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            '${widget.receiverUpi}  �  Rs.${widget.amount.toStringAsFixed(0)}',
            style: TextStyle(fontSize: 13, color: textSub),
          ),
          const SizedBox(height: 28),
          SizedBox(
            width: 200,
            child: LinearProgressIndicator(
              minHeight: 3,
              backgroundColor: Colors.grey.withValues(alpha: 0.2),
              valueColor: AlwaysStoppedAnimation<Color>(app.primaryColor),
            ),
          ),
        ],
      ),
    );
  }
}

class _AppTile extends StatefulWidget {
  final UpiApp app;
  final VoidCallback onTap;
  const _AppTile({required this.app, required this.onTap});
  @override
  State<_AppTile> createState() => _AppTileState();
}

class _AppTileState extends State<_AppTile> {
  bool _pressed = false;
  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final cardBg = isDark ? const Color(0xFF2A2F3E) : const Color(0xFFF8F9FA);
    return GestureDetector(
      onTapDown: (_) => setState(() => _pressed = true),
      onTapUp: (_) {
        setState(() => _pressed = false);
        widget.onTap();
      },
      onTapCancel: () => setState(() => _pressed = false),
      child: AnimatedScale(
        scale: _pressed ? 0.93 : 1.0,
        duration: const Duration(milliseconds: 100),
        child: Container(
          decoration: BoxDecoration(
            color: _pressed
                ? widget.app.primaryColor.withValues(alpha: 0.08)
                : cardBg,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(
              color: _pressed
                  ? widget.app.primaryColor.withValues(alpha: 0.5)
                  : Colors.transparent,
              width: 1.5,
            ),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: isDark ? 0.2 : 0.06),
                blurRadius: 8,
                offset: const Offset(0, 2),
              ),
            ],
          ),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              _AppLogoCircle(app: widget.app, size: 56, fontSize: 24),
              const SizedBox(height: 8),
              Text(
                widget.app.shortName,
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                  color: isDark ? Colors.white : const Color(0xFF1A1A2E),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _AppLogoCircle extends StatelessWidget {
  final UpiApp app;
  final double size;
  final double fontSize;
  const _AppLogoCircle({
    required this.app,
    required this.size,
    required this.fontSize,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: app.primaryColor,
        boxShadow: [
          BoxShadow(
            color: app.primaryColor.withValues(alpha: 0.35),
            blurRadius: size * 0.2,
            spreadRadius: 1,
          ),
        ],
      ),
      clipBehavior: Clip.antiAlias,
      child: ClipOval(
        child: Image.asset(
          app.assetPath,
          width: size,
          height: size,
          fit: BoxFit.cover,
          errorBuilder: (_, _, _) => Center(
            child: Text(
              app.logoLetter,
              style: TextStyle(
                fontSize: fontSize,
                fontWeight: FontWeight.bold,
                color: app.textColor,
              ),
            ),
          ),
        ),
      ),
    );
  }
}
