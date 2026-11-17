from .models import MessageAnalysis

def route(a: MessageAnalysis) -> str:
    # Hard escalation — sensitive intent always goes to human
    if a.intent == "sensitive":
        return "escalate"

    # Hard escalation — confident angry complaints
    if a.emotion in ("angry", "frustrated") and a.intent == "complaint":
        return "escalate"

    # Only truly-lost classifications escalate (parse failures bottom out at 0.5)
    if a.confidence < 0.4:
        return "escalate"

    # Emotional support cases
    if a.emotion in ("sad", "anxious") or a.intent == "request_help":
        return "therapist"

    # Default
    return "logical"