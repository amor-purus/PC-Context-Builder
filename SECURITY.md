# Security and data handling

## Application behavior

PC Context Builder is designed for local, read-only Windows PC context collection. It does not upload scan data, read user document contents, or modify source files/registry/settings. It emits metadata and system inventory only after user review and explicit confirmation.

## Sensitive output warning

Generated PC_Context_Pack_*.zip files may contain hardware model identifiers, operating-system details, software inventory (if selected), and other machine metadata. These exports are intentionally excluded from version control. Legacy AI_PC_Knowledge_Pack_*.zip exports are also ignored for backward compatibility. Review output contents before sharing with any service.

## Metadata and CSV handling

CSV text fields originating from file names, paths, registry metadata, and scan messages are neutralized when they begin with spreadsheet formula-triggering characters (including after leading whitespace/control characters). This reduces CSV formula-injection risk in common spreadsheet applications; it is not a universal guarantee. Review exported data before opening or sharing it.

Sensitive-directory filtering matches complete path components, including configured multi-component paths such as `.config/gcloud`. Common cloud-sync directory names and Windows sync-root environment variables are also excluded. Detection is heuristic: custom sync roots not exposed through a recognized environment variable or name may not be detected.

## Reporting vulnerabilities

Do not attach real PC exports, private keys, credentials, tokens, or unredacted personal paths to public issues. Report the affected version, a sanitized traceback, and a minimal reproduction.
