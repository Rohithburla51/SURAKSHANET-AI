"""
backend/core/demo_responses.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SurakshaNet AI — Static Demo / Fallback Responses
Model: Claude Sonnet 4.6 (1.3x)

Used when DEMO_MOCK_MODE=true OR when all external services (Groq, Supabase)
are unavailable during a live demo or hackathon judging run.

Every response is pre-formatted to match the exact Pydantic schema returned
by the real agents so the frontend never needs a code-path branch.
"""

from __future__ import annotations

# ─────────────────────────────────────────────────────────────────────────────
# Scam Analysis — ScamAnalysisResult compatible dicts
# ─────────────────────────────────────────────────────────────────────────────

DEMO_SCAM_DIGITAL_ARREST: dict = {
    "risk_score": 97,
    "category": "digital_arrest",
    "confidence": 0.98,
    "verdict": "SCAM",
    "manipulation_tactics": [
        "authority_impersonation",
        "fear_induction",
        "isolation",
        "urgency",
        "threatened_legal_action",
    ],
    "red_flags": [
        "Caller claims to be CBI / ED / Customs officer with badge number",
        "Victim is told their Aadhaar is linked to a money-laundering case",
        "Demand to stay on video call and not inform family ('digital custody')",
        "Immediate wire-transfer demand to a 'RBI verification account'",
        "Threat of arrest within hours if money is not transferred",
    ],
    "explanation": (
        "This message is a textbook **Digital Arrest** scam — one of the most "
        "psychologically aggressive fraud patterns targeting Indian citizens. "
        "The fraudster impersonates a federal law-enforcement officer to create "
        "extreme fear and a false sense of legal jeopardy. Victims are isolated "
        "from family so no one can reality-check the threat, then coerced into "
        "an immediate large transfer. No legitimate government agency in India "
        "operates through video calls or demands instant transfers."
    ),
    "explanation_hi": (
        "यह संदेश एक 'डिजिटल अरेस्ट' घोटाला है। कोई भी असली सरकारी एजेंसी "
        "वीडियो कॉल पर गिरफ्तारी की धमकी नहीं देती या तुरंत पैसे नहीं माँगती। "
        "कॉल काटें, परिवार को बताएं, और 1930 साइबर क्राइम हेल्पलाइन पर कॉल करें।"
    ),
    "recommended_actions": [
        "Hang up immediately — do not transfer any money.",
        "Call Cyber Crime Helpline 1930 to report the incident.",
        "File a complaint at https://cybercrime.gov.in",
        "Inform your bank to freeze any recent suspicious transactions.",
        "Alert family members so they are not targeted next.",
    ],
    "rag_matches_used": [
        {
            "category": "digital_arrest",
            "similarity": 0.96,
            "excerpt": "CBI officer claims Aadhaar linked to narcotics smuggling…",
        }
    ],
    "model_used": "demo_mock",
    "processing_time_ms": 12,
}

DEMO_SCAM_KYC_PHISHING: dict = {
    "risk_score": 89,
    "category": "kyc_phishing",
    "confidence": 0.93,
    "verdict": "SCAM",
    "manipulation_tactics": [
        "urgency",
        "authority_impersonation",
        "fear_induction",
    ],
    "red_flags": [
        "24-hour account suspension deadline creates panic",
        "Suspicious APK download link from non-official domain",
        "Request to share OTP — banks never ask for OTP",
        "SMS sender ID spoofed to look like SBIINB / HDFCBK",
    ],
    "explanation": (
        "This is a **KYC Phishing** attack. The fraudster impersonates a bank or "
        "telecom provider and creates an artificial deadline (account blocked in "
        "24 hours) to bypass the victim's rational thinking. The link leads to a "
        "fake banking page or a malicious APK that steals credentials and OTPs. "
        "Legitimate banks never ask for OTPs or request APK installations via SMS."
    ),
    "explanation_hi": (
        "यह एक KYC फ़िशिंग घोटाला है। बैंक कभी SMS या WhatsApp पर OTP नहीं माँगते। "
        "लिंक पर क्लिक न करें। बैंक की आधिकारिक वेबसाइट पर जाएं।"
    ),
    "recommended_actions": [
        "Do not click any links in the message.",
        "Do not download any APK files.",
        "Contact your bank directly on the number on the back of your card.",
        "Report the SMS to 1930 Cyber Crime Helpline.",
    ],
    "rag_matches_used": [
        {
            "category": "kyc_phishing",
            "similarity": 0.91,
            "excerpt": "Your SBI account will be blocked. Update KYC immediately…",
        }
    ],
    "model_used": "demo_mock",
    "processing_time_ms": 10,
}

DEMO_SCAM_UPI_FRAUD: dict = {
    "risk_score": 82,
    "category": "upi_collect_fraud",
    "confidence": 0.88,
    "verdict": "SCAM",
    "manipulation_tactics": [
        "false_reward",
        "urgency",
        "social_engineering",
    ],
    "red_flags": [
        "Unsolicited UPI 'collect' request — you must enter PIN to RECEIVE money",
        "Prize/lottery/refund claim from unknown sender",
        "PIN entry to receive money is the opposite of how UPI works",
        "Time pressure: 'Offer expires in 10 minutes'",
    ],
    "explanation": (
        "This is a **UPI Collect Request** scam. The attacker sends a payment "
        "collect request (which requires the victim to enter their UPI PIN) and "
        "frames it as 'receiving' a lottery prize or refund. In reality, entering "
        "the PIN authorises a debit from your account to the attacker. "
        "You never need to enter your PIN to receive money on UPI."
    ),
    "explanation_hi": (
        "UPI पर पैसे पाने के लिए कभी PIN दर्ज नहीं करना होता। "
        "यह एक 'कलेक्ट रिक्वेस्ट' घोटाला है। रिक्वेस्ट अस्वीकार करें।"
    ),
    "recommended_actions": [
        "Decline the UPI collect request immediately.",
        "Never enter your UPI PIN to 'receive' money — it only debits you.",
        "Block the sender on your UPI app.",
        "Report to your bank and file at cybercrime.gov.in.",
    ],
    "rag_matches_used": [
        {
            "category": "upi_collect_fraud",
            "similarity": 0.87,
            "excerpt": "Congratulations! You've won ₹50,000. Accept UPI request…",
        }
    ],
    "model_used": "demo_mock",
    "processing_time_ms": 9,
}

DEMO_SCAM_SAFE: dict = {
    "risk_score": 4,
    "category": "safe",
    "confidence": 0.97,
    "verdict": "SAFE",
    "manipulation_tactics": [],
    "red_flags": [],
    "explanation": (
        "This message does not exhibit any known scam patterns. "
        "No urgency triggers, authority impersonation, suspicious links, "
        "or financial pressure tactics were detected."
    ),
    "explanation_hi": "इस संदेश में कोई घोटाले के संकेत नहीं मिले।",
    "recommended_actions": [
        "No immediate action required.",
        "Stay vigilant — always verify unexpected requests through official channels.",
    ],
    "rag_matches_used": [],
    "model_used": "demo_mock",
    "processing_time_ms": 8,
}

# Default fallback when category cannot be determined
DEMO_SCAM_GENERIC_HIGH_RISK: dict = {
    "risk_score": 75,
    "category": "unknown_suspicious",
    "confidence": 0.70,
    "verdict": "LIKELY_SCAM",
    "manipulation_tactics": ["urgency", "social_engineering"],
    "red_flags": [
        "Unsolicited contact demanding immediate financial action",
        "Pressure tactics detected",
    ],
    "explanation": (
        "This message contains multiple hallmarks of a financial scam. "
        "Exercise extreme caution. Do not transfer money or share personal "
        "details until you have independently verified the sender's identity "
        "through official channels."
    ),
    "explanation_hi": (
        "इस संदेश में घोटाले के संकेत हैं। पैसे न भेजें, "
        "और 1930 पर कॉल करके सहायता लें।"
    ),
    "recommended_actions": [
        "Do not respond or transfer money.",
        "Verify the sender via official channels.",
        "Call Cyber Crime Helpline 1930 if in doubt.",
        "Report at https://cybercrime.gov.in",
    ],
    "rag_matches_used": [],
    "model_used": "demo_mock",
    "processing_time_ms": 11,
}

# Registry — keyed by scam category slug for quick lookup
DEMO_SCAM_RESPONSES: dict[str, dict] = {
    "digital_arrest":     DEMO_SCAM_DIGITAL_ARREST,
    "kyc_phishing":       DEMO_SCAM_KYC_PHISHING,
    "upi_collect_fraud":  DEMO_SCAM_UPI_FRAUD,
    "safe":               DEMO_SCAM_SAFE,
    "default":            DEMO_SCAM_GENERIC_HIGH_RISK,
}


def get_demo_scam_response(hint: str = "default") -> dict:
    """
    Return a canned ScamAnalysisResult-compatible dict for demo/fallback mode.

    hint: any substring of a category slug (e.g. 'arrest', 'kyc', 'upi', 'safe').
    Falls back to 'default' if hint doesn't match any key.
    """
    hint_lower = hint.lower()
    for key in DEMO_SCAM_RESPONSES:
        if key in hint_lower or hint_lower in key:
            return DEMO_SCAM_RESPONSES[key]
    return DEMO_SCAM_RESPONSES["default"]


# ─────────────────────────────────────────────────────────────────────────────
# Counterfeit Detection — CounterfeitResult compatible dicts
# Three fixtures covering every possible verdict branch.
# ─────────────────────────────────────────────────────────────────────────────

DEMO_COUNTERFEIT_GENUINE: dict = {
    "verdict": "GENUINE",
    "final_score": 96,
    "confidence": 0.97,
    "denomination": 500,
    "features_passed": [
        "watermark_opacity",
        "intaglio_sharpness",
        "security_thread",
        "microprint_clarity",
        "color_shift_ink",
        "bleed_lines",
        "latent_image",
    ],
    "features_failed": [],
    "opencv_metrics": {
        "clahe_contrast_score": 0.91,
        "fft_watermark_opacity": 0.88,
        "laplacian_variance":    412.7,
        "sobel_edge_density":    0.73,
        "bleed_line_count":      12,
    },
    "explanation": (
        "The ₹500 note passed all 7 structural integrity checks. "
        "FFT analysis detected a strong RBI watermark signature (opacity 0.88). "
        "Laplacian variance of 412.7 confirms sharp, genuine intaglio printing. "
        "No anomalies were found in the security thread, microprint, or bleed-line geometry."
    ),
    "recommended_actions": [
        "Note appears genuine. Accept it normally.",
        "If still uncertain, use the UV verification lamp at your counter.",
    ],
    "model_used": "demo_mock",
    "processing_time_ms": 18,
}

DEMO_COUNTERFEIT_SUSPECT: dict = {
    "verdict": "SUSPECT",
    "final_score": 54,
    "confidence": 0.71,
    "denomination": 500,
    "features_passed": [
        "security_thread",
        "color_shift_ink",
        "bleed_lines",
    ],
    "features_failed": [
        "watermark_opacity",
        "intaglio_sharpness",
        "microprint_clarity",
        "latent_image",
    ],
    "opencv_metrics": {
        "clahe_contrast_score": 0.62,
        "fft_watermark_opacity": 0.41,
        "laplacian_variance":    89.3,
        "sobel_edge_density":    0.44,
        "bleed_line_count":      7,
    },
    "explanation": (
        "This note raised significant concerns on 4 of 7 structural checks. "
        "FFT watermark opacity is abnormally low (0.41 vs expected ≥0.75), "
        "suggesting the Gandhi watermark may be printed rather than embedded. "
        "Laplacian variance of 89.3 indicates blurred intaglio relief — a common "
        "marker of inkjet-printed counterfeits. Microprint text appears degraded. "
        "Withhold the note and escalate to your branch manager for UV lamp verification."
    ),
    "recommended_actions": [
        "Do NOT return the note to the customer.",
        "Escalate to branch manager for UV and feel-based manual check.",
        "If confirmed suspect, impound and file FIR with the local police.",
        "Report to RBI Counterfeit Currency Reporting Cell.",
    ],
    "model_used": "demo_mock",
    "processing_time_ms": 22,
}

DEMO_COUNTERFEIT_COUNTERFEIT: dict = {
    "verdict": "COUNTERFEIT",
    "final_score": 11,
    "confidence": 0.95,
    "denomination": 500,
    "features_passed": [
        "color_shift_ink",   # surface ink can be approximated by high-quality printers
    ],
    "features_failed": [
        "watermark_opacity",
        "intaglio_sharpness",
        "security_thread",
        "microprint_clarity",
        "bleed_lines",
        "latent_image",
    ],
    "opencv_metrics": {
        "clahe_contrast_score": 0.38,
        "fft_watermark_opacity": 0.09,
        "laplacian_variance":    14.2,
        "sobel_edge_density":    0.21,
        "bleed_line_count":      2,
    },
    "explanation": (
        "HIGH CONFIDENCE COUNTERFEIT DETECTED. "
        "6 of 7 structural integrity checks failed critically. "
        "FFT watermark score of 0.09 (threshold: 0.60) indicates no embedded security "
        "watermark — this is a printed forgery. "
        "Laplacian variance of 14.2 confirms completely flat, non-intaglio printing. "
        "Only 2 bleed lines detected vs the 14–16 expected on a genuine ₹500 note. "
        "Security thread appears absent or printed on the surface. "
        "Do not accept this note under any circumstances."
    ),
    "recommended_actions": [
        "REJECT the note immediately. Do not return to the presenter.",
        "Detain the note — it is evidence.",
        "Note the presenter's details if possible without confrontation.",
        "Call local police and file an FIR immediately.",
        "Report to RBI via https://www.rbi.org.in/counterfeit",
        "Alert your bank's security team and regional manager.",
    ],
    "model_used": "demo_mock",
    "processing_time_ms": 25,
}

# Registry for counterfeit demo fixtures
DEMO_COUNTERFEIT_RESPONSES: dict[str, dict] = {
    "genuine":      DEMO_COUNTERFEIT_GENUINE,
    "suspect":      DEMO_COUNTERFEIT_SUSPECT,
    "counterfeit":  DEMO_COUNTERFEIT_COUNTERFEIT,
    "default":      DEMO_COUNTERFEIT_SUSPECT,   # conservative default
}


def get_demo_counterfeit_response(hint: str = "default") -> dict:
    """
    Return a canned CounterfeitResult-compatible dict for demo/fallback mode.

    hint: 'genuine' | 'suspect' | 'counterfeit' | 'default'
    Falls back to SUSPECT (conservative) if hint is unrecognised.
    """
    hint_lower = hint.lower()
    for key in DEMO_COUNTERFEIT_RESPONSES:
        if key in hint_lower:
            return dict(DEMO_COUNTERFEIT_RESPONSES[key])   # return a copy — callers mutate it
    return dict(DEMO_COUNTERFEIT_RESPONSES["default"])


# ─────────────────────────────────────────────────────────────────────────────
# Network / NL-to-Cypher — NetworkQueryResult compatible dicts
# Backs the police dashboard during demos and fallback scenarios.
# ─────────────────────────────────────────────────────────────────────────────

DEMO_NETWORK_ACTOR_LOOKUP: dict = {
    "question": "Find all mule accounts connected to Operator Alpha",
    "cypher_query": (
        "MATCH (a:FraudActor {name: 'Operator Alpha'})-[r*1..3]-(connected) "
        "RETURN a, r, connected LIMIT 50"
    ),
    "is_safe": True,
    "query_explanation": (
        "Traverses up to 3 hops from the FraudActor 'Operator Alpha' to find "
        "all connected entities including mule bank accounts, phone numbers, "
        "and UPI IDs."
    ),
    "summary": (
        "Operator Alpha is the central ringleader of a Jharkhand-based syndicate. "
        "The query surfaced 8 connected nodes: 3 mule SBI bank accounts, "
        "2 burner phone numbers operating across Mumbai and Delhi telecom circles, "
        "1 UPI ID linked to a wallet provider, and 2 secondary FraudActors acting "
        "as mid-tier handlers. Recommend immediate freeze action on the 3 bank "
        "accounts and SIM blocking on both phone numbers."
    ),
    "nodes": [
        {"id": "actor_alpha",  "label": "FraudActor",   "name": "Operator Alpha",     "role": "RINGLEADER",  "state": "Jharkhand"},
        {"id": "phone_1",      "label": "PhoneNumber",  "number": "+919876543210",    "telecom": "Jio",      "state": "Maharashtra"},
        {"id": "phone_2",      "label": "PhoneNumber",  "number": "+918765432109",    "telecom": "Airtel",   "state": "Delhi"},
        {"id": "bank_1",       "label": "BankAccount",  "account_id": "SBI-XXXX1234", "bank": "SBI",         "flagged": True},
        {"id": "bank_2",       "label": "BankAccount",  "account_id": "HDFC-XXXX5678","bank": "HDFC",        "flagged": True},
        {"id": "bank_3",       "label": "BankAccount",  "account_id": "ICICI-XXXX9012","bank": "ICICI",      "flagged": True},
        {"id": "upi_1",        "label": "UPIId",        "upi_id": "operator.alpha@paytm"},
        {"id": "actor_beta",   "label": "FraudActor",   "name": "Handler Beta",       "role": "MID_TIER",    "state": "Jharkhand"},
        {"id": "actor_gamma",  "label": "FraudActor",   "name": "Handler Gamma",      "role": "MID_TIER",    "state": "Bihar"},
    ],
    "edges": [
        {"source": "actor_alpha", "target": "phone_1",     "label": "USES"},
        {"source": "actor_alpha", "target": "phone_2",     "label": "USES"},
        {"source": "actor_alpha", "target": "bank_1",      "label": "CONTROLS"},
        {"source": "actor_alpha", "target": "bank_2",      "label": "CONTROLS"},
        {"source": "actor_alpha", "target": "upi_1",       "label": "OPERATES"},
        {"source": "actor_alpha", "target": "actor_beta",  "label": "DIRECTS"},
        {"source": "actor_alpha", "target": "actor_gamma", "label": "DIRECTS"},
        {"source": "actor_beta",  "target": "bank_3",      "label": "CONTROLS"},
    ],
    "row_count": 8,
    "model_used": "demo_mock",
    "processing_time_ms": 23,
}

DEMO_NETWORK_PHONE_TRACE: dict = {
    "question": "Show me all entities connected to phone number +919876543210",
    "cypher_query": (
        "MATCH path = (p:PhoneNumber {number: '+919876543210'})-[*1..3]-(connected) "
        "RETURN nodes(path) AS nodes, relationships(path) AS rels LIMIT 100"
    ),
    "is_safe": True,
    "query_explanation": (
        "Performs a 3-hop traversal from the seed PhoneNumber to surface every "
        "actor, bank account, and victim linked through any relationship type."
    ),
    "summary": (
        "Phone +919876543210 is operated by Operator Alpha and is linked to "
        "2 mule bank accounts and 4 victims who lost a combined ₹14.2 lakh "
        "across Q1 2026. The number is registered on Jio with a Maharashtra "
        "circle origin but call records show frequent activity from "
        "Jharkhand-based towers."
    ),
    "nodes": [
        {"id": "phone_1",      "label": "PhoneNumber",  "number": "+919876543210",     "telecom": "Jio"},
        {"id": "actor_alpha",  "label": "FraudActor",   "name": "Operator Alpha",      "role": "RINGLEADER"},
        {"id": "bank_1",       "label": "BankAccount",  "account_id": "SBI-XXXX1234",  "bank": "SBI"},
        {"id": "victim_1",     "label": "Victim",       "case_id": "NCRB-2026-MH-0142","state": "Maharashtra", "amount_lost": 450000},
        {"id": "victim_2",     "label": "Victim",       "case_id": "NCRB-2026-DL-0089","state": "Delhi",        "amount_lost": 320000},
    ],
    "edges": [
        {"source": "actor_alpha", "target": "phone_1",  "label": "USES"},
        {"source": "phone_1",     "target": "victim_1", "label": "CALLED"},
        {"source": "phone_1",     "target": "victim_2", "label": "CALLED"},
        {"source": "victim_1",    "target": "bank_1",   "label": "TRANSFERRED_TO"},
        {"source": "victim_2",    "target": "bank_1",   "label": "TRANSFERRED_TO"},
    ],
    "row_count": 5,
    "model_used": "demo_mock",
    "processing_time_ms": 19,
}

DEMO_NETWORK_UNSAFE_QUERY: dict = {
    "question": "Delete all fraud actors in Jharkhand",
    "cypher_query": (
        "MATCH (a:FraudActor {state: 'Jharkhand'}) DETACH DELETE a"
    ),
    "is_safe": False,
    "query_explanation": (
        "Generated query contained a DELETE clause and has been rejected by the "
        "safety auditor. The translation layer only permits read-only operations."
    ),
    "summary": (
        "Query rejected: this operation would mutate the graph (DETACH DELETE). "
        "The Police Intelligence Dashboard is restricted to read-only forensic "
        "queries. To remove a FraudActor from the case database, please use the "
        "Case Management module which requires Inspector-level authentication."
    ),
    "nodes": [],
    "edges": [],
    "row_count": 0,
    "model_used": "demo_mock",
    "processing_time_ms": 8,
}

DEMO_NETWORK_EMPTY_RESULT: dict = {
    "question": "Find connections for an unknown identifier",
    "cypher_query": (
        "MATCH (n {identifier: 'UNKNOWN-XXX'})-[*1..2]-(connected) "
        "RETURN n, connected LIMIT 20"
    ),
    "is_safe": True,
    "query_explanation": (
        "Searches for any node matching the provided identifier and returns "
        "connected entities within 2 hops."
    ),
    "summary": (
        "No matching entities were found in the fraud graph for this identifier. "
        "This could mean the identifier has not yet been catalogued in our system, "
        "or there are no recorded connections to known cases. Try searching by a "
        "partial phone number, bank account, or actor alias."
    ),
    "nodes": [],
    "edges": [],
    "row_count": 0,
    "model_used": "demo_mock",
    "processing_time_ms": 12,
}

# Registry for network demo fixtures
DEMO_NETWORK_RESPONSES: dict[str, dict] = {
    "actor":     DEMO_NETWORK_ACTOR_LOOKUP,
    "phone":     DEMO_NETWORK_PHONE_TRACE,
    "unsafe":    DEMO_NETWORK_UNSAFE_QUERY,
    "empty":     DEMO_NETWORK_EMPTY_RESULT,
    "default":   DEMO_NETWORK_ACTOR_LOOKUP,
}


def get_demo_network_response(hint: str = "default") -> dict:
    """
    Return a canned NetworkQueryResult-compatible dict for demo/fallback mode.

    hint: any substring of a key like 'actor', 'phone', 'unsafe', 'empty'.
    Falls back to the actor-lookup demo on no match.
    """
    hint_lower = hint.lower()
    for key in DEMO_NETWORK_RESPONSES:
        if key in hint_lower:
            return dict(DEMO_NETWORK_RESPONSES[key])
    return dict(DEMO_NETWORK_RESPONSES["default"])
