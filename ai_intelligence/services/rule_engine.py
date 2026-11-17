import re
from typing import List, Dict, Any, Tuple
from ai_intelligence.models import ClauseCategory, RiskType, SeverityLevel


# Regex rules for clause identification
CLAUSE_PATTERNS = [
    (r'(?i)\b(term(?:ination)?|duration|validity|period of agreement|exit)\b', ClauseCategory.TERMINATION),
    (r'(?i)\b(financial|payment|fee|cost|expense|compensation|remuneration)\b', ClauseCategory.PAYMENT),
    (r'(?i)\b(liabilit(?:y|ies)|indemnif(?:y|ication)|hold harmless|damages)\b', ClauseCategory.LIABILITY),
    (r'(?i)\b(confidentia(?:l|lity)|non-disclosure|nda|trade secret|proprietary)\b', ClauseCategory.CONFIDENTIALITY),
    (r'(?i)\b(intellectual property|patent|copyright|trademark|invention|ownership of ip)\b', ClauseCategory.INTELLECTUAL_PROPERTY),
    (r'(?i)\b(dispute|arbitrat(?:ion|or)|conciliation|mediation|settlement)\b', ClauseCategory.DISPUTE_RESOLUTION),
    (r'(?i)\b(governing law|jurisdiction|applicable law|court of)\b', ClauseCategory.GOVERNING_LAW),
    (r'(?i)\b(force majeure|act of god|unforeseen event)\b', ClauseCategory.FORCE_MAJEURE),
    (r'(?i)\b(deliverable|obligation|role|responsibility|scope of work|performance)\b', ClauseCategory.PERFORMANCE),
    (r'(?i)\b(warrant(?:y|ies)|representation|covenant)\b', ClauseCategory.WARRANTIES),
    (r'(?i)\b(student|academic record|data privacy|ferpa|gdpr|pii|personal information)\b', ClauseCategory.STUDENT_PRIVACY),
]

# Guardrail risk detection rules
GUARDRAIL_RULES = [
    {
        'id': 'unlimited_indemnity',
        'type': RiskType.LEGAL,
        'severity': SeverityLevel.HIGH,
        'title': 'Potentially Unlimited Indemnification / Liability',
        'pattern': r'(?i)\b(indemnif\w+.*against (?:all|any and all) (?:claims|losses|damages)|unlimited liability|no limit(?:ation)? of liability)\b',
        'description': 'The clause appears to impose broad or uncapped indemnification on the institution without clear financial limitations.',
        'action': 'Limit indemnification to actual direct damages and insert a mutual liability cap (e.g. aggregate value of agreement or standard fixed cap).',
    },
    {
        'id': 'ip_assignment',
        'type': RiskType.IP,
        'severity': SeverityLevel.HIGH,
        'title': 'Unilateral Intellectual Property Assignment',
        'pattern': r'(?i)\b((?:all|sole) (?:right|title|interest|ownership) in (?:any|all) (?:ip|inventions|work product) shall (?:vest in|belong exclusively to) (?:the partner|company))\b',
        'description': 'The agreement assigns ownership of generated intellectual property exclusively to the partner, potentially depriving students and faculty of their research inventions.',
        'action': 'Negotiate mutual or joint IP ownership, or ensure the college retains a non-exclusive, perpetual, royalty-free license for educational/research purposes.',
    },
    {
        'id': 'foreign_jurisdiction',
        'type': RiskType.LEGAL,
        'severity': SeverityLevel.MEDIUM,
        'title': 'Non-Local Dispute Jurisdiction',
        'pattern': r'(?i)\b(courts? of (?:singapore|london|new york|delaware|england)|exclusive jurisdiction of the courts of (?!local))\b',
        'description': 'Disputes are subjected to distant or foreign courts, which can result in prohibitive legal costs for the institution.',
        'action': 'Request governing law and arbitration to be seated within the college’s local state/territory or under standard institutional arbitration rules.',
    },
    {
        'id': 'unilateral_termination',
        'type': RiskType.OPERATIONAL,
        'severity': SeverityLevel.MEDIUM,
        'title': 'Unilateral or Immediate Termination Without Remedy',
        'pattern': r'(?i)\b(terminate (?:immediately|without (?:any )?prior notice)|sole discretion to terminate)\b',
        'description': 'Allows the partner to terminate the partnership immediately without giving the college adequate notice to safeguard ongoing student academic activities.',
        'action': 'Require at least 30 to 60 days written notice with a cure period for any alleged default.',
    },
    {
        'id': 'student_data_exposure',
        'type': RiskType.STUDENT_DATA,
        'severity': SeverityLevel.HIGH,
        'title': 'Potential Student Data / PII Exposure',
        'pattern': r'(?i)\b(student (?:records|data|information|performance) (?:shared|transferred|accessible)|access to student database)\b',
        'description': 'Provisions grant partner access to student personal information or academic records without explicit consent safeguards.',
        'action': 'Ensure strict compliance with student data privacy laws, restricting data transfer to anonymized statistics or verified opt-in consent.',
    },
    {
        'id': 'unspecified_fees',
        'type': RiskType.FINANCIAL,
        'severity': SeverityLevel.MEDIUM,
        'title': 'Ambiguous Financial Obligation',
        'pattern': r'(?i)\b(institution shall (?:bear|pay|reimburse) (?:all|reasonable)? costs|additional fees as may be determined)\b',
        'description': 'Imposes open-ended financial or reimbursement responsibilities on the institution without a fixed budget ceiling.',
        'action': 'Explicitly specify that neither party has financial obligations unless agreed to in a separate, mutually signed financial addendum.',
    },
]


class RuleBasedLegalEngine:
    """Offline, deterministic rule-based analysis engine for MOU documents."""

    @classmethod
    def segment_clauses(cls, text: str) -> List[Dict[str, Any]]:
        """Segments raw agreement text into distinct clauses or paragraphs."""
        clauses: List[Dict[str, Any]] = []

        # Split on standard clause numbering: "1.", "1.1", "Article I", "Section 1", "Clause 1", etc.
        pattern = r'(?:\n|\r\n)(?=(?:(?:Article|Section|Clause)\s+[0-9IVXLCDM]+|[0-9]{1,2}(?:\.[0-9]{1,2})*\.?\s+[A-Z]))'
        raw_chunks = re.split(pattern, text)

        if len(raw_chunks) <= 1:
            # Fallback to double newline paragraphs
            raw_chunks = [p.strip() for p in text.split('\n\n') if len(p.strip()) > 40]

        for idx, chunk in enumerate(raw_chunks, start=1):
            clean_chunk = chunk.strip()
            if not clean_chunk or len(clean_chunk) < 25:
                continue

            # Extract clause heading or number if present
            header_match = re.match(r'^((?:Article|Section|Clause)?\s*[0-9IVXLCDM.]*[\s:-]*[^\n.]+)', clean_chunk)
            clause_number = f"Clause {idx}"
            if header_match:
                clause_number = header_match.group(1).strip()[:40]

            category = cls.classify_clause(clean_chunk)
            risk_score, identified_risks, suggestions = cls.evaluate_clause_risk(clean_chunk, category)

            clauses.append({
                'clause_number': clause_number,
                'category': category,
                'clause_text': clean_chunk,
                'risk_score': risk_score,
                'confidence_score': 0.85,
                'sentiment': 'Unfavorable' if risk_score >= 6.0 else 'Neutral',
                'identified_risks': identified_risks,
                'suggested_improvements': suggestions,
                'key_terms': cls.extract_key_terms(clean_chunk),
                'page_number': 1,
            })

        return clauses

    @classmethod
    def classify_clause(cls, text: str) -> ClauseCategory:
        for pattern, category in CLAUSE_PATTERNS:
            if re.search(pattern, text):
                return category
        return ClauseCategory.GENERAL

    @classmethod
    def evaluate_clause_risk(cls, text: str, category: ClauseCategory) -> Tuple[float, List[str], str]:
        risks: List[str] = []
        suggestions: List[str] = []
        score = 2.0  # Base standard score

        for rule in GUARDRAIL_RULES:
            if re.search(rule['pattern'], text):
                risks.append(rule['title'])
                suggestions.append(rule['action'])
                if rule['severity'] == SeverityLevel.HIGH:
                    score += 4.5
                elif rule['severity'] == SeverityLevel.CRITICAL:
                    score += 6.0
                else:
                    score += 2.5

        # Check for missing essentials in critical categories
        if category == ClauseCategory.LIABILITY and not re.search(r'(?i)\bcap(?:ped)?|limit(?:ation)? of liability\b', text):
            risks.append("No explicit limitation of liability found")
            suggestions.append("Add a clause capping liability to direct damages only.")
            score += 2.0

        if category == ClauseCategory.INTELLECTUAL_PROPERTY and not re.search(r'(?i)\bmutual|joint|retains all right\b', text):
            risks.append("IP ownership rights not explicitly mutual")
            suggestions.append("Clarify that background IP remains the property of the respective creator.")
            score += 2.0

        final_score = min(round(score, 1), 10.0)
        return final_score, risks, " ".join(suggestions)

    @classmethod
    def extract_key_terms(cls, text: str) -> List[str]:
        terms = set()
        candidates = ['intellectual property', 'indemnify', 'termination', 'confidential', 'arbitration', 'liability', 'notice', 'deliverables', 'warranty']
        for c in candidates:
            if re.search(rf'(?i)\b{c}\b', text):
                terms.add(c.capitalize())
        return list(terms)[:5]

    @classmethod
    def analyze_full_document(cls, text: str) -> Dict[str, Any]:
        """Runs the complete offline rule-based pipeline on the full text."""
        clauses = cls.segment_clauses(text)
        if not clauses:
            return {
                'overall_risk_score': 2.0,
                'risk_level': 'very_low',
                'compliance_status': 'compliant',
                'executive_summary': 'No substantial contractual text detected or agreement is very concise.',
                'clauses': [],
                'risk_flags': [],
                'institutional_checks': {},
            }

        clause_scores = [c['risk_score'] for c in clauses]
        avg_score = sum(clause_scores) / len(clause_scores)
        # Cap overall score and weight high-risk clauses
        high_risk_clauses = [c for c in clauses if c['risk_score'] >= 7.0]
        if high_risk_clauses:
            overall_score = round(max(avg_score, 6.5 + (len(high_risk_clauses) * 0.5)), 1)
        else:
            overall_score = round(avg_score, 1)
        overall_score = min(overall_score, 10.0)

        # Risk level determination
        if overall_score >= 8.0:
            risk_level = 'high'
            compliance_status = 'review_required'
        elif overall_score >= 6.0:
            risk_level = 'medium'
            compliance_status = 'review_required'
        elif overall_score >= 4.0:
            risk_level = 'low'
            compliance_status = 'compliant'
        else:
            risk_level = 'very_low'
            compliance_status = 'compliant'

        # Generate actionable risk flags
        risk_flags = []
        for c in clauses:
            for rule in GUARDRAIL_RULES:
                if re.search(rule['pattern'], c['clause_text']):
                    risk_flags.append({
                        'title': rule['title'],
                        'risk_type': rule['type'],
                        'severity': rule['severity'],
                        'description': f"{rule['description']} (Detected in: {c['clause_number']})",
                        'suggested_action': rule['action'],
                        'clause_number': c['clause_number'],
                    })

        # Institutional checks summary
        institutional_checks = {
            'ip_ownership_safe': not any(f['risk_type'] == RiskType.IP for f in risk_flags),
            'liability_capped': not any('indemn' in f['title'].lower() for f in risk_flags),
            'local_jurisdiction': not any('jurisdiction' in f['title'].lower() for f in risk_flags),
            'student_data_safe': not any(f['risk_type'] == RiskType.STUDENT_DATA for f in risk_flags),
            'financial_obligations_clear': not any(f['risk_type'] == RiskType.FINANCIAL for f in risk_flags),
        }

        executive_summary = (
            f"The agreement contains {len(clauses)} analyzed clauses with an overall risk score of {overall_score}/10. "
            f"Identified {len(high_risk_clauses)} high-risk areas requiring institutional review. "
            f"IP safety: {'PASSED' if institutional_checks['ip_ownership_safe'] else 'ACTION REQUIRED'}, "
            f"Liability cap: {'VERIFIED' if institutional_checks['liability_capped'] else 'UNCAPPED'}, "
            f"Jurisdiction: {'STANDARD' if institutional_checks['local_jurisdiction'] else 'REVIEW SEAT'}."
        )

        return {
            'overall_risk_score': overall_score,
            'risk_level': risk_level,
            'compliance_status': compliance_status,
            'executive_summary': executive_summary,
            'clauses': clauses,
            'risk_flags': risk_flags,
            'institutional_checks': institutional_checks,
        }
