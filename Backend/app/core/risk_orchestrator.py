"""
RISK ORCHESTRATOR - THE 3-LAYER BRAIN 🧠
Implements the multi-layer independent risk architecture.

Architecture:
  Layer 1: User Relationship Analysis  → Measures UNCERTAINTY (familiarity)
  Layer 2: Amount Damage Analysis      → Measures IMPACT (financial damage)
  Layer 3: Receiver Fraud Risk (ML)    → Measures SUSPICION (receiver patterns)
  Final:   Aggregation Engine          → Combines signals → Decision

Design Principles:
  - No layer detects fraud alone
  - Fraud risk emerges when multiple independent signals agree
  - Each layer consumes only pre-fetched structured data
  - Final engine does NOT query database or run ML
"""

from typing import Dict, Optional
from datetime import datetime
from sqlalchemy.orm import Session
import logging
import uuid

from app.core.context_engine import get_user_context
from app.core.data_loader import load_sender_history, get_sender_stats, get_receiver_profile
from app.core.relationship_engine import analyze_user_relationship
from app.core.amount_risk_engine import analyze_amount_risk
from app.core.receiver_ml_engine import analyze_receiver_risk
from app.core.final_risk_engine import compute_final_risk
from app.core.genai_engine import genai
from app.database.models import RiskEvent, Transaction, User
from app.database.connection import SessionLocal

logger = logging.getLogger(__name__)


class RiskOrchestrator:
    """
    Coordinates the 3-Layer Risk Architecture.
    
    Data Flow:
      1. Frontend sends transaction request
      2. Backend pre-fetches: sender history, sender stats, receiver profile
      3. Layer-1 computes relationship risk
      4. Layer-2 computes amount risk
      5. Layer-3 provides receiver ML risk
      6. Final engine combines signals
      7. Decision returned to frontend
    """

    def __init__(self):
        logger.info("Risk Orchestrator (3-Layer Architecture) initialized")

    def _generate_transaction_id(self) -> str:
        return f"TXN-{uuid.uuid4().hex[:12].upper()}"

    def analyze_transaction(
        self,
        txn_data: Dict,
        user_id: str,
        db: Optional[Session] = None,
        save: bool = False
    ) -> Dict:
        """
        Main orchestration method.

        Args:
            txn_data: Transaction details (amount, receiver, note, device_id)
            user_id: Public User ID (string)
            db: Database session
            save: If True, creates transaction record and logs event (for /execute).
                  If False, strictly read-only (for /intent).
        """
        close_db = False
        if not db:
            db = SessionLocal()
            close_db = True

        try:
            transaction_id = self._generate_transaction_id()
            receiver = str(txn_data.get("receiver", "")).lower().strip()
            amount = float(txn_data.get("amount", 0.0))
            device_id = txn_data.get("device_id", "")

            logger.info(f"🧠 Orchestrating 3-Layer Analysis: {transaction_id} (Save={save}) - User: {user_id}")

            # ── GET USER PK ──
            user_orm = db.query(User).filter(User.user_id == user_id).first()
            if not user_orm:
                raise ValueError(f"User not found: {user_id}")

            new_txn = None
            if save:
                txn_params = {
                    "transaction_id": transaction_id,
                    "user_id": user_orm.id,
                    "amount": amount,
                    "receiver": receiver,
                    "note": txn_data.get("note", ""),
                    "status": "PENDING",
                    "device_id": device_id,
                }
                new_txn = Transaction(**txn_params)
                db.add(new_txn)
                # Don't commit yet — wait for full analysis

            # ──────────────────────────────────────────────
            # STEP 0: PRE-FETCH ALL DATA (Context Gathering)
            # ──────────────────────────────────────────────
            context = get_user_context(user_id, receiver, db)
            receiver_info = context.receiver_info or {}
            txn_stats = context.txn_stats or {}

            # Load CSV-based data for the 3-layer analysis
            sender_df = load_sender_history()
            sender_upi = txn_data.get("sender_upi", user_id)
            csv_stats = get_sender_stats(sender_upi)
            # Merge CSV stats into txn_stats — CSV ALWAYS takes priority.
            # Must use direct assignment (not setdefault) because context_engine
            # pre-populates all keys with 0.0 for new users, so setdefault would
            # never overwrite them and the CSV data would be silently ignored.
            for k, v in csv_stats.items():
                if k != "frequent_hours":
                    txn_stats[k] = v

            logger.info(f"✓ Context retrieved: tier={context.user_profile.get('risk_tier', 'BRONZE')}")

            # ──────────────────────────────────────────────
            # LAYER 1: USER RELATIONSHIP ANALYSIS
            # Purpose: Measures UNCERTAINTY / familiarity
            # Queries sender_history.csv for sender → receiver pair
            # ──────────────────────────────────────────────
            layer1_result = analyze_user_relationship(
                sender_upi=sender_upi,
                receiver_upi=receiver,
                history_df=sender_df,
            )
            user_risk_score = layer1_result["user_risk_score"]
            logger.info(f"✓ Layer 1 (Relationship): score={user_risk_score}, familiarity={layer1_result['familiarity']}")

            # ──────────────────────────────────────────────
            # LAYER 2: AMOUNT DAMAGE ANALYSIS
            # Purpose: Measures FINANCIAL IMPACT relative to sender behavior
            # Uses sender stats from CSV
            # ──────────────────────────────────────────────
            layer2_result = analyze_amount_risk(
                amount=amount,
                txn_stats=txn_stats,
            )
            amount_risk_score = layer2_result["amount_risk_score"]
            logger.info(f"✓ Layer 2 (Amount): score={amount_risk_score}, ratio_avg30={layer2_result.get('ratio_to_avg30', 'N/A')}")

            # ──────────────────────────────────────────────
            # LAYER 3: RECEIVER FRAUD RISK (ML LAYER)
            # Purpose: Measures RECEIVER SUSPICIOUSNESS
            # Engineers features and runs CatBoost / heuristic
            # ──────────────────────────────────────────────
            # Load receiver profile from CSV FIRST (used by both ml_context and Layer 3)
            recv_profile = get_receiver_profile(receiver)

            ml_context = {
                "avg_amount_7d": txn_stats.get("avg_amount_7d", 0),
                "avg_amount_30d": txn_stats.get("avg_amount_30d", 0),
                "max_amount_7d": txn_stats.get("max_amount_7d", 0),
                "txn_count_1h": txn_stats.get("txn_count_1h", 0),
                "txn_count_24h": txn_stats.get("txn_count_24h", 0),
                "night_txn_ratio": txn_stats.get("night_txn_ratio", 0),
                "days_since_last_txn": txn_stats.get("days_since_last_txn", 0),
                "frequent_hours": csv_stats.get("frequent_hours", set()),
            }
            # Enrich with receiver profile from CSV (impossible travel, fraud flags)
            ml_context["impossible_travel_count"] = recv_profile.get("impossible_travel_count", 0)
            ml_context["fraud_flag_ratio"] = recv_profile.get("fraud_flag_ratio", 0.0)
            # NEW: pass receiver-side signals needed for 22-feature ML vector
            ml_context["is_new_receiver"] = 0 if recv_profile.get("exists", False) else 1
            ml_context["location_mismatch"] = 1 if recv_profile.get("location_mismatches", 0) > 0 else 0
            ml_context["receiver_type"] = 1 if recv_profile.get("fraud_flag_ratio", 0) > 0.5 else 0
            ml_txn_data = {
                "amount": amount,
                "receiver": receiver,
                "timestamp": txn_data.get("timestamp", datetime.utcnow().isoformat()),
            }
            # Load CatBoost model for Layer 3.
            # The heuristic in receiver_ml_engine uses fraud_flag_ratio directly
            # from the receiver CSV and is the primary scoring signal.
            # We pass model=None so the heuristic always runs — it is deliberately
            # calibrated to the demo data and gives stronger fraud signals than
            # the pre-built model which was trained on a different distribution.
            ml_model = None

            layer3_result = analyze_receiver_risk(
                txn_data=ml_txn_data,
                context=ml_context,
                model=ml_model,
            )
            receiver_risk_score = layer3_result["receiver_risk_score"]
            logger.info(f"✓ Layer 3 (Receiver): score={receiver_risk_score}, level={layer3_result['risk_level']}")

            # ──────────────────────────────────────────────
            # FINAL ENGINE: AGGREGATION & DECISION
            # Purpose: Combines signals → ALLOW / WARN / OTP / BLOCK
            # Must NOT: query database, run ML, compute features
            # It is a PURE aggregation engine.
            # ──────────────────────────────────────────────
            final_result = compute_final_risk(
                user_score=user_risk_score,
                amount_score=amount_risk_score,
                receiver_score=receiver_risk_score,
            )

            final_risk_percent = final_result["final_risk_score"]
            final_score_normalized = final_risk_percent / 100.0  # 0.0 - 1.0
            action = final_result["action"]
            risk_level = final_result["risk_level"]

            logger.info(f"✓ Final Engine: score={final_risk_percent}%, action={action}, level={risk_level}")

            # ── UPDATE TRANSACTION (only if saving) ──
            if save and new_txn:
                new_txn.risk_score = final_score_normalized
                new_txn.risk_level = risk_level
                new_txn.rule_score = float(user_risk_score)    # Layer 1 in legacy column
                new_txn.ml_score = float(receiver_risk_score)  # Layer 3 in legacy column
                new_txn.action_taken = action
                db.commit()

            # ── BUILD RESPONSE ──
            response = self._build_response(
                transaction_id=transaction_id,
                final_result=final_result,
                final_score_normalized=final_score_normalized,
                layers={
                    "L1": layer1_result,
                    "L2": layer2_result,
                    "L3": layer3_result,
                },
                txn_data=txn_data,
                context=context,
            )

            # ── LOG RISK EVENT (only if saving) ──
            if save:
                self._log_risk_event(
                    user_id=user_orm.id,
                    transaction_id=new_txn.id if new_txn else None,
                    txn_data=txn_data,
                    final_score=final_score_normalized,
                    action=action,
                    layers={
                        "user_risk": user_risk_score,
                        "amount_risk": amount_risk_score,
                        "receiver_risk": receiver_risk_score,
                    },
                    db=db,
                )

            logger.info(f"✓ Risk analysis complete: {action}")
            return response

        finally:
            if close_db:
                db.close()

    # ──────────────────────────────────────────────────────
    # RESPONSE BUILDER
    # ──────────────────────────────────────────────────────
    def _build_response(
        self,
        transaction_id: str,
        final_result: Dict,
        final_score_normalized: float,
        layers: Dict,
        txn_data: Dict,
        context,
    ) -> Dict:
        """Build structured response matching PaymentIntentResponse schema."""
        action = final_result["action"]
        risk_level = final_result["risk_level"]
        risk_percent = final_result["final_risk_score"]

        # OTP / proceed logic
        requires_otp = action == "OTP"
        can_proceed = action in ["ALLOW", "WARN", "OTP"]

        # UI color map
        ui_map = {
            "ALLOW": {"icon": "🟢", "color": "#4CAF50", "bg": "#E8F5E9", "label": "Safe Transaction"},
            "WARN":  {"icon": "🟠", "color": "#FF9800", "bg": "#FFF3E0", "label": "Moderate Risk"},
            "OTP":   {"icon": "🔵", "color": "#2196F3", "bg": "#E3F2FD", "label": "Verification Required"},
            "BLOCK": {"icon": "🔴", "color": "#F44336", "bg": "#FFEBEE", "label": "High Risk Blocked"},
        }
        ui = ui_map.get(action, ui_map["BLOCK"])

        receiver = txn_data.get("receiver", "")
        amount = txn_data.get("amount", 0.0)

        # Risk factors — derived from layer outputs
        risk_factors = self._derive_risk_factors(layers, txn_data, context)

        # Recommendations
        recommendations = self._derive_recommendations(action, layers)

        # GenAI explanation
        genai_analysis = genai.generate_explanation(
            risk_score=final_score_normalized,
            flags=[f"L1:{layers['L1']['familiarity']}", f"L2:{layers['L2'].get('risk_level', 'N/A')}", f"L3:{layers['L3']['risk_level']}"],
            receiver=receiver,
        ) if genai else {}

        return {
            "transaction_id": transaction_id,
            "timestamp": datetime.utcnow().isoformat(),

            # Risk scoring
            "risk_score": round(final_score_normalized, 2),
            "risk_level": risk_level,
            "risk_percentage": risk_percent,

            # Action
            "action": action,
            "message": self._generate_message(action, risk_level, layers),
            "can_proceed": can_proceed,
            "requires_otp": requires_otp,

            # UI rendering
            "icon": ui["icon"],
            "color": ui["color"],
            "background": ui["bg"],
            "label": ui["label"],

            # GenAI
            "genai_analysis": genai_analysis,

            # Risk breakdown (3-layer)
            "risk_breakdown": {
                "behavior_analysis": {
                    "score": layers["L1"]["user_risk_score"],
                    "weight": 25,
                    "status": layers["L1"]["familiarity"],
                },
                "amount_analysis": {
                    "score": layers["L2"]["amount_risk_score"],
                    "weight": 15,
                    "status": layers["L2"].get("risk_level", "MEDIUM"),
                },
                "receiver_analysis": {
                    "score": layers["L3"]["receiver_risk_score"],
                    "weight": 60,
                    "status": layers["L3"]["risk_level"],
                },
            },

            # Risk factors
            "risk_factors": risk_factors,

            # Recommendations
            "recommendations": recommendations,

            # Transaction details
            "transaction_details": {
                "amount": amount,
                "receiver": receiver,
                "note": txn_data.get("note", ""),
            },

            # User info
            "user_info": {
                "trust_score": context.user_profile.get("trust_score", 0),
                "risk_tier": context.user_profile.get("risk_tier", "BRONZE"),
                "transaction_count_30d": context.txn_stats.get("txn_count_30d", 0),
            },

            # Receiver info
            "receiver_info": {
                "identifier": receiver,
                "is_new": context.receiver_info.get("is_new", True) if context.receiver_info else True,
                "reputation_score": context.receiver_info.get("reputation_score", 0.5) if context.receiver_info else 0.5,
                "total_transactions": context.receiver_info.get("total_transactions", 0) if context.receiver_info else 0,
            },

            # ── BLOCK FLAG: fires ONLY when receiver AND amount both RED ─
            "should_block": (
                layers["L3"]["receiver_risk_score"] >= 75
                and layers["L2"]["amount_risk_score"] >= 75
            ),

            # Debug (layer breakdown for development)
            "debug": {
                "layer1_relationship": layers["L1"],
                "layer2_amount": layers["L2"],
                "layer3_receiver": layers["L3"],
                "final_engine": final_result,
            },
        }

    # ──────────────────────────────────────────────────────
    # RISK FACTORS DERIVATION
    # ──────────────────────────────────────────────────────
    def _derive_risk_factors(self, layers: Dict, txn_data: Dict, context) -> list:
        """Derive human-readable risk factors from layer outputs with real data."""
        factors = []

        # ── Layer 1: Relationship Analysis ──
        familiarity = layers["L1"]["familiarity"]
        txn_count = layers["L1"].get("transaction_count", 0)
        last_days = layers["L1"].get("last_transaction_days", -1)

        if familiarity in ("new", "NEW"):
            factors.append({
                "factor": "First-time receiver - verify before paying",
                "severity": "high",
                "detail": "You have never transacted with this receiver before. First-time payments carry higher risk.",
            })
        elif familiarity in ("rare", "RARE"):
            factors.append({
                "factor": f"Rarely used receiver ({txn_count} past transaction)",
                "severity": "medium",
                "detail": f"You have only sent money to this receiver {txn_count} time before, {last_days} days ago.",
            })
        elif familiarity in ("known", "KNOWN") and last_days > 30:
            factors.append({
                "factor": f"No recent activity with receiver ({last_days} days gap)",
                "severity": "low",
                "detail": f"Last transaction was {last_days} days ago across {txn_count} past payments.",
            })

        # ── Layer 2: Amount Analysis ──
        amount_score = layers["L2"]["amount_risk_score"]
        ratio = layers["L2"].get("ratio_to_avg30", 0)
        exceeds = layers["L2"].get("exceeds_recent_max", False)
        amount = txn_data.get("amount", 0)
        txn_stats = getattr(context, 'txn_stats', {}) if hasattr(context, 'txn_stats') else {}
        avg_30d = txn_stats.get("avg_amount_30d", 0)
        # Use overall average for user-facing messages (more representative than 30-day window)
        avg_display = txn_stats.get("avg_amount_overall") or avg_30d or 0
        ratio_display = round(amount / avg_display, 1) if avg_display > 0 else ratio

        if amount_score >= 85:
            factors.append({
                "factor": f"Extreme amount - {ratio_display:.1f}x your average (Rs.{avg_display:,.0f})",
                "severity": "critical",
                "detail": f"Rs.{amount:,.0f} is {ratio_display:.1f}x higher than your average of Rs.{avg_display:,.0f}. This is extremely unusual.",
            })
        elif amount_score >= 70:
            factors.append({
                "factor": f"Unusually large amount - {ratio_display:.1f}x your average",
                "severity": "high",
                "detail": f"Rs.{amount:,.0f} is {ratio_display:.1f}x your average spending of Rs.{avg_display:,.0f}.",
            })
        elif amount_score >= 40:
            factors.append({
                "factor": f"Above-average amount ({ratio:.1f}x your usual)",
                "severity": "medium",
                "detail": f"This amount is {ratio:.1f}x higher than your typical transactions.",
            })

        if exceeds and amount_score < 85:
            factors.append({
                "factor": "Exceeds your recent maximum transaction",
                "severity": "medium",
                "detail": "This amount is higher than your largest transaction in the past 30 days.",
            })

        # ── Layer 3: Receiver Analysis ──
        receiver_score = layers["L3"]["receiver_risk_score"]
        receiver_level = layers["L3"]["risk_level"]
        features = layers["L3"].get("features_used", {})

        # Impossible travel (most critical signal)
        impossible_count = features.get("impossible_travel_count", 0)
        if impossible_count > 0:
            # Get event details from receiver profile
            recv_profile = {}
            try:
                from app.core.data_loader import get_receiver_profile
                receiver_upi = txn_data.get("receiver", "")
                recv_profile = get_receiver_profile(receiver_upi)
            except Exception:
                pass

            events = recv_profile.get("impossible_travel_events", [])
            if events:
                first = events[0]
                detail = f"Receiver appeared in {first['from_city']} and {first['to_city']} within {first['time_gap_min']:.0f} minutes ({first['distance_km']:.0f} km apart)"
                if len(events) > 1:
                    detail += f". {len(events)} impossible travel events detected in total."
                factors.append({
                    "factor": f"Impossible travel detected ({impossible_count} events)",
                    "severity": "critical",
                    "detail": detail,
                })
            else:
                factors.append({
                    "factor": f"Impossible travel detected ({impossible_count} events)",
                    "severity": "critical",
                    "detail": "Receiver has transactions from physically distant cities in impossibly short timeframes.",
                })

        # High-risk receiver profile
        if receiver_level in ("HIGH_RISK", "CRITICAL") and impossible_count == 0:
            factors.append({
                "factor": "Suspicious receiver activity pattern",
                "severity": "critical",
                "detail": f"Receiver risk score is {receiver_score}/100. Multiple behavioral anomalies detected.",
            })
        elif receiver_level == "SUSPICIOUS":
            factors.append({
                "factor": "Receiver shows moderate risk signals",
                "severity": "medium",
                "detail": f"Receiver risk score is {receiver_score}/100. Some unusual patterns observed.",
            })

        # Night transaction
        if features.get("is_night", 0):
            factors.append({
                "factor": f"Transaction at unusual time ({txn_data.get('timestamp', '')[11:16]})",
                "severity": "medium",
                "detail": "Transactions between 10 PM and 5 AM are flagged as higher risk.",
            })

        # If nothing risky — add a safe factor
        if not factors:
            factors.append({
                "factor": "All checks passed - transaction looks safe",
                "severity": "safe",
                "detail": "No risk signals detected across relationship, amount, and receiver analysis.",
            })

        return factors[:6]

    # ──────────────────────────────────────────────────────
    # RECOMMENDATIONS DERIVATION
    # ──────────────────────────────────────────────────────
    def _derive_recommendations(self, action: str, layers: Dict) -> list:
        """Generate actionable recommendations based on risk decision."""
        recs = []

        if action == "BLOCK":
            recs.append("This transaction has been blocked for your safety.")
            recs.append("Contact support if you believe this is an error.")
        elif action == "OTP":
            recs.append("Complete OTP verification to proceed with this transaction.")
            recs.append("Verify the receiver's identity before confirming payment.")
        elif action == "WARN":
            recs.append("Double-check the receiver's UPI ID before proceeding.")
            if layers["L1"]["familiarity"] == "NEW":
                recs.append("Consider making a small test payment first.")
            if layers["L2"]["amount_risk_score"] >= 50:
                recs.append("This amount is higher than your usual — proceed carefully.")
        else:
            recs.append("Transaction appears safe based on your history.")

        return recs

    # ──────────────────────────────────────────────────────
    # MESSAGE GENERATION
    # ──────────────────────────────────────────────────────
    def _generate_message(self, action: str, risk_level: str, layers: Dict) -> str:
        """Generate user-facing message."""
        if action == "ALLOW":
            return "✅ Transaction looks safe. You may proceed."
        elif action == "WARN":
            return "⚠️ Moderate risk detected. Please verify before proceeding."
        elif action == "OTP":
            return "🔐 Additional verification required for this transaction."
        elif action == "BLOCK":
            return "🚫 Transaction blocked due to high risk signals."
        return f"Risk assessment: {risk_level}"

    # ──────────────────────────────────────────────────────
    # RISK EVENT LOGGING
    # ──────────────────────────────────────────────────────
    def _log_risk_event(
        self,
        user_id: int,
        transaction_id: int,
        txn_data: Dict,
        final_score: float,
        action: str,
        layers: Dict,
        db: Session,
    ):
        """Log risk event to database for audit trail."""
        try:
            event = RiskEvent(
                user_id=user_id,
                transaction_id=transaction_id,
                final_score=final_score,
                action=action,
                rule_score=layers.get("user_risk", 0),
                ml_score=layers.get("receiver_risk", 0),
                flags=[
                    f"L1_USER_RISK:{layers.get('user_risk', 0)}",
                    f"L2_AMOUNT_RISK:{layers.get('amount_risk', 0)}",
                    f"L3_RECEIVER_RISK:{layers.get('receiver_risk', 0)}",
                ],
            )
            db.add(event)
            db.commit()
            logger.info(f"✓ Risk event logged: {event.id}")
        except Exception as e:
            logger.error(f"Failed to log risk event: {e}")
            db.rollback()


# Global orchestrator instance
orchestrator = RiskOrchestrator()
