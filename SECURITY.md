# Security and personal data boundaries

PC Context Builder runs locally on Windows. It does not upload collected information
or read user document contents. The plaintext ZIP is **not encrypted**, and
its machine metadata can still be sensitive.

## Before data is collected

- System hardware and storage statistics are enabled by default.
- Installed software and filesystem metadata are **not collected** unless the
  user opts in before scanning. Review/export approval is a separate stage.
- Credentials, cloud-sync folders, reparse points, hidden/system files and
  sensitive-name candidates are filtered heuristically, not perfectly.

## Before a ZIP is published

- Default storage exports redact all volume labels as `[redacted]`.
- Raw PowerShell error strings are not exported: diagnostic descriptions are
  mapped to bounded codes, and unexpected text is replaced with
  `diagnostic_detail_redacted`.
- AI README text is fixed, not constructed from attacker-controllable
  device/software/file strings. Treat all JSON/CSV fields as **untrusted data**.
- A strict member allowlist, CRC read-back and scope/selection cross-check run
  before an archive receives its final public filename.
- Source files are not modified. ZIP creation uses local temporary files
  that may themselves contain sensitive metadata while a task is active.
- A prior interrupted stage can be removed only on explicit consent and after
  checking journal and temporary-file identity. Uncertain residuals are kept.

## Known limits

No system can guarantee against malicious software with the current user's
permissions, unknown cloud sync configurations, an adversary able to modify
source data, all forms of filename-based prompt injection, malicious hardware,
storage corruption, or complete power-loss atomicity. The program does not
authenticate provenance of metadata values.

Without full end-user GUI acceptance testing, GitHub-hosted CI proves only
the automated tests actually executed. The released EXE is unsigned;
verify its origin and SHA-256 before running.

## Vulnerability reports

Never attach real PC exports, private keys, API tokens, full stack traces
with unredacted paths, or screenshots containing personal information to
public issues. Report the affected version, a synthetic minimal reproduction
and an appropriately sanitized error category.

For the stable data schema and AI trust boundary see [SCHEMA_V2.md](docs/SCHEMA_V2.md).
