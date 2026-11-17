from datetime import timedelta
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.utils import timezone
from django.urls import reverse

from mous.models import MOU, ShareLink, MOUStatus, ActivityLog, ActivityAction
from mous.services.expiry_service import ExpiryMonitoringService
from ai_intelligence.services.analyzer_service import MOUAnalysisOrchestrator
from ai_intelligence.models import AIAnalysis


class MOUWorkflowTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='teststaff', password='password123')
        self.mou = MOU.objects.create(
            title="Test Institutional Agreement",
            partner_name="John Doe",
            partner_organization="Acme Robotics",
            partner_email="john@acme.com",
            department="Robotics Lab",
            status=MOUStatus.DRAFT,
            description="Testing research collaboration terms.",
            start_date=timezone.now().date(),
            expiry_date=timezone.now().date() + timedelta(days=20),
            created_by=self.user,
        )

    def test_share_link_creation_and_validity(self):
        link = ShareLink.objects.create(
            mou=self.mou,
            expires_at=timezone.now() + timedelta(days=7),
            max_access_count=5,
            created_by=self.user,
        )
        self.assertTrue(link.is_valid)

        # Access count exhaustion
        for _ in range(5):
            link.record_access()
        self.assertFalse(link.is_valid)

    def test_partner_portal_access(self):
        link = ShareLink.objects.create(
            mou=self.mou,
            expires_at=timezone.now() + timedelta(days=7),
            max_access_count=5,
        )
        response = self.client.get(reverse('partner_portal', kwargs={'token': link.token}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Institutional Agreement")

    def test_ai_analysis_orchestration(self):
        self.mou.extracted_text = "Clause 1. Indemnity. Each party agrees to indemnify the other for direct damages."
        self.mou.save()

        analysis = MOUAnalysisOrchestrator.analyze_mou(self.mou, actor=self.user)
        self.assertIsNotNone(analysis)
        self.assertEqual(self.mou.ai_analysis, analysis)
        self.assertGreater(analysis.clauses.count(), 0)

    def test_expiry_monitoring(self):
        # Expiry set to 20 days (Urgent: 0-30 days)
        self.mou.status = MOUStatus.APPROVED
        self.mou.save()

        result = ExpiryMonitoringService.process_expiries()
        self.assertEqual(result['urgent_count'], 1)

        # Move date to yesterday
        self.mou.expiry_date = timezone.now().date() - timedelta(days=1)
        self.mou.save()

        result2 = ExpiryMonitoringService.process_expiries()
        self.assertEqual(result2['expired_count'], 1)
        self.mou.refresh_from_db()
        self.assertEqual(self.mou.status, MOUStatus.EXPIRED)
