"""Canonical application metadata shared by the GUI and Windows launchers."""

from pathlib import Path

# APP_NAME.txt is the single source of truth readable by both Python and CMD.
APP_NAME = Path(__file__).with_name("APP_NAME.txt").read_text(encoding="utf-8-sig").strip()
if not APP_NAME:
    raise RuntimeError("APP_NAME.txt is empty.")
