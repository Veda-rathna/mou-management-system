from django.core.management.base import BaseCommand
from mous.services.expiry_service import ExpiryMonitoringService


class Command(BaseCommand):
    help = "Runs daily MOU expiry check: updates expired statuses and sends email digests."

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Running MOU Expiry Radar scan..."))
        result = ExpiryMonitoringService.process_expiries()
        self.stdout.write(self.style.SUCCESS(
            f"Scan complete:\n"
            f"  - Newly Expired: {result['expired_count']}\n"
            f"  - Urgent (0-30d): {result['urgent_count']}\n"
            f"  - Warning (31-60d): {result['warning_count']}\n"
            f"  - Info (61-90d): {result['info_count']}\n"
            f"  - Digest Emails Sent: {result['emails_sent']}"
        ))
