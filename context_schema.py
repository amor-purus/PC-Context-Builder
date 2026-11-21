"""Stable schema and content allowlist for shareable PC Context Packs.

All variable machine/software/filesystem strings are UNTRUSTED DATA, never
instructions. Inspect the complete ZIP before it receives its final name.
"""
from __future__ import annotations

import csv
import io
import json
import zipfile

SCHEMA_VERSION = "2.0"
ROOT = "PC_Context_Pack/"
MANDATORY = {
    ROOT + "00_README_FOR_AI.md",
    ROOT + "06_SCAN_REPORT/scan_report.json",
    ROOT + "06_SCAN_REPORT/manifest.json",
}
CATEGORIES = {
    "system": ROOT + "01_PC_PROFILE/system_profile.json",
    "software": ROOT + "02_SOFTWARE/installed_software.csv",
    "drives": ROOT + "03_STORAGE/volumes.csv",
    "folders": ROOT + "04_FILE_INDEX/folders.csv",
    "files": ROOT + "04_FILE_INDEX/files.csv",
    "warnings": ROOT + "06_SCAN_REPORT/warnings.csv",
    "security": ROOT + "05_SECURITY/excluded_items_summary.csv",
}


def expected_members(selected: dict) -> set[str]:
    return MANDATORY | {path for key, path in CATEGORIES.items() if bool(selected.get(key))}


def verify_archive(path: str, selected: dict) -> None:
    """Fail-closed content check performed before final ZIP publication."""
    with zipfile.ZipFile(path, "r") as archive:
        items = archive.namelist()
        if len(items) != len(set(items)):
            raise ValueError("ZIP contains duplicate members")
        expected = expected_members(selected)
        if set(items) != expected:
            raise ValueError("ZIP export does not match approved category allowlist")
        for info in archive.infolist():
            if info.is_dir() or info.filename.startswith("/") or "\\" in info.filename:
                raise ValueError("ZIP entry is outside approved relative paths")
            if info.file_size > 100 * 1024 * 1024:
                raise ValueError("Unexpectedly large context member")
        damaged = archive.testzip()
        if damaged:
            raise ValueError("ZIP CRC validation failed")
        manifest = json.loads(archive.read(ROOT + "06_SCAN_REPORT/manifest.json"))
        if manifest.get("schema_version") != SCHEMA_VERSION:
            raise ValueError("Context-pack schema version mismatch")
        if manifest.get("selected_categories") != {
            name: bool(selected.get(name)) for name in CATEGORIES
        }:
            raise ValueError("Manifest selection mismatches user approval")
        scope = manifest.get("collection_scope", {})
        if not isinstance(scope, dict):
            raise ValueError("Missing collection scope")
        if manifest.get("data_trust") != "untrusted_machine_metadata":
            raise ValueError("Missing explicit untrusted-data marker")
        record_counts = manifest.get("record_counts")
        if not isinstance(record_counts, dict):
            raise ValueError("Missing record count manifest")
        for category, member in CATEGORIES.items():
            if not selected.get(category):
                continue
            if category == "system":
                if record_counts.get(category) != 1:
                    raise ValueError("System profile count mismatch")
                continue
            with io.StringIO(archive.read(member).decode("utf-8-sig"), newline="") as fp:
                rows = list(csv.DictReader(fp))
            actual = (
                sum(int(row.get("Count", 0)) for row in rows)
                if category == "security" else len(rows)
            )
            if record_counts.get(category) != actual:
                raise ValueError(f"Incorrect exported record count for {category}")
        if not bool(scope.get("filesystem_metadata", False)) and (
            selected.get("files") or selected.get("folders")
        ):
            raise ValueError("Unexpected file metadata exported without collection consent")
        if not bool(scope.get("installed_software", False)) and selected.get("software"):
            raise ValueError("Unexpected software exported without collection consent")
        if selected.get("system"):
            system = json.loads(archive.read(CATEGORIES["system"]))
            if not selected.get("software") and (
                "software" in system or "browser_summary" in system
            ):
                raise ValueError("Opted-out software data leaked into system profile")
            if not selected.get("drives") and "drives" in system:
                raise ValueError("Opted-out storage data leaked into system profile")
            if selected.get("drives") and any(
                d.get("VolumeName") != "[redacted]" for d in system.get("drives", [])
            ):
                raise ValueError("Unredacted volume label in system profile")
        readme = archive.read(ROOT + "00_README_FOR_AI.md").decode("utf-8")
        if "UNTRUSTED DATA" not in readme:
            raise ValueError("Missing explicit AI untrusted-data boundary")
