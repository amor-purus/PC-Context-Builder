# AI PC Intelligence

AI PC Intelligence is a local-first Windows inventory and knowledge-packaging tool. It collects selected system and storage metadata, provides a review step, and exports a privacy-conscious ZIP for AI-assisted troubleshooting.

## Current release

- Version: `v1.0.7`
- Platform: Windows 11 / Python 3.14 (standard library only)
- Access: local read-only inventory; no file-content collection; no network upload
- Packaging: opt-in software/file/folder metadata; sensitive locations excluded by default

See `README.txt` for the full Chinese user guide, `SECURITY.md` for the security boundary, and `VERIFICATION_STATUS.txt` for tested versus device-verified behavior.

## Quick start

1. Download or clone this repository on Windows.
2. Run `start.bat`.
3. Review the selected collection options before creating a ZIP.

Run `check_tool.bat` for local self-tests.
