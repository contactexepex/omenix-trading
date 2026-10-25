"""The public-record safety scan (``fno/shared/record_scan``): planted (synthetic) secrets are flagged, clean text
passes, allowed channel IDs pass, and code files are scanned only for credential shapes.

No real secret appears in this file. Credential-shaped strings are assembled at runtime by concatenation, so no
credential-shaped *literal* exists for the commit hook (which scans ``tests/`` for credential shapes) to trip on."""

from __future__ import annotations

import pytest

from fno.shared.record_scan.scanner import Finding, RecordScanner
from fno.shared.record_scan.wiring import build_record_scanner

# Assembled at runtime; neither half is a credential-shaped literal on its own.
FAKE_AWS_KEY = "AKIA" + "A1B2C3D4E5F6G7H8"  # AKIA + 16 chars: AWS access-key shape
FAKE_AI_KEY = "sk-" + "proj-" + "0123456789abcdefghijklmnop"  # sk-proj-... shape
# A value written next to a secret's name: a record pattern, NOT a credential shape (safe to write literally).
SECRET_ASSIGNMENT = "api_key = s3cr3tvalue99"


def _kinds(findings: list[Finding]) -> set[str]:
    return {f.kind for f in findings}


def test_build_record_scanner_is_a_scanner() -> None:
    assert isinstance(build_record_scanner(), RecordScanner)


def test_secret_assignment_flagged_in_a_record() -> None:
    scanner = build_record_scanner()
    findings = scanner.scan_text("journal/notes.md", f"some prose\n{SECRET_ASSIGNMENT}\nmore prose\n")
    assert "value next to a secret's name" in _kinds(findings)
    assert findings[0].line == 2  # names the line, not the value


def test_credential_shape_flagged_in_a_record() -> None:
    scanner = build_record_scanner()
    assert "AWS access key" in _kinds(scanner.scan_text("journal/x.txt", f"key: {FAKE_AWS_KEY}\n"))
    assert "AI API key" in _kinds(scanner.scan_text("journal/y.txt", f"token {FAKE_AI_KEY}\n"))


def test_clean_text_passes() -> None:
    scanner = build_record_scanner()
    clean = "NIFTY closed at 22100.25 with OI 1234567 and PCR 0.98 on 2026-10-12.\n"
    assert scanner.scan_text("journal/clean.md", clean) == []


def test_allowed_channel_id_passes_but_other_slack_id_flagged() -> None:
    scanner = build_record_scanner()
    assert scanner.scan_text("journal/a.md", "posted to C0C89E8QCCD\n") == []  # #fno-desk is allow-listed
    other = scanner.scan_text("journal/b.md", "posted to C9ABCDEFGHZ\n")
    assert "Slack user, workspace or channel ID" in _kinds(other)


def test_broker_field_and_email_flagged() -> None:
    scanner = build_record_scanner()
    findings = scanner.scan_text("journal/trade.json", '{"client_code": "AB1234", "note": "x"}\n')
    assert "broker order or account field" in _kinds(findings)
    assert "e-mail address" in _kinds(scanner.scan_text("journal/c.md", "write to someone@example.org please\n"))


def test_code_file_scanned_only_for_credential_shapes() -> None:
    scanner = build_record_scanner()
    # In a code file, a secret-name assignment is legitimate (the scan's own examples live in code) and is NOT flagged,
    # but a real credential shape still is.
    as_code = scanner.scan_text("fno/example.py", f"{SECRET_ASSIGNMENT}\n", is_code=True)
    assert as_code == []
    assert "AWS access key" in _kinds(scanner.scan_text("fno/example.py", f"x = '{FAKE_AWS_KEY}'\n", is_code=True))


def test_null_byte_text_is_unscannable() -> None:
    scanner = build_record_scanner()
    findings = scanner.scan_text("journal/blob.bin", "abc\x00def")
    assert findings and findings[0].line == 0


def test_finding_str_has_no_value() -> None:
    finding = Finding("journal/x.md", 3, "e-mail address")
    assert str(finding) == "journal/x.md:3: e-mail address"


@pytest.mark.parametrize("text", ["", "just words and numbers 42\n", "https://nseindia.com/path\n"])
def test_varied_clean_texts_pass(text: str) -> None:
    assert build_record_scanner().scan_text("journal/z.md", text) == []
