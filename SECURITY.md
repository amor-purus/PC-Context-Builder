# Security and data handling

## Application behavior

AI PC Intelligence is designed for local, read-only inventory collection. It does not upload scan data, read user document contents, or modify source files/registry/settings. It emits metadata and system inventory only after user review and explicit confirmation.

## Sensitive output warning

Generated AI_PC_Knowledge_Pack_*.zip files may contain hardware model identifiers, operating-system details, software inventory (if selected), and other machine metadata. These exports are intentionally excluded from version control. Review output contents before sharing with any service.

## Reporting vulnerabilities

Do not attach real PC exports, private keys, credentials, tokens, or unredacted personal paths to public issues. Report the affected version, a sanitized traceback, and a minimal reproduction.
