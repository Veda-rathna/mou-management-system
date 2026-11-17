from django.db import models
from django.contrib.auth.models import User
from mous.models import MOU


class RiskLevel(models.TextChoices):
    VERY_LOW = 'very_low', 'Very Low Risk (0 - 3.9)'
    LOW = 'low', 'Low Risk (4.0 - 5.9)'
    MEDIUM = 'medium', 'Medium Risk (6.0 - 7.9)'
    HIGH = 'high', 'High Risk (8.0 - 10.0)'


class ComplianceStatus(models.TextChoices):
    COMPLIANT = 'compliant', 'Compliant with Guidelines'
    REVIEW_REQUIRED = 'review_required', 'Review Required (Action Needed)'
    NON_COMPLIANT = 'non_compliant', 'Non-Compliant (High Concern)'
    PENDING_ANALYSIS = 'pending_analysis', 'Pending Analysis'


class ClauseCategory(models.TextChoices):
    TERMINATION = 'termination', 'Termination & Exit'
    PAYMENT = 'payment', 'Payment & Financial Obligations'
    LIABILITY = 'liability', 'Liability & Indemnification'
    CONFIDENTIALITY = 'confidentiality', 'Confidentiality & NDA'
    INTELLECTUAL_PROPERTY = 'ip', 'Intellectual Property & Patents'
    DISPUTE_RESOLUTION = 'dispute_resolution', 'Dispute Resolution & Arbitration'
    GOVERNING_LAW = 'governing_law', 'Governing Law & Jurisdiction'
    FORCE_MAJEURE = 'force_majeure', 'Force Majeure'
    PERFORMANCE = 'performance', 'Performance & Deliverables'
    WARRANTIES = 'warranties', 'Warranties & Representations'
    STUDENT_PRIVACY = 'student_privacy', 'Student Privacy & Data Protection'
    GENERAL = 'general', 'General Provisions'
    OTHER = 'other', 'Other / Uncategorized'


class AIAnalysis(models.Model):
    """Document-level AI analysis result for an MOU."""
    mou = models.OneToOneField(MOU, on_delete=models.CASCADE, related_name='ai_analysis')
    overall_risk_score = models.FloatField(default=0.0, help_text="Aggregate score from 0.0 (safest) to 10.0 (highest risk)")
    risk_level = models.CharField(max_length=30, choices=RiskLevel.choices, default=RiskLevel.VERY_LOW)
    compliance_status = models.CharField(max_length=30, choices=ComplianceStatus.choices, default=ComplianceStatus.PENDING_ANALYSIS)
    executive_summary = models.TextField(blank=True, help_text="AI executive summary of agreement strengths and risks")
    model_used = models.CharField(max_length=100, default='Google Gemini 1.5 Flash')
    processing_time_seconds = models.FloatField(default=0.0)

    total_clauses_analyzed = models.PositiveIntegerField(default=0)
    high_risk_count = models.PositiveIntegerField(default=0)
    medium_risk_count = models.PositiveIntegerField(default=0)
    low_risk_count = models.PositiveIntegerField(default=0)

    # Specific institutional guardrail checks (IP, liability cap, local jurisdiction, student privacy, hidden fees)
    institutional_checks = models.JSONField(default=dict, blank=True)

    analyzed_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-analyzed_at']
        verbose_name = 'AI Analysis Record'
        verbose_name_plural = 'AI Analysis Records'

    def __str__(self):
        return f"AI Analysis for {self.mou.title} - Score: {self.overall_risk_score}/10 ({self.get_compliance_status_display()})"

    @property
    def badge_color(self):
        if self.overall_risk_score >= 8.0:
            return 'danger'
        elif self.overall_risk_score >= 6.0:
            return 'warning'
        elif self.overall_risk_score >= 4.0:
            return 'info'
        return 'success'


class ClauseAnalysis(models.Model):
    """Structured clause identification, risk assessment and improvement suggestions."""
    analysis = models.ForeignKey(AIAnalysis, on_delete=models.CASCADE, related_name='clauses')
    clause_number = models.CharField(max_length=50, blank=True, help_text="Clause 1.1, Section 4, etc.")
    category = models.CharField(max_length=50, choices=ClauseCategory.choices, default=ClauseCategory.GENERAL)
    clause_text = models.TextField()
    risk_score = models.FloatField(default=0.0, help_text="0.0 to 10.0")
    confidence_score = models.FloatField(default=0.9, help_text="0.0 to 1.0")
    sentiment = models.CharField(max_length=50, blank=True, default='Neutral')
    identified_risks = models.JSONField(default=list, blank=True)
    suggested_improvements = models.TextField(blank=True)
    key_terms = models.JSONField(default=list, blank=True)
    page_number = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ['id']
        verbose_name = 'Clause Analysis'
        verbose_name_plural = 'Clause Analyses'

    def __str__(self):
        return f"Clause {self.clause_number or '#'} ({self.get_category_display()}) - Risk: {self.risk_score}"

    @property
    def risk_badge_class(self):
        if self.risk_score >= 7.0:
            return 'bg-danger text-white'
        if self.risk_score >= 4.0:
            return 'bg-warning text-dark'
        return 'bg-success text-white'


class SeverityLevel(models.TextChoices):
    LOW = 'low', 'Low Severity'
    MEDIUM = 'medium', 'Medium Severity'
    HIGH = 'high', 'High Severity'
    CRITICAL = 'critical', 'Critical Red-Flag'


class RiskType(models.TextChoices):
    LEGAL = 'legal', 'Legal & Liability Risk'
    FINANCIAL = 'financial', 'Financial & Hidden Costs'
    IP = 'ip', 'Intellectual Property Risk'
    COMPLIANCE = 'compliance', 'Compliance & Regulatory'
    OPERATIONAL = 'operational', 'Operational & Ambiguity'
    STUDENT_DATA = 'student_data', 'Student Privacy & Data Protection'


class RiskFlag(models.Model):
    """Actionable issue requiring human review and resolution."""
    mou = models.ForeignKey(MOU, on_delete=models.CASCADE, related_name='risk_flags')
    clause = models.ForeignKey(ClauseAnalysis, on_delete=models.SET_NULL, null=True, blank=True, related_name='flags')
    title = models.CharField(max_length=255)
    risk_type = models.CharField(max_length=50, choices=RiskType.choices, default=RiskType.LEGAL)
    severity = models.CharField(max_length=30, choices=SeverityLevel.choices, default=SeverityLevel.MEDIUM)
    description = models.TextField()
    suggested_action = models.TextField(blank=True)

    is_resolved = models.BooleanField(default=False, db_index=True)
    resolved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['is_resolved', '-severity', '-created_at']

    def __str__(self):
        status = "Resolved" if self.is_resolved else "Open"
        return f"[{self.get_severity_display()}] {self.title} ({status})"

    @property
    def severity_badge(self):
        mapping = {
            SeverityLevel.LOW: 'bg-info text-dark',
            SeverityLevel.MEDIUM: 'bg-warning text-dark',
            SeverityLevel.HIGH: 'bg-danger text-white',
            SeverityLevel.CRITICAL: 'bg-dark text-white',
        }
        return mapping.get(self.severity, 'bg-secondary')


class AIModelMetrics(models.Model):
    """System-wide telemetry on AI performance and processing throughput."""
    documents_analyzed = models.PositiveIntegerField(default=0)
    clauses_analyzed = models.PositiveIntegerField(default=0)
    average_processing_time = models.FloatField(default=0.0)
    failure_count = models.PositiveIntegerField(default=0)
    last_run = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'AI Model Metric'
        verbose_name_plural = 'AI Model Metrics'

    def __str__(self):
        return f"AI Metrics: {self.documents_analyzed} docs analyzed, avg {self.average_processing_time:.2f}s"
