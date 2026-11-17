import json
import logging
from typing import Dict, Any, Optional
from django.conf import settings
import google.generativeai as genai

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are an expert institutional legal counsel and contract intelligence AI specializing in Memoranda of Understanding (MOUs) between universities/colleges and industrial or external partner organizations.

Analyze the provided agreement text thoroughly with particular attention to institutional safety guardrails:
1. Intellectual Property (IP): Does the partner claim exclusive ownership of student/faculty research IP?
2. Indemnity & Liability: Is there broad, uncapped indemnification or unlimited liability imposed on the college?
3. Governing Law & Jurisdiction: Are disputes subjected to foreign/distant courts rather than the institution's local jurisdiction?
4. Termination & Exit: Can the partner terminate immediately without adequate written notice (30-60 days)?
5. Student Privacy / PII: Does the agreement compromise student records or personal data?
6. Financial Obligations: Are there hidden fees, unilateral expense reimbursements, or penalties?

You must respond ONLY with valid, parseable JSON matching this exact structure:
{
  "overall_risk_score": 3.5,
  "risk_level": "low",
  "compliance_status": "compliant",
  "executive_summary": "Concise 2-4 sentence summary of the MOU scope, key strengths, and areas requiring review.",
  "institutional_checks": {
    "ip_ownership_safe": true,
    "liability_capped": false,
    "local_jurisdiction": true,
    "student_data_safe": true,
    "financial_obligations_clear": true
  },
  "clauses": [
    {
      "clause_number": "Clause 1 or Section 2.1",
      "category": "termination | payment | liability | confidentiality | ip | dispute_resolution | governing_law | force_majeure | performance | warranties | student_privacy | general | other",
      "clause_text": "Exact or representative clause text",
      "risk_score": 4.5,
      "confidence_score": 0.95,
      "sentiment": "Neutral | Unfavorable | Favorable | Ambiguous",
      "identified_risks": ["Risk point 1", "Risk point 2"],
      "suggested_improvements": "Actionable suggestion to safeguard the college",
      "key_terms": ["Indemnity", "Direct Damages"],
      "page_number": 1
    }
  ],
  "risk_flags": [
    {
      "title": "Clear headline of risk",
      "risk_type": "legal | financial | ip | compliance | operational | student_data",
      "severity": "low | medium | high | critical",
      "description": "Why this is dangerous or problematic for the college",
      "suggested_action": "Specific redline or negotiation recommendation",
      "clause_number": "Clause 4.2"
    }
  ]
}

Note:
- overall_risk_score must be a float between 0.0 and 10.0.
- risk_level must be one of: "very_low" (0-3.9), "low" (4.0-5.9), "medium" (6.0-7.9), "high" (8.0-10.0).
- compliance_status must be one of: "compliant", "review_required", "non_compliant".
- Ensure all JSON output is strictly valid without markdown fences or additional commentary.
"""


class GeminiLegalAnalysisService:
    """Zero-cost AI inference using Google Gemini Flash API."""

    @classmethod
    def analyze_document(cls, text: str) -> Optional[Dict[str, Any]]:
        api_key = getattr(settings, 'GEMINI_API_KEY', '').strip()
        if not api_key:
            logger.info("GEMINI_API_KEY is not configured; using offline rule-based legal engine.")
            return None

        try:
            genai.configure(api_key=api_key)
            # Use gemini-1.5-flash or gemini-2.0-flash (both free tier on AI Studio)
            model = genai.GenerativeModel(
                model_name="gemini-1.5-flash",
                generation_config={
                    "response_mime_type": "application/json",
                    "temperature": 0.2,
                },
                system_instruction=SYSTEM_PROMPT,
            )

            prompt = f"Analyze the following MOU agreement text:\n\n{text[:60000]}"
            response = model.generate_content(prompt)

            if not response or not response.text:
                return None

            data = json.loads(response.text)
            return data
        except Exception as e:
            logger.warning(f"Gemini API analysis failed or quota exceeded: {e}; falling back to rule engine.")
            return None
