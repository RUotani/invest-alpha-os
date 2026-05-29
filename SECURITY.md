# Security Policy

## Supported versions

Security fixes apply to the default branch only.

## Reporting a vulnerability

Do not open public issues for sensitive reports.

Contact the repository owner privately with:

- affected component
- reproduction steps (redacted)
- impact assessment

Do not include secrets, broker files, or account data in reports.

## Safe development

- Never commit `.env`, credentials, tokens, or broker/manual data files.
- Generated reports belong in `invest-alpha-os-reports-private`, not this repository.
- Use `security-leakage-audit` and `security-dashboard` CLI commands before publishing artifacts.
