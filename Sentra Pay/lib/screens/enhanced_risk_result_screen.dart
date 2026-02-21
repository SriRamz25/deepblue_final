import 'package:flutter/material.dart';
import '../theme/app_theme.dart';
import '../widgets/custom_button.dart';
import '../widgets/risk_gauge.dart';
import '../widgets/risk_factor_breakdown.dart';
import '../widgets/community_alert.dart';
import 'payment_success_screen.dart';
import '../models/fraud_store.dart';
import '../models/transaction_history.dart';
import '../models/auth_provider.dart';
import 'package:provider/provider.dart';
import '../services/api_service.dart';
import 'package:url_launcher/url_launcher.dart';
import 'dart:io' show Platform;
import 'package:flutter/foundation.dart' show kIsWeb;
import '../widgets/upi_app_selector_sheet.dart';

class EnhancedRiskResultScreen extends StatefulWidget {
  final double amount;
  final String recipient;
  final RiskAnalysisResult? riskResult; // Added optional result
  final String? transactionId; // Transaction ID from backend

  const EnhancedRiskResultScreen({
    super.key,
    required this.amount,
    required this.recipient,
    this.riskResult, // Pass from HomeScreen after async call
    this.transactionId, // For payment confirmation
  });

  @override
  State<EnhancedRiskResultScreen> createState() =>
      _EnhancedRiskResultScreenState();
}

class _EnhancedRiskResultScreenState extends State<EnhancedRiskResultScreen>
    with SingleTickerProviderStateMixin {
  late AnimationController _fadeController;
  late Animation<double> _fadeAnimation;

  // Risk Data
  double _riskScore = 0.0;
  List<String> _riskFactors = [];
  bool _isSafe = true;
  bool _isUserReported = false;
  bool _isFlaggedReceiver =
      false; // receiver was previously flagged by this user
  RiskCategory _riskCategory = RiskCategory.low;
  double _behaviorScore = 0.0;
  double _amountScore = 0.0;
  double _receiverScore = 0.0;
  bool _isLocalAnalysis = false;
  bool _shouldBlock = false; // true when receiver RED + amount RED → payment blocked

  @override
  void initState() {
    super.initState();
    _fadeController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 800),
    );
    _fadeAnimation = CurvedAnimation(
      parent: _fadeController,
      curve: Curves.easeIn,
    );
    _fadeController.forward();

    _checkRisk();
  }

  void _checkRisk() {
    RiskAnalysisResult result;

    if (widget.riskResult != null) {
      result = widget.riskResult!;
      _isLocalAnalysis = false;
    } else {
      final authProvider = Provider.of<AuthProvider>(context, listen: false);
      final user = authProvider.currentUser;
      result = FraudStore.analyzeRisk(
        widget.recipient,
        widget.amount,
        user: user,
      );
      _isLocalAnalysis = true;
    }

    setState(() {
      _riskScore = result.score;
      _riskFactors = result.factors;
      _isSafe = !result.isBlocked && result.category != RiskCategory.high;
      _riskCategory = result.category;
      _behaviorScore = result.behaviorScore;
      _amountScore = result.amountScore;
      _receiverScore = result.receiverScore;
      _isFlaggedReceiver = result.isFlaggedReceiver;
      _shouldBlock = result.shouldBlock;
    });
  }

  void _reportFraud() {
    setState(() {
      _isUserReported = true;
      _isSafe = false;
    });
    FraudStore.report(widget.recipient);

    // Record user-reported fraud as blocked transaction
    TransactionHistory.addTransaction(
      Transaction(
        id:
            widget.transactionId ??
            "RPT-${DateTime.now().millisecondsSinceEpoch}",
        recipient: widget.recipient,
        amount: widget.amount,
        riskScore: _riskScore,
        riskCategory: 'High',
        timestamp: DateTime.now(),
        wasBlocked: true,
      ),
    );
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text("✓ Reported ${widget.recipient} as fraud"),
        backgroundColor: AppTheme.errorColor,
      ),
    );
  }

  void _handleSimulatedPayment(Map<String, dynamic> result) {
    // Handle simulated payment result (for desktop/web)
    if (result['status'] == 'success') {
      // Payment successful! Navigate to success screen
      if (mounted) {
        // Log successful transaction
        TransactionHistory.addTransaction(
          Transaction(
            id:
                widget.transactionId ??
                "TXN-${DateTime.now().millisecondsSinceEpoch}",
            recipient: widget.recipient,
            amount: widget.amount,
            riskScore: _riskScore,
            riskCategory: _riskCategory.toString().split('.').last,
            timestamp: DateTime.now(),
            wasBlocked: false,
          ),
        );

        FraudStore.addTransaction(
          receiver: widget.recipient,
          amount: widget.amount,
          risk: _riskCategory == RiskCategory.high
              ? 'high'
              : (_riskCategory == RiskCategory.medium ? 'medium' : 'low'),
          timestamp: DateTime.now(),
        );

        Navigator.pushReplacement(
          context,
          MaterialPageRoute(
            builder: (context) => PaymentSuccessScreen(
              amount: widget.amount,
              recipient: widget.recipient,
              utrNumber: result['utr_number'],
              pspName: result['psp_name'],
              transactionId: widget.transactionId,
            ),
          ),
        );
      }
    } else {
      // Payment failed
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Payment failed: ${result['message']}'),
            backgroundColor: AppTheme.errorColor,
          ),
        );
      }
    }
  }

  @override
  void dispose() {
    _fadeController.dispose();
    super.dispose();
  }

  Color _getRiskColor() {
    if (_isUserReported || !_isSafe) return AppTheme.errorColor;

    // If backend provided a color, use it
    if (widget.riskResult?.color != null) {
      try {
        final colorStr = widget.riskResult!.color!.replaceFirst('#', '0xFF');
        return Color(int.parse(colorStr));
      } catch (e) {
        print("Error parsing backend color: $e");
      }
    }

    if (_riskScore < 0.4) return AppTheme.successColor;
    if (_riskScore < 0.7) return Colors.orange;
    return AppTheme.errorColor;
  }

  Widget _buildLayerSummaryItem(
    IconData icon,
    String label,
    String description,
    Color color,
    Color textColor,
  ) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.all(6),
            decoration: BoxDecoration(
              color: color.withOpacity(0.1),
              shape: BoxShape.circle,
            ),
            child: Icon(icon, size: 14, color: color),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  label,
                  style: TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.bold,
                    color: color,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  description,
                  style: TextStyle(fontSize: 13, color: textColor, height: 1.3),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  String _getRiskTitle() {
    if (_isUserReported || !_isSafe) return "Fraud Detected";

    // If backend provided a label, use it
    if (widget.riskResult?.label != null) {
      return widget.riskResult!.label!;
    }

    switch (_riskCategory) {
      case RiskCategory.low:
        return "Low Risk Detected";
      case RiskCategory.medium:
        return "Moderate Risk Warning";
      case RiskCategory.high:
        return "High Risk Alert";
    }
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final bgColor = isDark
        ? AppTheme.darkBackgroundColor
        : const Color(0xFFF8FAFC);
    final cardColor = isDark ? AppTheme.darkCardColor : Colors.white;
    final textColor = isDark
        ? AppTheme.darkTextPrimary
        : const Color(0xFF0F172A);
    final secondaryColor = isDark
        ? AppTheme.darkTextSecondary
        : const Color(0xFF64748B);

    return Scaffold(
      backgroundColor: bgColor,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        leading: IconButton(
          icon: Icon(
            Icons.arrow_back_ios_new_rounded,
            size: 20,
            color: textColor,
          ),
          onPressed: () => Navigator.pop(context),
        ),
        centerTitle: true,
        title: Text(
          "Risk Analysis",
          style: TextStyle(
            color: textColor,
            fontWeight: FontWeight.bold,
            fontSize: 16,
          ),
        ),
      ),
      body: FadeTransition(
        opacity: _fadeAnimation,
        child: Column(
          children: [
            Expanded(
              child: SingleChildScrollView(
                padding: const EdgeInsets.symmetric(horizontal: 24),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.center,
                  children: [
                    const SizedBox(height: 20),

                    // Gauge Section
                    RiskGauge(
                      score: _riskScore,
                      riskCategory: _riskCategory == RiskCategory.high
                          ? 'high'
                          : _riskCategory == RiskCategory.medium
                          ? 'medium'
                          : 'low',
                    ),

                    const SizedBox(height: 30),

                    // Headline
                    Text(
                      _getRiskTitle(),
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        fontSize: 22,
                        fontWeight: FontWeight.bold,
                        color: _getRiskColor(),
                        letterSpacing: -0.5,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      "AI-powered fraud detection analysis",
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        fontSize: 12,
                        color: secondaryColor,
                        height: 1.4,
                      ),
                    ),
                    const SizedBox(height: 16),

                    // Behavioral Profile Status
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 16,
                        vertical: 8,
                      ),
                      decoration: BoxDecoration(
                        color:
                            (_isLocalAnalysis
                                    ? Colors.blue
                                    : const Color(0xFF4F46E5))
                                .withOpacity(0.05),
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(
                          color:
                              (_isLocalAnalysis
                                      ? Colors.blue
                                      : const Color(0xFF4F46E5))
                                  .withOpacity(0.1),
                        ),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(
                            _isLocalAnalysis
                                ? Icons.security_rounded
                                : Icons.psychology_rounded,
                            size: 16,
                            color: _isLocalAnalysis
                                ? Colors.blue
                                : const Color(0xFF4F46E5),
                          ),
                          const SizedBox(width: 8),
                          Text(
                            _isLocalAnalysis
                                ? "Secure Local Verification"
                                : "AI Multi-Layer Analysis",
                            style: TextStyle(
                              fontSize: 11,
                              fontWeight: FontWeight.bold,
                              color: _isLocalAnalysis
                                  ? Colors.blue
                                  : const Color(0xFF4F46E5),
                            ),
                          ),
                        ],
                      ),
                    ),

                    const SizedBox(height: 32),

                    // Community Alert
                    CommunityAlertWidget(recipientId: widget.recipient),

                    const SizedBox(height: 16),

                    // Risk Factor Breakdown (NEW!)
                    RiskFactorBreakdown(
                      behaviorScore: _behaviorScore,
                      amountScore: _amountScore,
                      receiverScore: _receiverScore,
                      overallRisk: _riskCategory == RiskCategory.high
                          ? 'high'
                          : _riskCategory == RiskCategory.medium
                          ? 'medium'
                          : 'low',
                    ),

                    const SizedBox(height: 16),

                    // Factors Card — Data-Driven
                    Container(
                      width: double.infinity,
                      padding: const EdgeInsets.all(20),
                      decoration: BoxDecoration(
                        color: cardColor,
                        borderRadius: BorderRadius.circular(20),
                        border: Border.all(
                          color: isDark
                              ? const Color(0xFF334155)
                              : const Color(0xFFE5E7EB),
                        ),
                        boxShadow: [
                          BoxShadow(
                            color: Colors.black.withOpacity(
                              isDark ? 0.3 : 0.04,
                            ),
                            blurRadius: 10,
                            offset: const Offset(0, 4),
                          ),
                        ],
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          // —— FLAGGED RECEIVER BANNER ——
                          if (_isFlaggedReceiver)
                            Container(
                              margin: const EdgeInsets.only(bottom: 16),
                              padding: const EdgeInsets.symmetric(
                                horizontal: 14,
                                vertical: 12,
                              ),
                              decoration: BoxDecoration(
                                color: const Color(0xFFEF4444).withOpacity(0.1),
                                borderRadius: BorderRadius.circular(10),
                                border: Border.all(
                                  color: const Color(0xFFEF4444),
                                  width: 1.5,
                                ),
                              ),
                              child: Row(
                                children: [
                                  const Icon(
                                    Icons.flag_rounded,
                                    color: Color(0xFFEF4444),
                                    size: 18,
                                  ),
                                  const SizedBox(width: 10),
                                  Expanded(
                                    child: Text(
                                      "You previously flagged this receiver. This is a known fraudster in your account.",
                                      style: const TextStyle(
                                        color: Color(0xFFEF4444),
                                        fontSize: 13,
                                        fontWeight: FontWeight.w600,
                                        height: 1.4,
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          Text(
                            "ANALYSIS FACTORS",
                            style: TextStyle(
                              fontSize: 11,
                              fontWeight: FontWeight.bold,
                              color: secondaryColor.withOpacity(0.7),
                              letterSpacing: 1.2,
                            ),
                          ),
                          const SizedBox(height: 16),
                          // Layer summary items
                          _buildLayerSummaryItem(
                            Icons.people_alt_rounded,
                            "Behavior Analysis",
                            _behaviorScore < 0.35
                                ? "Trusted receiver — previous transactions found"
                                : _behaviorScore < 0.7
                                ? "Limited transaction history with this receiver"
                                : "First-time receiver — no prior transactions",
                            _behaviorScore < 0.35
                                ? (_riskCategory == RiskCategory.low
                                      ? const Color(0xFF10B981)
                                      : const Color(0xFFF59E0B))
                                : _behaviorScore < 0.7
                                ? const Color(0xFFF59E0B)
                                : const Color(0xFFEF4444),
                            textColor,
                          ),
                          _buildLayerSummaryItem(
                            Icons.currency_rupee_rounded,
                            "Amount Analysis",
                            _amountScore < 0.35
                                ? "Amount is within your normal spending range"
                                : _amountScore < 0.7
                                ? "Amount is slightly above your usual average"
                                : "Amount is far above your usual average",
                            _amountScore < 0.35
                                ? (_riskCategory == RiskCategory.low
                                      ? const Color(0xFF10B981)
                                      : const Color(0xFFF59E0B))
                                : _amountScore < 0.7
                                ? const Color(0xFFF59E0B)
                                : const Color(0xFFEF4444),
                            textColor,
                          ),
                          _buildLayerSummaryItem(
                            Icons.account_circle_rounded,
                            "Receiver Analysis",
                            _receiverScore < 0.35
                                ? "Receiver appears clean — no fraud signals found"
                                : _receiverScore < 0.7
                                ? "Some risk patterns detected for this receiver"
                                : "High fraud risk — multiple fraud flags detected",
                            _receiverScore < 0.35
                                ? (_riskCategory == RiskCategory.low
                                      ? const Color(0xFF10B981)
                                      : const Color(0xFFF59E0B))
                                : _receiverScore < 0.7
                                ? const Color(0xFFF59E0B)
                                : const Color(0xFFEF4444),
                            textColor,
                          ),
                          if (_riskFactors.isNotEmpty)
                            Divider(
                              height: 24,
                              color: textColor.withOpacity(0.08),
                            ),
                          ..._riskFactors.map((factor) {
                            // Parse severity for color
                            final severity = factor.toLowerCase();
                            Color iconColor;
                            IconData iconData;

                            if (severity.contains("impossible travel") ||
                                severity.contains("extreme amount") ||
                                severity.contains("suspicious receiver") ||
                                severity.contains("flagged this receiver") ||
                                severity.contains("previously flagged")) {
                              iconColor = const Color(0xFFEF4444); // Red
                              iconData = Icons.error_rounded;
                            } else if (severity.contains("first-time") ||
                                severity.contains("unusually large")) {
                              iconColor = const Color(0xFFF97316); // Orange
                              iconData = Icons.warning_rounded;
                            } else if (severity.contains("unusual time") ||
                                severity.contains("above-average") ||
                                severity.contains("rarely") ||
                                severity.contains("exceeds") ||
                                severity.contains("moderate")) {
                              iconColor = const Color(0xFFF59E0B); // Amber
                              iconData = Icons.info_rounded;
                            } else if (severity.contains("all checks passed") ||
                                severity.contains("safe")) {
                              iconColor = const Color(0xFF10B981); // Green
                              iconData = Icons.check_circle_rounded;
                            } else {
                              iconColor = _isSafe
                                  ? const Color(0xFF10B981)
                                  : const Color(0xFFF59E0B);
                              iconData = _isSafe
                                  ? Icons.check_rounded
                                  : Icons.priority_high_rounded;
                            }

                            return Padding(
                              padding: const EdgeInsets.only(bottom: 12.0),
                              child: Row(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Container(
                                    padding: const EdgeInsets.all(6),
                                    decoration: BoxDecoration(
                                      color: iconColor.withOpacity(0.1),
                                      shape: BoxShape.circle,
                                    ),
                                    child: Icon(
                                      iconData,
                                      size: 14,
                                      color: iconColor,
                                    ),
                                  ),
                                  const SizedBox(width: 12),
                                  Expanded(
                                    child: Text(
                                      factor,
                                      style: TextStyle(
                                        fontSize: 14,
                                        fontWeight: FontWeight.w600,
                                        color: textColor,
                                        height: 1.4,
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                            );
                          }),
                        ],
                      ),
                    ),

                    const SizedBox(height: 24),
                  ],
                ),
              ),
            ),

            // Bottom Action
            Container(
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                color: cardColor,
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withOpacity(isDark ? 0.3 : 0.05),
                    blurRadius: 20,
                    offset: const Offset(0, -5),
                  ),
                ],
              ),
              child: SafeArea(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    // All risk levels show a pay button — HIGH risk shows a stronger warning
                    Column(
                      children: [
                        // Warning banner for MEDIUM and HIGH risk
                        if (_riskCategory == RiskCategory.medium ||
                            _riskCategory == RiskCategory.high ||
                            _isUserReported)
                          Container(
                            width: double.infinity,
                            padding: const EdgeInsets.all(16),
                            margin: const EdgeInsets.only(bottom: 16),
                            decoration: BoxDecoration(
                              color:
                                  (_riskCategory == RiskCategory.high ||
                                      _isUserReported)
                                  ? AppTheme.errorColor.withOpacity(0.1)
                                  : const Color(0xFFFF9800).withOpacity(0.1),
                              borderRadius: BorderRadius.circular(12),
                              border: Border.all(
                                color:
                                    (_riskCategory == RiskCategory.high ||
                                        _isUserReported)
                                    ? AppTheme.errorColor.withOpacity(0.4)
                                    : const Color(0xFFFF9800).withOpacity(0.3),
                                width: 1.5,
                              ),
                            ),
                            child: Row(
                              children: [
                                Icon(
                                  (_riskCategory == RiskCategory.high ||
                                          _isUserReported)
                                      ? Icons.dangerous_rounded
                                      : Icons.warning_amber_rounded,
                                  color:
                                      (_riskCategory == RiskCategory.high ||
                                          _isUserReported)
                                      ? AppTheme.errorColor
                                      : const Color(0xFFFF9800),
                                  size: 24,
                                ),
                                const SizedBox(width: 12),
                                Expanded(
                                  child: Text(
                                    (_riskCategory == RiskCategory.high ||
                                            _isUserReported)
                                        ? "High fraud risk detected. This receiver has been flagged in your account. You can still pay, but proceed only if you are absolutely sure."
                                        : "We suggest you verify the account before proceeding with this transaction.",
                                    style: TextStyle(
                                      color: isDark
                                          ? AppTheme.darkTextPrimary
                                          : const Color(0xFF1F2937),
                                      fontSize: 13,
                                      fontWeight: FontWeight.w500,
                                      height: 1.4,
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          ),

                        // ── BLOCKED STATE: receiver RED + amount RED ─────
                        if (_shouldBlock) ...[
                          Container(
                            width: double.infinity,
                            padding: const EdgeInsets.all(16),
                            margin: const EdgeInsets.only(bottom: 12),
                            decoration: BoxDecoration(
                              color: const Color(0xFFFFEEEE),
                              borderRadius: BorderRadius.circular(16),
                              border: Border.all(color: const Color(0xFFFFCDD2)),
                            ),
                            child: Column(
                              children: [
                                const Icon(Icons.block_rounded,
                                    color: Color(0xFFD32F2F), size: 36),
                                const SizedBox(height: 10),
                                const Text(
                                  'Transaction Blocked',
                                  style: TextStyle(
                                    fontFamily: 'Manrope',
                                    fontWeight: FontWeight.w800,
                                    fontSize: 17,
                                    color: Color(0xFFD32F2F),
                                  ),
                                ),
                                const SizedBox(height: 6),
                                const Text(
                                  'Our fraud engine has blocked this payment.\nSuspicious receiver + unusually high amount detected.',
                                  textAlign: TextAlign.center,
                                  style: TextStyle(
                                    fontFamily: 'Manrope',
                                    fontSize: 13,
                                    color: Color(0xFF666666),
                                    height: 1.5,
                                  ),
                                ),
                                const SizedBox(height: 12),
                                Row(
                                  children: [
                                    Expanded(
                                      child: Container(
                                        padding: const EdgeInsets.all(10),
                                        decoration: BoxDecoration(
                                          color: const Color(0xFFFFF3F3),
                                          borderRadius: BorderRadius.circular(10),
                                          border: Border.all(color: const Color(0xFFFFCDD2)),
                                        ),
                                        child: Column(
                                          children: [
                                            const Text('Receiver Risk',
                                                style: TextStyle(fontFamily: 'Manrope', fontSize: 11, color: Color(0xFF666666))),
                                            Text('${(_receiverScore * 100).toStringAsFixed(0)}/100',
                                                style: const TextStyle(fontFamily: 'Manrope', fontWeight: FontWeight.w700, fontSize: 14, color: Color(0xFFD32F2F))),
                                          ],
                                        ),
                                      ),
                                    ),
                                    const SizedBox(width: 8),
                                    Expanded(
                                      child: Container(
                                        padding: const EdgeInsets.all(10),
                                        decoration: BoxDecoration(
                                          color: const Color(0xFFFFF3F3),
                                          borderRadius: BorderRadius.circular(10),
                                          border: Border.all(color: const Color(0xFFFFCDD2)),
                                        ),
                                        child: Column(
                                          children: [
                                            const Text('Amount Risk',
                                                style: TextStyle(fontFamily: 'Manrope', fontSize: 11, color: Color(0xFF666666))),
                                            Text('${(_amountScore * 100).toStringAsFixed(0)}/100',
                                                style: const TextStyle(fontFamily: 'Manrope', fontWeight: FontWeight.w700, fontSize: 14, color: Color(0xFFD32F2F))),
                                          ],
                                        ),
                                      ),
                                    ),
                                  ],
                                ),
                              ],
                            ),
                          ),
                          SizedBox(
                            width: double.infinity,
                            child: ElevatedButton.icon(
                              onPressed: null, // disabled — cannot proceed
                              icon: const Icon(Icons.block_rounded, color: Colors.white54),
                              label: const Text(
                                'Payment Blocked',
                                style: TextStyle(
                                  fontFamily: 'Manrope',
                                  fontWeight: FontWeight.w700,
                                  fontSize: 15,
                                  color: Colors.white54,
                                ),
                              ),
                              style: ElevatedButton.styleFrom(
                                backgroundColor: const Color(0xFFB71C1C),
                                disabledBackgroundColor: const Color(0xFFB71C1C),
                                shape: RoundedRectangleBorder(
                                    borderRadius: BorderRadius.circular(14)),
                                padding: const EdgeInsets.symmetric(vertical: 16),
                              ),
                            ),
                          ),
                        ] else ...[

                        // Payment button
                        CustomButton(
                          text: _riskCategory == RiskCategory.low
                              ? "Pay Now"
                              : _riskCategory == RiskCategory.high ||
                                    _isUserReported
                              ? "Proceed Anyway"
                              : "Pay Anyway",
                          isPrimary: true,
                          color: _riskCategory == RiskCategory.low
                              ? null
                              : _riskCategory == RiskCategory.high ||
                                    _isUserReported
                              ? AppTheme.errorColor
                              : const Color(0xFFFF9800),
                          onPressed: () async {
                            // HIGH risk: show strong confirmation dialog
                            if (_riskCategory == RiskCategory.high ||
                                _isUserReported) {
                              final confirmed = await showDialog<bool>(
                                context: context,
                                builder: (ctx) => AlertDialog(
                                  shape: RoundedRectangleBorder(
                                    borderRadius: BorderRadius.circular(16),
                                  ),
                                  title: Row(
                                    children: [
                                      Icon(
                                        Icons.dangerous_rounded,
                                        color: AppTheme.errorColor,
                                        size: 26,
                                      ),
                                      const SizedBox(width: 10),
                                      const Text(
                                        "High Risk — Are You Sure?",
                                        style: TextStyle(fontSize: 16),
                                      ),
                                    ],
                                  ),
                                  content: Text(
                                    "This receiver has been flagged as high risk in your account.\n\nSentraPay strongly advises against this payment. If you proceed, you do so at your own risk.\n\nAre you absolutely sure you want to pay \"${widget.recipient}\"?",
                                    style: const TextStyle(
                                      fontSize: 14,
                                      height: 1.5,
                                    ),
                                  ),
                                  actions: [
                                    TextButton(
                                      onPressed: () =>
                                          Navigator.pop(ctx, false),
                                      child: const Text(
                                        "Cancel",
                                        style: TextStyle(color: Colors.grey),
                                      ),
                                    ),
                                    ElevatedButton(
                                      style: ElevatedButton.styleFrom(
                                        backgroundColor: AppTheme.errorColor,
                                        foregroundColor: Colors.white,
                                        shape: RoundedRectangleBorder(
                                          borderRadius: BorderRadius.circular(
                                            8,
                                          ),
                                        ),
                                      ),
                                      onPressed: () => Navigator.pop(ctx, true),
                                      child: const Text(
                                        "Yes, I Accept the Risk",
                                      ),
                                    ),
                                  ],
                                ),
                              );
                              if (confirmed != true) return;
                            }
                            // MODERATE risk: show confirmation dialog first
                            else if (_riskCategory == RiskCategory.medium) {
                              final confirmed = await showDialog<bool>(
                                context: context,
                                builder: (ctx) => AlertDialog(
                                  shape: RoundedRectangleBorder(
                                    borderRadius: BorderRadius.circular(16),
                                  ),
                                  title: const Row(
                                    children: [
                                      Icon(
                                        Icons.warning_amber_rounded,
                                        color: Color(0xFFFF9800),
                                        size: 26,
                                      ),
                                      SizedBox(width: 10),
                                      Text(
                                        "Double-Check Wisely",
                                        style: TextStyle(fontSize: 17),
                                      ),
                                    ],
                                  ),
                                  content: Text(
                                    "This transaction has moderate risk signals.\n\nAre you sure you want to proceed? Verify the receiver \"${widget.recipient}\" before paying.",
                                    style: const TextStyle(
                                      fontSize: 14,
                                      height: 1.5,
                                    ),
                                  ),
                                  actions: [
                                    TextButton(
                                      onPressed: () =>
                                          Navigator.pop(ctx, false),
                                      child: const Text(
                                        "Cancel",
                                        style: TextStyle(color: Colors.grey),
                                      ),
                                    ),
                                    ElevatedButton(
                                      style: ElevatedButton.styleFrom(
                                        backgroundColor: const Color(
                                          0xFFFF9800,
                                        ),
                                        foregroundColor: Colors.white,
                                        shape: RoundedRectangleBorder(
                                          borderRadius: BorderRadius.circular(
                                            8,
                                          ),
                                        ),
                                      ),
                                      onPressed: () => Navigator.pop(ctx, true),
                                      child: const Text("Yes, Pay Anyway"),
                                    ),
                                  ],
                                ),
                              );
                              if (confirmed != true) return; // user cancelled
                            }

                            // ── UPI App Selector ────────────────────────
                            if (!mounted) return;
                            final selectedApp = await showUpiAppSelector(
                              context,
                              amount: widget.amount,
                              receiverUpi: widget.recipient,
                            );
                            if (selectedApp == null || !mounted) return;

                            // Check if we have transaction ID from backend
                            if (widget.transactionId != null) {
                              // Get auth token
                              final authProvider = Provider.of<AuthProvider>(
                                context,
                                listen: false,
                              );
                              final token = authProvider.token ?? "demo-token";

                              // Call payment execution API (Now uses /execute)
                              final result = await ApiService.confirmPayment(
                                transactionId: widget.transactionId!,
                                token: token,
                                amount: widget.amount,
                                receiver: widget.recipient,
                                userAcknowledged: true,
                              );

                              if (result != null) {
                                final isMobile =
                                    !kIsWeb &&
                                    (Platform.isAndroid || Platform.isIOS);

                                if (isMobile) {
                                  // MOBILE: Launch selected UPI app via deep-link
                                  final appUri = selectedApp.buildUri(
                                    receiverUpi: widget.recipient,
                                    amount: widget.amount,
                                    payeeName: widget.recipient
                                        .split('@')
                                        .first,
                                  );
                                  print(
                                    '🚀 Launching ${selectedApp.name}: $appUri',
                                  );

                                  try {
                                    final uri = appUri;
                                    final canLaunch = await canLaunchUrl(uri);

                                    if (canLaunch) {
                                      await launchUrl(
                                        uri,
                                        mode: LaunchMode.externalApplication,
                                      );

                                      // Show message that user should complete payment in PSP app
                                      if (mounted) {
                                        ScaffoldMessenger.of(
                                          context,
                                        ).showSnackBar(
                                          const SnackBar(
                                            content: Text(
                                              'Complete payment in your UPI app',
                                            ),
                                            duration: Duration(seconds: 3),
                                          ),
                                        );
                                      }

                                      // In real app, you'd wait for callback from PSP app
                                      // For now, navigate to success screen after delay
                                      await Future.delayed(
                                        const Duration(seconds: 3),
                                      );

                                      if (result['status'] == 'success' &&
                                          mounted) {
                                        // Log successful transaction
                                        TransactionHistory.addTransaction(
                                          Transaction(
                                            id:
                                                widget.transactionId ??
                                                "TXN-${DateTime.now().millisecondsSinceEpoch}",
                                            recipient: widget.recipient,
                                            amount: widget.amount,
                                            riskScore: _riskScore,
                                            riskCategory: _riskCategory
                                                .toString()
                                                .split('.')
                                                .last,
                                            timestamp: DateTime.now(),
                                            wasBlocked: false,
                                          ),
                                        );

                                        FraudStore.addTransaction(
                                          receiver: widget.recipient,
                                          amount: widget.amount,
                                          risk:
                                              _riskCategory == RiskCategory.high
                                              ? 'high'
                                              : (_riskCategory ==
                                                        RiskCategory.medium
                                                    ? 'medium'
                                                    : 'low'),
                                          timestamp: DateTime.now(),
                                        );

                                        Navigator.pushReplacement(
                                          context,
                                          MaterialPageRoute(
                                            builder: (context) =>
                                                PaymentSuccessScreen(
                                                  amount: widget.amount,
                                                  recipient: widget.recipient,
                                                  utrNumber:
                                                      result['utr_number'],
                                                  pspName: result['psp_name'],
                                                  transactionId:
                                                      widget.transactionId,
                                                ),
                                          ),
                                        );
                                      }
                                    } else {
                                      print('❌ Cannot launch UPI link');
                                      // Fallback to simulated payment
                                      _handleSimulatedPayment({
                                        ...result,
                                        'psp_name': selectedApp.name,
                                      });
                                    }
                                  } catch (e) {
                                    print('Error launching UPI: $e');
                                    _handleSimulatedPayment({
                                      ...result,
                                      'psp_name': selectedApp.name,
                                    });
                                  }
                                } else {
                                  // DESKTOP/WEB: Use simulated payment flow
                                  print(
                                    '💻 Desktop/Web mode - simulated payment via ${selectedApp.name}',
                                  );
                                  _handleSimulatedPayment({
                                    ...result,
                                    'psp_name': selectedApp.name,
                                  });
                                }
                              } else {
                                // API call failed
                                if (mounted) {
                                  ScaffoldMessenger.of(context).showSnackBar(
                                    const SnackBar(
                                      content: Text(
                                        'Failed to process payment. Please try again.',
                                      ),
                                      backgroundColor: AppTheme.errorColor,
                                    ),
                                  );
                                }
                              }
                            } else {
                              // Fallback: No transaction ID (local mode)
                              // Save to local history even if backend is down
                              TransactionHistory.addTransaction(
                                Transaction(
                                  id: "LOC-TXN-${DateTime.now().millisecondsSinceEpoch}",
                                  recipient: widget.recipient,
                                  amount: widget.amount,
                                  riskScore: _riskScore,
                                  riskCategory: _riskCategory
                                      .toString()
                                      .split('.')
                                      .last,
                                  timestamp: DateTime.now(),
                                  wasBlocked: false,
                                ),
                              );

                              FraudStore.addTransaction(
                                receiver: widget.recipient,
                                amount: widget.amount,
                                risk: _riskCategory == RiskCategory.high
                                    ? 'high'
                                    : (_riskCategory == RiskCategory.medium
                                          ? 'medium'
                                          : 'low'),
                                timestamp: DateTime.now(),
                              );

                              Navigator.push(
                                context,
                                MaterialPageRoute(
                                  builder: (context) => PaymentSuccessScreen(
                                    amount: widget.amount,
                                    recipient: widget.recipient,
                                    pspName: selectedApp.name,
                                  ),
                                ),
                              );
                            }
                          },
                        ),
                        ], // end else (not blocked)
                      ],
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
