import time
import logging
from typing import Dict, Any, Optional
from django.db import transaction
from django.utils import timezone
from django.contrib.auth.models import User

from mous.models import MOU, ActivityAction
from mous.services.activity_service import ActivityService
from ai_intelligence.models import (
    AIAnalysis, ClauseAnalysis, RiskFlag, AIModelMetrics,
    RiskLevel, ComplianceStatus, ClauseCategory, SeverityLevel, RiskType
)
from ai_intelligence.services.gemini_service import GeminiLegalAnalysisService
from ai_intelligence.services.rule_engine import RuleBasedLegalEngine

logger = logging.getLogger(__name__)


class MOUAnalysisOrchestrator:
    """Orchestrates hybrid AI contract intelligence (Gemini Flash API + Rule-Based Engine)."""

    @classmethod
    def analyze_mou(cls, mou: MOU, actor: Optional[User] = None) -> AIAnalysis:
        start_time = time.time()
        text = (mou.extracted_text or '').strip()

        if not text:
            # If no extracted text yet, attempt extraction or analyze description
            text = mou.description or f"Memorandum of Understanding between {mou.partner_organization} and College."

        # Step 1: Try Google Gemini API
        analysis_data: Optional[Dict[str, Any]] = GeminiLegalAnalysisService.analyze_document(text)
        model_used = "Google Gemini 1.5 Flash (Legal Guardrails)"

        # Step 2: Fallback to Offline Rule Engine if Gemini is absent or failed
        if not analysis_data or not isinstance(analysis_data, dict):
            analysis_data = RuleBasedLegalEngine.analyze_full_document(text)
            model_used = "Institutional Rule-Based Engine (Offline Fallback)"

        duration = round(time.time() - start_time, 2)

        # Step 3: Persist results transactionally
        with transaction.atomic():
            # Delete previous analysis & risk flags for fresh versioning
            AIAnalysis.objects.filter(mou=mou).delete()
            RiskFlag.objects.filter(mou=mou, is_resolved=False).delete()

            overall_score = float(analysis_data.get('overall_risk_score', 2.5))
            risk_level_str = analysis_data.get('risk_level', 'low')
            compliance_str = analysis_data.get('compliance_status', 'compliant')

            # Map to valid choices
            risk_level = RiskLevel.LOW
            for choice in RiskLevel.values:
                if choice == risk_level_str:
                    risk_level = choice
                    break

            compliance_status = ComplianceStatus.COMPLIANT
            for choice in ComplianceStatus.values:
                if choice == compliance_str:
                    compliance_status = choice
                    break

            ai_record = AIAnalysis.objects.create(
                mou=mou,
                overall_risk_score=overall_score,
                risk_level=risk_level,
                compliance_status=compliance_status,
                executive_summary=analysis_data.get('executive_summary', ''),
                model_used=model_used,
                processing_time_seconds=duration,
                institutional_checks=analysis_data.get('institutional_checks', {}),
            )

            # Persist clauses
            raw_clauses = analysis_data.get('clauses', [])
            clause_objs = []
            clause_map = {}

            high_count = 0
            med_count = 0
            low_count = 0

            for c in raw_clauses:
                c_score = float(c.get('risk_score', 0.0))
                if c_score >= 7.0:
                    high_count += 1
                elif c_score >= 4.0:
                    med_count += 1
                else:
                    low_count += 1

                cat_str = c.get('category', ClauseCategory.GENERAL)
                category = ClauseCategory.GENERAL
                for choice in ClauseCategory.values:
                    if choice == cat_str:
                        category = choice
                        break

                clause_instance = ClauseAnalysis(
                    analysis=ai_record,
                    clause_number=str(c.get('clause_number', ''))[:50],
                    category=category,
                    clause_text=c.get('clause_text', ''),
                    risk_score=c_score,
                    confidence_score=float(c.get('confidence_score', 0.9)),
                    sentiment=str(c.get('sentiment', 'Neutral'))[:50],
                    identified_risks=c.get('identified_risks', []),
                    suggested_improvements=c.get('suggested_improvements', ''),
                    key_terms=c.get('key_terms', []),
                    page_number=int(c.get('page_number', 1)),
                )
                clause_objs.append(clause_instance)

            created_clauses = ClauseAnalysis.objects.bulk_create(clause_objs)
            for c_obj in created_clauses:
                clause_map[c_obj.clause_number] = c_obj

            # Update clause counts
            ai_record.total_clauses_analyzed = len(created_clauses)
            ai_record.high_risk_count = high_count
            ai_record.medium_risk_count = med_count
            ai_record.low_risk_count = low_count
            ai_record.save(update_fields=['total_clauses_analyzed', 'high_risk_count', 'medium_risk_count', 'low_risk_count'])

            # Persist Risk Flags
            raw_flags = analysis_data.get('risk_flags', [])
            for f in raw_flags:
                sev_str = f.get('severity', SeverityLevel.MEDIUM)
                severity = SeverityLevel.MEDIUM
                for choice in SeverityLevel.values:
                    if choice == sev_str:
                        severity = choice
                        break

                type_str = f.get('risk_type', RiskType.LEGAL)
                risk_type = RiskType.LEGAL
                for choice in RiskType.values:
                    if choice == type_str:
                        risk_type = choice
                        break

                c_num = f.get('clause_number')
                matched_clause = clause_map.get(c_num) if c_num else None

                RiskFlag.objects.create(
                    mou=mou,
                    clause=matched_clause,
                    title=f.get('title', 'Identified Risk Factor')[:255],
                    risk_type=risk_type,
                    severity=severity,
                    description=f.get('description', ''),
                    suggested_action=f.get('suggested_action', ''),
                )

            # Update system metrics
            metrics, _ = AIModelMetrics.objects.get_or_create(id=1)
            metrics.documents_analyzed += 1
            metrics.clauses_analyzed += len(created_clauses)
            if metrics.average_processing_time == 0:
                metrics.average_processing_time = duration
            else:
                metrics.average_processing_time = round((metrics.average_processing_time + duration) / 2, 2)
            metrics.save()

            # Record audit log
            ActivityService.log(
                mou=mou,
                action=ActivityAction.AI_ANALYSIS_RUN,
                actor=actor,
                description=f"AI Contract Intelligence executed using {model_used}. Risk Score: {overall_score}/10 ({len(created_clauses)} clauses evaluated, {len(raw_flags)} flags generated)."
            )

        return ai_record
