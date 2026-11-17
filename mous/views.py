import json
from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Avg, Count
from django.http import JsonResponse, HttpResponseForbidden
from django.utils import timezone
from django.views.decorators.http import require_POST

from mous.models import MOU, ShareLink, PartnerSubmission, ActivityLog, MOUStatus, ActivityAction
from mous.forms import MOUForm, PartnerInviteForm, PartnerPortalSubmissionForm, CollegeSignForm
from mous.services.pdf_service import PDFProcessingService
from mous.services.signature_service import SignatureProcessingService
from mous.services.activity_service import ActivityService
from ai_intelligence.services.analyzer_service import MOUAnalysisOrchestrator
from ai_intelligence.models import RiskFlag, AIAnalysis


@login_required
def mou_dashboard(request):
    """Executive Dashboard with portfolio metrics, search, filtering, and sorting."""
    queryset = MOU.objects.all()

    # Search query
    q = request.GET.get('q', '').strip()
    if q:
        queryset = queryset.filter(
            Q(title__icontains=q) |
            Q(partner_name__icontains=q) |
            Q(partner_organization__icontains=q) |
            Q(department__icontains=q)
        )

    # Status filter
    status_filter = request.GET.get('status', '').strip()
    if status_filter:
        queryset = queryset.filter(status=status_filter)

    # Sorting
    sort = request.GET.get('sort', '-created_at')
    allowed_sorts = ['-created_at', 'created_at', 'title', '-title', 'expiry_date', '-expiry_date', 'partner_organization']
    if sort in allowed_sorts:
        queryset = queryset.order_by(sort)
    else:
        queryset = queryset.order_by('-created_at')

    # Executive Telemetry & Counts
    total_count = MOU.objects.count()
    active_approved_count = MOU.objects.filter(status=MOUStatus.APPROVED).count()
    pending_partner_count = MOU.objects.filter(status=MOUStatus.PENDING_PARTNER).count()
    pending_review_count = MOU.objects.filter(status=MOUStatus.PENDING_REVIEW).count()

    today = timezone.now().date()
    thirty_days_later = today + timedelta(days=30)
    expiring_soon_count = MOU.objects.filter(
        status=MOUStatus.APPROVED,
        expiry_date__gte=today,
        expiry_date__lte=thirty_days_later
    ).count()

    avg_risk = AIAnalysis.objects.aggregate(Avg('overall_risk_score'))['overall_risk_score__avg'] or 0.0

    # Pagination
    paginator = Paginator(queryset, 10)
    page_number = request.GET.get('page')
    mous_page = paginator.get_page(page_number)

    context = {
        'mous': mous_page,
        'q': q,
        'status_filter': status_filter,
        'sort': sort,
        'total_count': total_count,
        'active_approved_count': active_approved_count,
        'pending_partner_count': pending_partner_count,
        'pending_review_count': pending_review_count,
        'expiring_soon_count': expiring_soon_count,
        'avg_risk': round(avg_risk, 1),
        'MOUStatus': MOUStatus,
    }
    return render(request, 'mous/dashboard.html', context)


@login_required
def mou_create(request):
    """Create new MOU or initiate partner collaboration."""
    if request.method == 'POST':
        form = MOUForm(request.POST, request.FILES)
        if form.is_valid():
            mou = form.save(commit=False)
            mou.created_by = request.user
            mou.status = MOUStatus.DRAFT
            mou.save()

            # Process PDF text extraction
            if mou.document:
                try:
                    pdf_data = PDFProcessingService.extract_document_data(mou.document.path)
                    mou.extracted_text = pdf_data.get('text', '')
                    mou.page_count = pdf_data.get('page_count', 0)
                    mou.save(update_fields=['extracted_text', 'page_count'])
                    ActivityService.log(
                        mou=mou,
                        action=ActivityAction.DOCUMENT_UPLOADED,
                        actor=request.user,
                        description=f"Uploaded initial MOU PDF ({mou.page_count} pages).",
                        request=request
                    )
                except Exception as e:
                    messages.warning(request, f"Document uploaded, but text extraction had a warning: {e}")

            ActivityService.log(
                mou=mou,
                action=ActivityAction.CREATED,
                actor=request.user,
                description=f"MOU '{mou.title}' created by {request.user.get_full_name() or request.user.username}.",
                request=request
            )

            # Trigger AI Analysis
            if mou.extracted_text or mou.description:
                MOUAnalysisOrchestrator.analyze_mou(mou, actor=request.user)

            messages.success(request, f"MOU '{mou.title}' successfully initialized!")
            return redirect('mou_detail', pk=mou.pk)
    else:
        form = MOUForm()

    return render(request, 'mous/mou_form.html', {'form': form, 'title': 'Create New MOU Record'})


@login_required
def mou_detail(request, pk):
    """Split-screen Reviewer Studio: PDF preview on left, AI Intelligence & flags on right."""
    mou = get_object_or_404(MOU, pk=pk)
    ai_analysis = getattr(mou, 'ai_analysis', None)
    clauses = ai_analysis.clauses.all() if ai_analysis else []
    risk_flags = mou.risk_flags.all()
    unresolved_flags = risk_flags.filter(is_resolved=False)
    resolved_flags = risk_flags.filter(is_resolved=True)
    share_links = mou.share_links.all()[:5]
    submissions = mou.partner_submissions.all()
    activity_logs = mou.activity_logs.all()[:15]

    college_sign_form = CollegeSignForm(initial={
        'signatory_name': mou.college_signatory_name or (request.user.get_full_name() or request.user.username),
        'signatory_title': mou.college_signatory_title or 'Authorized Dean / Principal',
    })

    context = {
        'mou': mou,
        'ai_analysis': ai_analysis,
        'clauses': clauses,
        'risk_flags': risk_flags,
        'unresolved_flags': unresolved_flags,
        'resolved_flags': resolved_flags,
        'share_links': share_links,
        'submissions': submissions,
        'activity_logs': activity_logs,
        'college_sign_form': college_sign_form,
        'MOUStatus': MOUStatus,
    }
    return render(request, 'mous/mou_detail.html', context)


@login_required
def mou_edit(request, pk):
    """Edit MOU metadata or upload revised PDF."""
    mou = get_object_or_404(MOU, pk=pk)
    old_doc = mou.document.name if mou.document else None

    if request.method == 'POST':
        form = MOUForm(request.POST, request.FILES, instance=mou)
        if form.is_valid():
            updated_mou = form.save()
            new_doc = updated_mou.document.name if updated_mou.document else None

            # If document changed, re-extract and re-analyze
            if new_doc != old_doc and updated_mou.document:
                try:
                    pdf_data = PDFProcessingService.extract_document_data(updated_mou.document.path)
                    updated_mou.extracted_text = pdf_data.get('text', '')
                    updated_mou.page_count = pdf_data.get('page_count', 0)
                    updated_mou.save(update_fields=['extracted_text', 'page_count'])
                    MOUAnalysisOrchestrator.analyze_mou(updated_mou, actor=request.user)
                except Exception as e:
                    messages.warning(request, f"Document updated, but text extraction notice: {e}")

            ActivityService.log(
                mou=updated_mou,
                action=ActivityAction.UPDATED,
                actor=request.user,
                description="MOU agreement details updated.",
                request=request
            )
            messages.success(request, "MOU updated successfully.")
            return redirect('mou_detail', pk=updated_mou.pk)
    else:
        form = MOUForm(instance=mou)

    return render(request, 'mous/mou_form.html', {'form': form, 'title': f'Edit: {mou.title}', 'mou': mou})


@login_required
@require_POST
def generate_share_link(request, pk):
    """Generate a secure, time-limited token link for external partner collaboration."""
    mou = get_object_or_404(MOU, pk=pk)
    days = int(request.POST.get('days', 7))
    max_clicks = int(request.POST.get('max_clicks', 15))

    link = ShareLink.objects.create(
        mou=mou,
        expires_at=timezone.now() + timedelta(days=days),
        max_access_count=max_clicks,
        created_by=request.user,
    )

    # Update status to Pending Partner if currently in draft
    if mou.status == MOUStatus.DRAFT:
        mou.status = MOUStatus.PENDING_PARTNER
        mou.save(update_fields=['status', 'updated_at'])

    full_url = request.build_absolute_uri(f"/partner/{link.token}/")

    ActivityService.log(
        mou=mou,
        action=ActivityAction.LINK_GENERATED,
        actor=request.user,
        description=f"Generated partner collaboration link valid for {days} days ({max_clicks} max accesses).",
        request=request
    )

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success', 'url': full_url, 'token': str(link.token)})

    messages.success(request, f"Partner link generated: {full_url}")
    return redirect('mou_detail', pk=mou.pk)


def partner_portal(request, token):
    """Public, secure portal for external partner to review, upload draft, and sign."""
    share_link = get_object_or_404(ShareLink, token=token)

    if not share_link.is_valid:
        return render(request, 'partner/link_expired.html', {'link': share_link})

    mou = share_link.mou

    # Log access
    if request.method == 'GET':
        share_link.record_access()
        ActivityService.log(
            mou=mou,
            action=ActivityAction.LINK_ACCESSED,
            actor_name=f"Partner ({share_link.token})",
            description=f"Partner accessed secure MOU portal. (Access count: {share_link.access_count}/{share_link.max_access_count})",
            request=request
        )

    if request.method == 'POST':
        form = PartnerPortalSubmissionForm(request.POST, request.FILES)
        if form.is_valid():
            submission = form.save(commit=False)
            submission.mou = mou
            submission.share_link = share_link
            submission.ip_address = request.META.get('REMOTE_ADDR')

            # Process canvas signature
            sig_data = form.cleaned_data.get('signature_data')
            if sig_data:
                sig_file = SignatureProcessingService.process_canvas_signature(sig_data, prefix=f"partner_{mou.id}")
                if sig_file:
                    submission.signature_image.save(sig_file.name, sig_file, save=False)

            submission.save()

            # If partner uploaded an updated/proposed PDF, set as current official document
            if submission.updated_document:
                mou.document = submission.updated_document
                try:
                    pdf_data = PDFProcessingService.extract_document_data(mou.document.path)
                    mou.extracted_text = pdf_data.get('text', '')
                    mou.page_count = pdf_data.get('page_count', 0)
                except Exception as e:
                    pass

            # Update partner details if empty
            if not mou.partner_name:
                mou.partner_name = submission.partner_name
            if not mou.partner_organization:
                mou.partner_organization = submission.partner_organization
            if not mou.partner_email:
                mou.partner_email = submission.partner_email

            # Update status to Pending Review (College Reviewer notified)
            mou.status = MOUStatus.PENDING_REVIEW
            mou.save()

            # Automatically run AI Analysis on partner's document
            MOUAnalysisOrchestrator.analyze_mou(mou)

            ActivityService.log(
                mou=mou,
                action=ActivityAction.PARTNER_SUBMITTED,
                actor_name=f"{submission.partner_name} ({submission.partner_organization})",
                description=f"Partner submitted response & digital signature. Updated document: {'Yes' if submission.updated_document else 'No'}. MOU is now under institutional review.",
                request=request
            )

            return redirect('partner_success', token=token)
    else:
        initial_data = {
            'partner_name': mou.partner_name,
            'partner_organization': mou.partner_organization,
            'partner_email': mou.partner_email,
            'partner_phone': mou.partner_phone,
        }
        form = PartnerPortalSubmissionForm(initial=initial_data)

    ai_analysis = getattr(mou, 'ai_analysis', None)

    context = {
        'share_link': share_link,
        'mou': mou,
        'form': form,
        'ai_analysis': ai_analysis,
    }
    return render(request, 'partner/portal.html', context)


def partner_success(request, token):
    """Partner submission confirmation page."""
    share_link = get_object_or_404(ShareLink, token=token)
    return render(request, 'partner/success.html', {'mou': share_link.mou, 'token': token})


@login_required
@require_POST
def college_approve_and_sign(request, pk):
    """Authorized internal Dean / Principal signs digitally and approves the MOU."""
    mou = get_object_or_404(MOU, pk=pk)
    form = CollegeSignForm(request.POST)

    if form.is_valid():
        sig_data = form.cleaned_data['signature_data']
        sig_file = SignatureProcessingService.process_canvas_signature(sig_data, prefix=f"college_{mou.id}")

        mou.college_signatory_name = form.cleaned_data['signatory_name']
        mou.college_signatory_title = form.cleaned_data['signatory_title']
        if sig_file:
            mou.college_signature.save(sig_file.name, sig_file, save=False)
        mou.college_signed_at = timezone.now()
        mou.status = MOUStatus.APPROVED

        # Default start date to today if empty
        if not mou.start_date:
            mou.start_date = timezone.now().date()
        # Default expiry to 1 year if empty
        if not mou.expiry_date:
            mou.expiry_date = timezone.now().date() + timedelta(days=365)

        mou.save()

        ActivityService.log(
            mou=mou,
            action=ActivityAction.APPROVED,
            actor=request.user,
            description=f"MOU officially approved and digitally signed by {mou.college_signatory_name} ({mou.college_signatory_title}). Validity set until {mou.expiry_date}.",
            request=request
        )

        messages.success(request, f"MOU '{mou.title}' has been successfully approved and digitally executed!")
    else:
        messages.error(request, "Please provide a valid signature before approving.")

    return redirect('mou_detail', pk=mou.pk)


@login_required
@require_POST
def request_partner_changes(request, pk):
    """College requests amendments from partner and provides feedback notes."""
    mou = get_object_or_404(MOU, pk=pk)
    notes = request.POST.get('notes', 'Amendments requested per institutional legal review.')

    mou.status = MOUStatus.CHANGES_REQUESTED
    mou.save(update_fields=['status', 'updated_at'])

    ActivityService.log(
        mou=mou,
        action=ActivityAction.CHANGES_REQUESTED,
        actor=request.user,
        description=f"Changes requested by {request.user.get_full_name() or request.user.username}: {notes}",
        request=request
    )

    messages.info(request, "Status updated: Changes Requested. The partner has been flagged for revisions.")
    return redirect('mou_detail', pk=mou.pk)


@login_required
@require_POST
def reanalyze_mou(request, pk):
    """Manually re-run AI Contract Intelligence."""
    mou = get_object_or_404(MOU, pk=pk)

    # Re-extract text if needed
    if mou.document and not mou.extracted_text:
        try:
            pdf_data = PDFProcessingService.extract_document_data(mou.document.path)
            mou.extracted_text = pdf_data.get('text', '')
            mou.page_count = pdf_data.get('page_count', 0)
            mou.save(update_fields=['extracted_text', 'page_count'])
        except Exception:
            pass

    analysis = MOUAnalysisOrchestrator.analyze_mou(mou, actor=request.user)
    messages.success(request, f"AI analysis completed! Risk score: {analysis.overall_risk_score}/10.")
    return redirect('mou_detail', pk=mou.pk)


@login_required
@require_POST
def resolve_risk_flag(request, flag_id):
    """Mark a flagged legal risk as resolved with human audit notes."""
    flag = get_object_or_404(RiskFlag, pk=flag_id)
    notes = request.POST.get('resolution_notes', 'Resolved per reviewer assessment.')

    flag.is_resolved = True
    flag.resolved_by = request.user
    flag.resolved_at = timezone.now()
    flag.resolution_notes = notes
    flag.save()

    ActivityService.log(
        mou=flag.mou,
        action=ActivityAction.FLAG_RESOLVED,
        actor=request.user,
        description=f"Resolved risk flag '{flag.title}'. Notes: {notes}",
        request=request
    )

    messages.success(request, f"Flag '{flag.title}' marked as resolved.")
    return redirect('mou_detail', pk=flag.mou.pk)


@login_required
def executive_summary_view(request, pk):
    """Printable 1-page executive summary for Director / Dean / Board review."""
    mou = get_object_or_404(MOU, pk=pk)
    ai_analysis = getattr(mou, 'ai_analysis', None)
    risk_flags = mou.risk_flags.all()

    context = {
        'mou': mou,
        'ai_analysis': ai_analysis,
        'risk_flags': risk_flags,
        'now': timezone.now(),
    }
    return render(request, 'mous/executive_summary.html', context)


@login_required
def audit_log_view(request, pk):
    """Full chronological audit trail view."""
    mou = get_object_or_404(MOU, pk=pk)
    logs = mou.activity_logs.all()
    return render(request, 'mous/audit_log.html', {'mou': mou, 'logs': logs})
