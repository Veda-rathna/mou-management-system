import uuid
from datetime import timedelta
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.exceptions import ValidationError


def validate_pdf_file(value):
    """Ensure uploaded document is a valid PDF and under 10MB."""
    if not value.name.lower().endswith('.pdf'):
        raise ValidationError('Only PDF documents (.pdf) are supported.')
    if value.size > 10 * 1024 * 1024:
        raise ValidationError('File size must not exceed 10 MB.')


class MOUStatus(models.TextChoices):
    DRAFT = 'draft', 'Draft (Initiated)'
    PENDING_PARTNER = 'pending_partner', 'Pending Partner Action'
    PENDING_REVIEW = 'pending_review', 'Partner Submitted (Under Review)'
    APPROVED = 'approved', 'Approved & Executed'
    CHANGES_REQUESTED = 'changes_requested', 'Changes Requested'
    EXPIRED = 'expired', 'Expired'


class MOU(models.Model):
    """Primary agreement record connecting documents, partners, and AI analysis."""
    title = models.CharField(max_length=255, help_text="e.g. Research & Student Internship Collaboration Agreement")
    partner_name = models.CharField(max_length=255, help_text="Primary Contact / Signatory Name")
    partner_organization = models.CharField(max_length=255, help_text="Partner Company, Institution or University")
    partner_email = models.EmailField(help_text="Official email of the partner contact")
    partner_phone = models.CharField(max_length=50, blank=True, null=True)
    department = models.CharField(max_length=255, blank=True, default='Institutional Relations', help_text="Host Department / Faculty")

    status = models.CharField(
        max_length=30,
        choices=MOUStatus.choices,
        default=MOUStatus.DRAFT,
        db_index=True
    )

    document = models.FileField(
        upload_to='mou_documents/%Y/%m/',
        validators=[validate_pdf_file],
        blank=True,
        null=True,
        help_text="Current official MOU PDF document"
    )

    description = models.TextField(blank=True, help_text="Scope of cooperation, deliverables, objectives")
    start_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True, db_index=True)

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_mous')

    # College Internal Digital Signatory details
    college_signatory_name = models.CharField(max_length=255, blank=True)
    college_signatory_title = models.CharField(max_length=255, blank=True, default='Authorized Dean / Principal')
    college_signature = models.ImageField(upload_to='signatures/college/', blank=True, null=True)
    college_signed_at = models.DateTimeField(null=True, blank=True)

    # Document extraction cache
    extracted_text = models.TextField(blank=True, help_text="Raw text extracted from PDF")
    page_count = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'MOU Agreement'
        verbose_name_plural = 'MOU Agreements'

    def __str__(self):
        return f"{self.title} - {self.partner_organization} ({self.get_status_display()})"

    @property
    def is_expired(self):
        if self.expiry_date:
            return self.expiry_date < timezone.now().date()
        return False

    @property
    def days_until_expiry(self):
        if self.expiry_date:
            delta = self.expiry_date - timezone.now().date()
            return delta.days
        return None

    @property
    def expiry_urgency(self):
        days = self.days_until_expiry
        if days is None:
            return 'none'
        if days < 0:
            return 'expired'
        if days <= 30:
            return 'urgent'
        if days <= 60:
            return 'warning'
        if days <= 90:
            return 'info'
        return 'normal'


def default_share_expiry():
    return timezone.now() + timedelta(days=7)


class ShareLink(models.Model):
    """Secure, time-limited token links for external partner collaboration."""
    mou = models.ForeignKey(MOU, on_delete=models.CASCADE, related_name='share_links')
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)
    expires_at = models.DateTimeField(default=default_share_expiry)
    max_access_count = models.PositiveIntegerField(default=10)
    access_count = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Share Link for {self.mou.title} (Expires: {self.expires_at.strftime('%Y-%m-%d')})"

    @property
    def is_valid(self):
        if not self.is_active:
            return False
        if timezone.now() > self.expires_at:
            return False
        if self.access_count >= self.max_access_count:
            return False
        return True

    def record_access(self):
        self.access_count += 1
        if self.access_count >= self.max_access_count:
            self.is_active = False
        self.save(update_fields=['access_count', 'is_active'])


class PartnerSubmission(models.Model):
    """Submission and signature record from external partner."""
    mou = models.ForeignKey(MOU, on_delete=models.CASCADE, related_name='partner_submissions')
    share_link = models.ForeignKey(ShareLink, on_delete=models.SET_NULL, null=True, blank=True)
    partner_name = models.CharField(max_length=255)
    partner_organization = models.CharField(max_length=255)
    partner_email = models.EmailField()
    partner_phone = models.CharField(max_length=50, blank=True)
    partner_designation = models.CharField(max_length=255, blank=True)

    signature_image = models.ImageField(upload_to='signatures/partners/', blank=True, null=True)
    signature_data = models.TextField(blank=True, help_text="Base64 encoded signature image")
    updated_document = models.FileField(
        upload_to='partner_revisions/%Y/%m/',
        validators=[validate_pdf_file],
        blank=True,
        null=True,
        help_text="Partner proposed revised PDF if any"
    )
    notes = models.TextField(blank=True, help_text="Partner feedback, proofreading comments or revision notes")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-submitted_at']

    def __str__(self):
        return f"Submission by {self.partner_name} ({self.partner_organization}) on {self.submitted_at.strftime('%Y-%m-%d %H:%M')}"


class ActivityAction(models.TextChoices):
    CREATED = 'created', 'MOU Created'
    UPDATED = 'updated', 'MOU Updated'
    DOCUMENT_UPLOADED = 'document_uploaded', 'Document Uploaded'
    LINK_GENERATED = 'link_generated', 'Partner Link Generated'
    LINK_ACCESSED = 'link_accessed', 'Partner Opened Link'
    PARTNER_SUBMITTED = 'partner_submitted', 'Partner Submitted & Signed'
    AI_ANALYSIS_RUN = 'ai_analysis_run', 'AI Contract Intelligence Executed'
    CHANGES_REQUESTED = 'changes_requested', 'Changes Requested'
    APPROVED = 'approved', 'MOU Approved & Executed'
    COLLEGE_SIGNED = 'college_signed', 'College Signatory Signed'
    EXPIRED = 'expired', 'MOU Marked Expired'
    NOTIFICATION_SENT = 'notification_sent', 'Expiry Reminder Sent'
    FLAG_RESOLVED = 'flag_resolved', 'Risk Flag Resolved'


class ActivityLog(models.Model):
    """Immutable audit trail for institutional compliance and transparency."""
    mou = models.ForeignKey(MOU, on_delete=models.CASCADE, related_name='activity_logs')
    action = models.CharField(max_length=50, choices=ActivityAction.choices, db_index=True)
    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    actor_name = models.CharField(max_length=255, blank=True)
    description = models.TextField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"[{self.timestamp.strftime('%Y-%m-%d %H:%M')}] {self.get_action_display()} - {self.mou.title}"
