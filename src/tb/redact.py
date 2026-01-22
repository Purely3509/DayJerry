from __future__ import annotations

import re

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?:(?:\+?\d{1,3}[\s-]?)?(?:\(\d{2,4}\)[\s-]?)?\d{3,4}[\s-]?\d{3,4})")
LONG_NUMBER_RE = re.compile(r"\b\d{8,}\b")
URL_RE = re.compile(r"https?://\S+")


def redact_text(text: str, redact_urls: bool = True) -> str:
    if not text:
        return text
    redacted = EMAIL_RE.sub("[REDACTED_EMAIL]", text)
    redacted = PHONE_RE.sub("[REDACTED_PHONE]", redacted)
    redacted = LONG_NUMBER_RE.sub("[REDACTED_NUMBER]", redacted)
    if redact_urls:
        redacted = URL_RE.sub("[REDACTED_URL]", redacted)
    return redacted
