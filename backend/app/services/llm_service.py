"""
LLM Reasoning & Risk Scoring Service
Gemini-powered analysis over retrieved evidence chunks.
Deterministic heuristic scoring layered on top of LLM findings.
API key is read from the GEMINI_API_KEY environment variable — never from user input.
"""

import json
import os
import re
import google.generativeai as genai
from typing import Optional

# ── Configure Gemini once at module load using server-side env var ────────────
_api_key = os.environ.get("GEMINI_API_KEY")
if not _api_key:
    raise RuntimeError("GEMINI_API_KEY environment variable is not set.")
genai.configure(api_key=_api_key)

# ── Risk categories and their retrieval queries ───────────────────────────────
RISK_QUERIES = {
    "data_collection": "what personal data is collected from users",
    "third_party_sharing": "sharing data with third parties advertisers partners",
    "retention_policy": "how long data is retained stored deletion",
    "user_rights": "user rights access deletion opt-out control",
    "tracking_cookies": "cookies tracking pixels fingerprinting advertising",
    "consent_mechanisms": "consent opt-in opt-out user choice",
}

# Heuristic keyword signals for scoring
HIGH_RISK_SIGNALS = [
    "may share", "third parties", "advertising partners", "we may sell",
    "indefinitely", "as long as necessary", "without notice",
    "non-personally identifiable", "aggregate data", "retain indefinitely",
    "cannot opt out", "no right to deletion",
]

LOW_RISK_SIGNALS = [
    "you may request deletion", "opt-out", "you can control",
    "we do not sell", "explicit consent", "right to erasure",
    "data minimization", "limited retention", "you may withdraw",
]

SYSTEM_PROMPT = """You are a privacy policy analyst. You will be given excerpts from a privacy policy and asked to analyze them for a specific risk category.

Respond ONLY with valid JSON in this exact format:
{
  "risk_category": "<category name>",
  "risk_score": <integer 0-10>,
  "summary": "<2-3 sentence summary of findings>",
  "key_findings": ["<finding 1>", "<finding 2>", "<finding 3>"],
  "evidence": ["<direct quote or paraphrase from policy>"],
  "red_flags": ["<concerning clause if any>"],
  "positive_indicators": ["<user-friendly clause if any>"]
}

Be objective. Base findings strictly on the provided text. If evidence is insufficient, say so."""


def analyze_risk_category(
    category_name: str,
    retrieved_chunks: list[dict],
) -> dict:
    """
    Run LLM reasoning over retrieved chunks for one risk category.
    Combines LLM output with deterministic heuristic scoring.
    """
    if not retrieved_chunks:
        return _empty_finding(category_name)

    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        system_instruction=SYSTEM_PROMPT,
    )

    # Assemble context from retrieved evidence
    context = "\n\n---\n\n".join(
        f"[Section: {c['section']}]\n{c['content']}"
        for c in retrieved_chunks[:4]
    )

    prompt = f"""Analyze the following privacy policy excerpts for the risk category: "{category_name}".

POLICY EXCERPTS:
{context}

Analyze the risk level (0 = no risk, 10 = very high risk) and provide structured findings."""

    try:
        response = model.generate_content(prompt)
        raw = response.text.strip()

        # Strip markdown fences if present
        raw = re.sub(r"^```json\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

        finding = json.loads(raw)
        finding["risk_category"] = category_name
        finding["evidence_chunks"] = retrieved_chunks[:3]
        finding["risk_score"] = _heuristic_adjust(finding.get("risk_score", 5), context)
        finding["score_method"] = "llm+heuristic"
        return finding

    except (json.JSONDecodeError, Exception) as e:
        return _empty_finding(category_name, error=str(e))


def _heuristic_adjust(llm_score: int, text: str) -> int:
    """Nudge the LLM score using deterministic keyword signals."""
    text_lower = text.lower()
    high_hits = sum(1 for s in HIGH_RISK_SIGNALS if s in text_lower)
    low_hits  = sum(1 for s in LOW_RISK_SIGNALS  if s in text_lower)
    adjustment = (high_hits * 0.5) - (low_hits * 0.5)
    return max(0, min(10, round(llm_score + adjustment)))


def _empty_finding(category: str, error: Optional[str] = None) -> dict:
    return {
        "risk_category": category,
        "risk_score": 5,
        "summary": "Insufficient evidence found in the policy for this category.",
        "key_findings": ["Could not retrieve relevant clauses."],
        "evidence": [],
        "red_flags": [],
        "positive_indicators": [],
        "evidence_chunks": [],
        "score_method": "default",
        "error": error,
    }


def compute_overall_score(findings: list[dict]) -> dict:
    """Aggregate per-category scores into an overall weighted privacy risk score."""
    weights = {
        "data_collection": 1.0,
        "third_party_sharing": 1.5,
        "retention_policy": 1.2,
        "user_rights": 1.3,
        "tracking_cookies": 1.0,
        "consent_mechanisms": 1.2,
    }

    total_weight = 0.0
    weighted_sum = 0.0

    for finding in findings:
        cat_key = finding["risk_category"].lower().replace(" ", "_")
        weight = weights.get(cat_key, 1.0)
        weighted_sum += finding["risk_score"] * weight
        total_weight += weight

    overall = round(weighted_sum / total_weight, 1) if total_weight > 0 else 5.0

    if overall <= 3:
        label, color = "Low Risk", "green"
    elif overall <= 6:
        label, color = "Moderate Risk", "amber"
    else:
        label, color = "High Risk", "red"

    return {"score": overall, "label": label, "color": color}


def generate_executive_summary(findings: list[dict], overall: dict) -> str:
    """Generate a short plain-language executive summary using Gemini."""
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        top_risks = sorted(findings, key=lambda x: x["risk_score"], reverse=True)[:3]
        risk_lines = "\n".join(
            f"- {f['risk_category']}: {f['risk_score']}/10 — {f['summary']}"
            for f in top_risks
        )
        prompt = f"""Write exactly 2-3 sentences summarizing this privacy policy analysis for a non-technical reader.
Overall risk: {overall['score']}/10 ({overall['label']})
Top risks:\n{risk_lines}\nBe direct and neutral."""

        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception:
        return (
            f"This privacy policy received an overall risk score of {overall['score']}/10 "
            f"({overall['label']}). Review the detailed findings below for category-level analysis."
        )
