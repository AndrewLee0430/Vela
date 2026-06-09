# -*- coding: utf-8 -*-
"""PHI sanitizer — Taiwan-mobile coverage (R5, lawyer-raised P0).

TAIWAN_PHONE_PATTERN is the SHARED constant used by both
PHIDetector.detect()/_check_phi (the input gate that BLOCKS) and
PHIDetector.sanitize_for_log() (the storage MASK). Extended 2026-06-09 from the
contiguous-only `\\b09\\d{8}\\b` to also cover dashed / spaced / +886 forms.

POSITIVE: every TW-mobile format is masked AND detected.
NEGATIVE (over-masking guard — the decisive check): clinical content — lab values,
dosages, dates — is left UNTOUCHED by the mask AND NOT flagged by the gate.

Run: python tests/test_phi_taiwan_phone.py   (or via pytest)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.middleware.phi_handler import PHIDetector  # noqa: E402

# Every TW-mobile format the extended pattern must cover.
TW_MOBILE_FORMATS = [
    "0912345678",
    "0912-345-678",
    "0912 345 678",
    "+886-912-345-678",
    "+886 912 345 678",
    "+886912345678",
    "886-912-345-678",
]

# Clinical content that must NOT be masked or flagged (the over-masking guard).
CLINICAL_SAFE = [
    "K 6.8",
    "Na 128",
    "Glucose 250 mg/dL",
    "WBC 9.2",
    "2024-09-12",          # ISO date — '-' separated, but not the 09xx phone shape
    "09/12/2024",          # slash date — '/' is deliberately NOT a phone separator
    "Sample 0912 collected today",  # bare 4-digit value, not a 10-digit phone
]


def test_tw_mobile_formats_are_masked():
    for s in TW_MOBILE_FORMATS:
        out = PHIDetector.sanitize_for_log(s)
        assert "***" in out and s not in out, f"NOT masked: {s!r} -> {out!r}"


def test_tw_mobile_formats_are_detected():
    for s in TW_MOBILE_FORMATS:
        assert PHIDetector.detect(s) is not None, f"NOT detected by gate: {s!r}"


def test_clinical_content_not_masked():
    for s in CLINICAL_SAFE:
        out = PHIDetector.sanitize_for_log(s)
        assert out == s, f"OVER-MASKED clinical content: {s!r} -> {out!r}"


def test_clinical_content_not_detected():
    for s in CLINICAL_SAFE:
        assert PHIDetector.detect(s) is None, f"FALSE BLOCK on clinical content: {s!r}"


def test_mixed_string_masks_only_the_phone():
    mixed = "Call 0912-345-678 re: K 6.8 on 2024-09-12"
    out = PHIDetector.sanitize_for_log(mixed)
    assert "0912-345-678" not in out, "phone not masked in mixed string"
    assert "K 6.8" in out and "2024-09-12" in out, "clinical content lost in mixed string"


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS  {name}")
            except AssertionError as e:
                failures += 1
                print(f"FAIL  {name}: {e}")
    print(f"\n{'ALL PASS' if failures == 0 else f'{failures} FAILED'}")
    sys.exit(1 if failures else 0)
