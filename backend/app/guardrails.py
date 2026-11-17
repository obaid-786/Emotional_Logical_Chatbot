INJECTION_PATTERNS = [
    "ignore previous", "ignore all instructions", "ignore your instructions",
    "system prompt", "you are now", "jailbreak", "disregard the above",
    "reveal your prompt", "print your instructions",
]

def is_safe(text: str) -> bool:
    low = text.lower()
    return not any(p in low for p in INJECTION_PATTERNS)

BLOCKED_RESPONSE = ("I can't help with that request. If you have a real question about our "
                    "products or services, I'm happy to help.")