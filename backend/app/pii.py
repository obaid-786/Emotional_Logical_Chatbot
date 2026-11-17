import re

PATTERNS = [
    (re.compile(r'\b(?:\d[ -]?){13,19}\b'), '[CARD]'),
    (re.compile(r'\b\d{3}-\d{2}-\d{4}\b'), '[SSN]'),
    (re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b'), '[EMAIL]'),
    (re.compile(r'(?<!\d)(?:\+?\d[\d\s\-()]{8,}\d)(?!\d)'), '[PHONE]'),
]

def redact(text: str) -> str:
    for pat, tag in PATTERNS:
        text = pat.sub(tag, text)
    return text