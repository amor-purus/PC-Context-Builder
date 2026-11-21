"""Privacy guards for diagnostics and AI context exports.

Only narrowly defined machine-generated diagnostic codes are safe to export.
Unexpected PowerShell exception text and user-controlled volume labels are
never copied into a shareable context ZIP by default.
"""
from __future__ import annotations

import re

_SAFE_REASON = re.compile(
    r"^(?:access_error|metadata_error|timestamp_format_error):\s*"
    r"(?:PermissionError|OSError|OverflowError|ValueError|TypeError|FileNotFoundError)$"
)
_SAFE_CODES = frozenset({
    "synthetic_warning", "selected_drives_unavailable_or_not_fixed",
    "diagnostic_detail_redacted",
})
_CIM = re.compile(r"^CIM_unavailable:\s*(Win32_[A-Za-z0-9_]{1,70})\b")
_FALLBACK = re.compile(
    r"^PowerShell_CIM_unavailable_python_fallback_used:\s*"
    r"(?:RuntimeError|TimeoutError|OSError|PermissionError|ValueError|JSONDecodeError|"
    r"FileNotFoundError|UnicodeError)\b"
)


def scrub_diagnostic(reason: object) -> str:
    """Converts untrusted diagnostic prose into a narrow, privacy-safe code."""
    text = str(reason or "").strip()
    match = _SAFE_REASON.fullmatch(text)
    if match:
        return text.replace(": ", ":")
    if text in _SAFE_CODES:
        return text
    match = _CIM.match(text)
    if match:
        return "CIM_unavailable:" + match.group(1)
    match = _FALLBACK.match(text)
    if match:
        error = text.split(":", 2)[1].strip().split(":", 1)[0]
        return "PowerShell_CIM_unavailable_python_fallback_used:" + error
    return "diagnostic_detail_redacted"


def export_warning_rows(rows: list) -> list[dict]:
    """Keep only drive letter and non-sensitive reason code."""
    clean = []
    for row in rows:
        if not isinstance(row, dict):
            clean.append({"Drive": "unknown", "Reason": "diagnostic_detail_redacted"})
            continue
        drive = str(row.get("Drive", ""))
        if not re.fullmatch(r"[A-Za-z]:", drive) and drive not in {"local", "system"}:
            drive = "unknown"
        clean.append({"Drive": drive, "Reason": scrub_diagnostic(row.get("Reason"))})
    return clean


def export_drive_rows(rows: list) -> list[dict]:
    """User-controlled volume labels are omitted even in the default storage view."""
    out = []
    for row in rows:
        item = dict(row)
        item["VolumeName"] = "[redacted]"
        out.append(item)
    return out


def sanitized_scope(raw: object) -> dict:
    """Stable boolean scope, independent of UI and application version."""
    if not isinstance(raw, dict):
        raw = {}
    return {
        "system": bool(raw.get("system", True)),
        "installed_software": bool(raw.get("installed_software", False)),
        "filesystem_metadata": bool(raw.get("filesystem_metadata", False)),
    }
