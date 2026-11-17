import os
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from mous.models import MOU, ShareLink, MOUStatus, ActivityAction
from mous.services.activity_service import ActivityService
from ai_intelligence.services.analyzer_service import MOUAnalysisOrchestrator

SAMPLE_MOU_TEXT = """
MEMORANDUM OF UNDERSTANDING (MOU)

BETWEEN:
DEPARTMENT OF COMPUTER SCIENCE & ENGINEERING, METROPOLITAN UNIVERSITY (Hereinafter referred to as "the Institution")
AND
APEX GLOBAL SOFTWARE TECHNOLOGIES INC. (Hereinafter referred to as "the Industry Partner")

1. PURPOSE & SCOPE OF COOPERATION
The purpose of this Memorandum of Understanding is to establish a cooperative framework for joint research, curriculum enhancement, faculty development programs, and student internships in cloud computing and artificial intelligence.

2. TERM AND TERMINATION
2.1 This MOU shall take effect on the date of execution and shall remain in effect for a period of three (3) years.
2.2 Either party may terminate this agreement upon thirty (30) days prior written notice to the other party. However, ongoing student internship batches shall be allowed to complete their term without disruption.

3. INTELLECTUAL PROPERTY RIGHTS
3.1 All pre-existing intellectual property belonging to either party prior to this agreement shall remain the exclusive property of that party.
3.2 Any new intellectual property, patentable inventions, or software code developed solely by students or faculty during projects under this MOU shall remain the property of the University. The Industry Partner is hereby granted a non-exclusive, royalty-free license for internal commercial evaluation.

4. CONFIDENTIALITY & NON-DISCLOSURE
Both parties agree to treat all proprietary technical data, curriculum materials, and business secrets disclosed during the collaboration as strictly confidential for a period of two (2) years following disclosure.

5. INDEMNITY & LIMITATION OF LIABILITY
5.1 Each party agrees to indemnify and hold harmless the other party against direct losses arising from gross negligence or willful misconduct.
5.2 IN NO EVENT SHALL EITHER PARTY BE LIABLE FOR ANY INDIRECT, INCIDENTAL, SPECIAL, OR CONSEQUENTIAL DAMAGES. The aggregate liability of either party under this agreement shall be capped at the total financial commitment or a maximum of $10,000 USD.

6. STUDENT DATA PRIVACY & RECORD PROTECTION
The Industry Partner agrees that student performance records, personal contact data, and academic transcripts shall not be transferred, sold, or shared with third parties, in compliance with applicable education privacy standards.

7. FINANCIAL OBLIGATIONS
Unless explicitly stated in a subsequent separate Project Statement of Work signed by authorized institutional officials, neither party shall have any monetary obligation to the other.

8. GOVERNING LAW AND DISPUTE RESOLUTION
This agreement shall be governed by and construed in accordance with the laws of the local state jurisdiction. In the event of any dispute, the parties shall first attempt mutual conciliation before referring the matter to local arbitration.

IN WITNESS WHEREOF, the authorized representatives of both parties have executed this agreement.
"""


class Command(BaseCommand):
    help = "Seeds standard demo admin user and a realistic institutional sample MOU."

    def handle(self, *args, **options):
        # 1. Create or verify demo staff user
        user, created = User.objects.get_or_create(username='admin')
        if created:
            user.set_password('admin123')
            user.is_staff = True
            user.is_superuser = True
            user.first_name = 'Admin'
            user.last_name = 'Director'
            user.email = 'admin@college.edu'
            user.save()
            self.stdout.write(self.style.SUCCESS("Created demo superuser: username='admin', password='admin123'"))
        else:
            self.stdout.write(self.style.NOTICE("Superuser 'admin' already exists."))

        # 2. Create sample MOU record if none exists
        if not MOU.objects.filter(title__icontains="Apex Global").exists():
            mou = MOU.objects.create(
                title="AI & Cloud Computing Research and Internship Collaboration",
                partner_name="Vikramaditya Roy",
                partner_organization="Apex Global Software Technologies Inc.",
                partner_email="v.roy@apexsoftware.com",
                partner_phone="+1 415 800 2938",
                department="Dept of Computer Science & Engineering",
                status=MOUStatus.PENDING_REVIEW,
                description="Joint university-industry training lab, student summer internships, faculty enablement workshops, and co-developed curriculum.",
                start_date=timezone.now().date(),
                expiry_date=timezone.now().date() + timedelta(days=180),
                created_by=user,
                extracted_text=SAMPLE_MOU_TEXT,
                page_count=3,
                college_signatory_name="Dr. S. K. Narayanan",
                college_signatory_title="Principal & Dean of Engineering",
            )

            # Run AI Analysis
            analysis = MOUAnalysisOrchestrator.analyze_mou(mou, actor=user)

            # Generate sample ShareLink
            share_link = ShareLink.objects.create(
                mou=mou,
                expires_at=timezone.now() + timedelta(days=7),
                max_access_count=15,
                created_by=user,
            )

            ActivityService.log(
                mou=mou,
                action=ActivityAction.CREATED,
                actor=user,
                description="Sample MOU created during initial system setup."
            )
            ActivityService.log(
                mou=mou,
                action=ActivityAction.LINK_GENERATED,
                actor=user,
                description=f"Generated collaboration link for external partner. Token: {share_link.token}"
            )

            self.stdout.write(self.style.SUCCESS(
                f"Created sample MOU: '{mou.title}'\n"
                f"  - AI Risk Score: {analysis.overall_risk_score}/10\n"
                f"  - Partner Share Token: {share_link.token}\n"
                f"  - Public Partner URL: /partner/{share_link.token}/"
            ))
        else:
            self.stdout.write(self.style.NOTICE("Sample MOU already present."))
