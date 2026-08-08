# Security Policy

EMUAdvisor is a local research/demo application and is not an official Eastern Mediterranean University service.

## Supported use

The repository is intended for local development, evaluation, and demonstration. It should not be exposed directly to the public Internet without an independent deployment/security review.

## Admin authentication

When `EMU_ADVISOR_PROFILE=production`, `EMU_ADVISOR_ADMIN_TOKEN` is required. Admin credentials must be supplied through request headers. Tokens must not be placed in URLs, query parameters, source files, screenshots, logs, or committed environment files.

The browser diagnostics client stores an explicitly supplied token in `sessionStorage` for the current browser session only and sends it as an `Authorization: Bearer` header.

## Secrets and local artifacts

Do not commit:

- `.env` files or service credentials;
- local Qdrant data;
- generated crawl/index artifacts;
- audit logs or chat histories;
- private university material not already publicly available from official sources.

## Reporting

If you find a security issue, report it privately to the repository owner rather than opening a public issue containing exploit details or secrets.
