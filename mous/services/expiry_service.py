import logging
from datetime import date
from typing import Dict, List, Any
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from mous.models import MOU, MOUStatus, ActivityAction
from mous.services.activity_service import ActivityService

logger = logging.getLogger(__name__)


class ExpiryMonitoringService:
    """Service to track agreement validity, transition expired MOUs, and send alerts."""

    @staticmethod
    def process_expiries() -> Dict[str, Any]:
        today = timezone.now().date()

        # 1. Automatically update approved MOUs whose validity has ended
        newly_expired = MOU.objects.filter(
            status=MOUStatus.APPROVED,
            expiry_date__lt=today
        )
        expired_count = newly_expired.count()
        for mou in newly_expired:
            mou.status = MOUStatus.EXPIRED
            mou.save(update_fields=['status', 'updated_at'])
            ActivityService.log(
                mou=mou,
                action=ActivityAction.EXPIRED,
                description=f"MOU automatically marked as Expired on {today.strftime('%Y-%m-%d')}."
            )

        # 2. Find approved MOUs approaching expiry (0-30 days, 31-60 days, 61-90 days)
        active_mous = MOU.objects.filter(
            status=MOUStatus.APPROVED,
            expiry_date__isnull=False,
            expiry_date__gte=today
        )

        urgent_list: List[MOU] = []
        warning_list: List[MOU] = []
        info_list: List[MOU] = []

        for mou in active_mous:
            days = (mou.expiry_date - today).days
            if days <= 30:
                urgent_list.append(mou)
            elif days <= 60:
                warning_list.append(mou)
            elif days <= 90:
                info_list.append(mou)

        total_alerts = len(urgent_list) + len(warning_list) + len(info_list)

        # 3. Send email notifications if alerts exist
        emails_sent = 0
        if total_alerts > 0:
            emails_sent = ExpiryMonitoringService._send_expiry_digest(
                urgent=urgent_list,
                warning=warning_list,
                info=info_list
            )

        return {
            'expired_count': expired_count,
            'urgent_count': len(urgent_list),
            'warning_count': len(warning_list),
            'info_count': len(info_list),
            'emails_sent': emails_sent,
        }

    @staticmethod
    def _send_expiry_digest(urgent: List[MOU], warning: List[MOU], info: List[MOU]) -> int:
        subject = f"[MOU Expiry Radar] {len(urgent)} Urgent, {len(warning)} Approaching Expiration"

        body_lines = [
            "MOU Management System - Institutional Expiry Radar Report",
            "=" * 60,
            f"Generated on: {timezone.now().strftime('%Y-%m-%d %H:%M UTC')}",
            "",
        ]

        if urgent:
            body_lines.append("🔴 URGENT EXPIRIES (0 - 30 DAYS REMAINING):")
            for m in urgent:
                body_lines.append(f"  • {m.title} | Partner: {m.partner_organization} | Expiry: {m.expiry_date} ({m.days_until_expiry} days left)")
            body_lines.append("")

        if warning:
            body_lines.append("🟡 UPCOMING EXPIRIES (31 - 60 DAYS REMAINING):")
            for m in warning:
                body_lines.append(f"  • {m.title} | Partner: {m.partner_organization} | Expiry: {m.expiry_date} ({m.days_until_expiry} days left)")
            body_lines.append("")

        if info:
            body_lines.append("🔵 ADVANCE NOTICE (61 - 90 DAYS REMAINING):")
            for m in info:
                body_lines.append(f"  • {m.title} | Partner: {m.partner_organization} | Expiry: {m.expiry_date} ({m.days_until_expiry} days left)")
            body_lines.append("")

        body_lines.append("Please log in to the MOU Management portal to renew, renegotiate, or archive these agreements.")
        body_text = "\n".join(body_lines)

        try:
            recipient = getattr(settings, 'DEFAULT_FROM_EMAIL', 'admin@local.test')
            send_mail(
                subject=subject,
                message=body_text,
                from_email=recipient,
                recipient_list=[recipient],
                fail_silently=True,
            )
            return 1
        except Exception as e:
            logger.error(f"Failed to send expiry digest email: {e}")
            return 0
