from app.extensions import db
from datetime import datetime, timezone
import enum


class EthicsCategory(enum.Enum):
    FINANCIAL_MISINFORMATION = "financial_misinformation"
    # Wrong APR, fee, rate, or credit term in a financial product context
    # Highest severity — regulatory implications (CFPB, FDIC)

    HEALTH_MISINFORMATION    = "health_misinformation"
    # Wrong dosage, drug interaction, or medical claim
    # FTC, FDA implications

    DISCRIMINATORY_CONTENT   = "discriminatory_content"
    # AI providing different information based on perceived demographics
    # ECOA, Fair Housing Act implications for financial companies

    PRIVACY_VIOLATION        = "privacy_violation"
    # AI referencing PII or non-public personal information

    MISLEADING_COMPARISON    = "misleading_comparison"
    # AI presenting a competitor comparison that is factually wrong in our favor

    UNDISCLOSED_LIMITATION   = "undisclosed_limitation"
    # AI omitting material limitations (e.g. not mentioning a card's foreign transaction fee)

    REGULATORY_BREACH        = "regulatory_breach"
    # Any other output that may violate specific regulatory requirements


class EthicsSeverity(enum.Enum):
    CRITICAL  = "critical"   # Immediate legal action required — compliance must be notified today
    HIGH      = "high"       # Legal review needed within 48 hours
    MEDIUM    = "medium"     # Flag for next compliance review cycle
    LOW       = "low"        # Monitor — may escalate if pattern emerges


class AlertStatus(enum.Enum):
    OPEN       = "open"       # Not yet actioned
    ALERTED    = "alerted"    # Compliance team has been notified
    REVIEWING  = "reviewing"  # Under active legal/compliance review
    RESOLVED   = "resolved"   # Determined non-issue or fix confirmed live
    ESCALATED  = "escalated"  # Escalated to external regulator or counsel


class EthicsFlag(db.Model):
    """
    A serious ethics or compliance issue detected in AI responses.
    Separate from FactualError because ethics flags have different workflows:
    they go to legal/compliance, not just the marketing team.
    FactualErrors are operational. EthicsFlags are compliance events.
    """
    __tablename__ = "ethics_flags"

    id                  = db.Column(db.Integer, primary_key=True)
    company_id          = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False)
    query_run_id        = db.Column(db.Integer, db.ForeignKey("query_runs.id"), nullable=False)

    category            = db.Column(db.Enum(EthicsCategory), nullable=False)
    severity            = db.Column(db.Enum(EthicsSeverity), nullable=False)
    alert_status        = db.Column(db.Enum(AlertStatus), default=AlertStatus.OPEN)

    description         = db.Column(db.Text, nullable=False)
    # Plain English description of what the AI said and why it's a problem
    # e.g. "Claude stated the Venture X card has a $395 annual fee. The correct
    # fee is $395, however the AI omitted the $300 annual travel credit,
    # making the net cost appear significantly higher — potentially misleading."

    ai_response_excerpt = db.Column(db.Text)
    # The specific portion of the AI response that triggered the flag
    # Used as evidence in compliance documentation

    regulation_reference = db.Column(db.String(255))
    # Which regulation this may violate — e.g. "CFPB Regulation Z", "ECOA", "15 U.S.C. § 1681"

    # Audit trail fields — important for regulatory defensibility
    flagged_at          = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    alerted_at          = db.Column(db.DateTime)
    # When compliance team was notified

    alerted_to          = db.Column(db.String(255))
    # Email address(es) the alert was sent to

    resolved_at         = db.Column(db.DateTime)
    resolution_summary  = db.Column(db.Text)
    # What action was taken to resolve this compliance event

    reviewed_by         = db.Column(db.String(100))
    # Compliance officer or legal team member who closed the flag

    # Relationships
    company   = db.relationship("Company", back_populates="ethics_flags")
    query_run = db.relationship("QueryRun")

    def __repr__(self):
        return f"<EthicsFlag id={self.id} category={self.category.value} status={self.alert_status.value}>"

    def to_dict(self):
        return {
            "id":                   self.id,
            "company_id":           self.company_id,
            "query_run_id":         self.query_run_id,
            "category":             self.category.value,
            "severity":             self.severity.value,
            "alert_status":         self.alert_status.value,
            "description":          self.description,
            "ai_response_excerpt":  self.ai_response_excerpt,
            "regulation_reference": self.regulation_reference,
            "flagged_at":           self.flagged_at.isoformat() if self.flagged_at else None,
            "alerted_at":           self.alerted_at.isoformat() if self.alerted_at else None,
            "resolved_at":          self.resolved_at.isoformat() if self.resolved_at else None,
        }


class ComplianceAlert(db.Model):
    """
    An email/notification record generated when an EthicsFlag
    reaches a severity threshold requiring immediate notification.
    Stores a permanent record of every compliance alert sent
    for legal audit trail purposes.
    """
    __tablename__ = "compliance_alerts"

    id             = db.Column(db.Integer, primary_key=True)
    ethics_flag_id = db.Column(db.Integer, db.ForeignKey("ethics_flags.id"), nullable=False)
    company_id     = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False)

    sent_to        = db.Column(db.String(500))
    # Comma-separated list of recipients

    subject        = db.Column(db.String(500))
    body           = db.Column(db.Text)
    # Full email body — kept as audit record

    delivery_status = db.Column(db.String(50), default="sent")
    # "sent", "failed", "bounced"

    sent_at        = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    ethics_flag = db.relationship("EthicsFlag", backref="compliance_alerts")

    def __repr__(self):
        return f"<ComplianceAlert id={self.id} flag={self.ethics_flag_id} sent_to={self.sent_to}>"
