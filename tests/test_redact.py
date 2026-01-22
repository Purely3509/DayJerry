from tb.redact import redact_text


def test_redact_text_patterns():
    text = "Email me at jane@example.com or call 415-555-1234. Ref 12345678. https://example.com"
    redacted = redact_text(text)
    assert "[REDACTED_EMAIL]" in redacted
    assert "[REDACTED_PHONE]" in redacted
    assert "[REDACTED_NUMBER]" in redacted
    assert "[REDACTED_URL]" in redacted
