# ============================================================
# MedGuardian AI - Smart Triage Engine
# ============================================================

def assess_risk(symptoms):
    """
    Basic safety-oriented triage layer.
    This does NOT diagnose diseases.
    """

    text = symptoms.lower().strip()

    # --------------------------------------------------------
    # EMERGENCY SYMPTOMS
    # --------------------------------------------------------

    emergency_keywords = [
        "chest pain",
        "severe chest pain",
        "difficulty breathing",
        "can't breathe",
        "cannot breathe",
        "shortness of breath",
        "severe bleeding",
        "unconscious",
        "passed out",
        "loss of consciousness",
        "seizure",
        "stroke symptoms",
        "face drooping",
        "slurred speech",
        "sudden weakness",
        "severe allergic reaction",
        "anaphylaxis"
    ]

    for keyword in emergency_keywords:
        if keyword in text:
            return {
                "level": "EMERGENCY",
                "emoji": "🚨",
                "color": "red",
                "message": (
                    "This symptom combination may require urgent "
                    "medical evaluation. Seek emergency medical "
                    "attention immediately."
                ),
                "specialist": "Emergency Medicine"
            }

    # --------------------------------------------------------
    # HIGH RISK
    # --------------------------------------------------------

    high_risk_keywords = [
        "very high fever",
        "high fever",
        "severe headache",
        "severe abdominal pain",
        "severe stomach pain",
        "persistent vomiting",
        "blood in vomit",
        "blood in stool",
        "confusion",
        "fainting",
        "severe dehydration"
    ]

    for keyword in high_risk_keywords:
        if keyword in text:
            return {
                "level": "HIGH",
                "emoji": "🔴",
                "color": "red",
                "message": (
                    "Your symptoms may need prompt medical "
                    "assessment. Please consider contacting a "
                    "healthcare professional soon."
                ),
                "specialist": "General Physician"
            }

    # --------------------------------------------------------
    # MEDIUM RISK
    # --------------------------------------------------------

    medium_keywords = [
        "fever",
        "cough",
        "vomiting",
        "diarrhea",
        "persistent pain",
        "sore throat",
        "ear pain",
        "back pain",
        "stomach pain",
        "abdominal pain",
        "dizziness"
    ]

    for keyword in medium_keywords:
        if keyword in text:
            return {
                "level": "MEDIUM",
                "emoji": "🟡",
                "color": "orange",
                "message": (
                    "Monitor your symptoms and consider consulting "
                    "a healthcare professional if they persist, "
                    "worsen, or new warning signs appear."
                ),
                "specialist": "General Physician"
            }

    # --------------------------------------------------------
    # LOW RISK / GENERAL
    # --------------------------------------------------------

    return {
        "level": "LOW",
        "emoji": "🟢",
        "color": "green",
        "message": (
            "No obvious emergency keyword was detected. "
            "General health information can be provided, but "
            "this system cannot diagnose medical conditions."
        ),
        "specialist": "General Physician"
    }