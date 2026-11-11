# Security Policy

## Reporting

Please report security issues privately to the repository owner rather than opening a public issue containing credentials, logs, hostnames, IP addresses, or other sensitive data.

## Sensitive data handling

- Never commit `settings.json`, API secrets, subscription URLs, proxy credentials, or collected logs.
- Keep External Controller bound to loopback (`127.0.0.1`) unless you have a separate, secured administrative design.
- Review and redact `FlClashLogs/` and `collector-startup.log` before sharing them.
- If an API secret is exposed, rotate it in FlClash and update the local settings file.