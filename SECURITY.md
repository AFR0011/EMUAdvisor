# Security Policy

EMUAdvisor is a local research/demo application and is not an official Eastern Mediterranean University service.

## Supported use

The repository is intended for local development, evaluation, and demonstration. It should not be exposed directly to the public Internet without an independent deployment/security review, service hardening, and validation of the target Qdrant/runtime environment.

## Admin authentication

When `EMU_ADVISOR_PROFILE=production`, `EMU_ADVISOR_ADMIN_TOKEN` is required for protected diagnostic/data APIs. Admin credentials must be supplied through request headers.

The static `/admin` application shell remains reachable so a user can enter the credential locally; loading that HTML does not grant access to protected metrics, retrieval diagnostics, analytics, corpus status, or `/ask` responses.

Tokens must **not** be placed in URLs, query parameters, source files, screenshots, logs, or committed environment files. Query parameters are not an authentication mechanism.

The browser diagnostics client accepts a token through an explicit password-style field, stores it in `sessionStorage` for the current browser tab only, and sends it as an `Authorization: Bearer` header. Clearing or closing the tab removes that browser-session credential.

## Secrets and local artifacts

Do not commit:

- `.env` files or service credentials;
- local Qdrant data;
- generated crawl/index artifacts;
- audit logs or chat histories;
- human-review working files containing information not intended for publication;
- private university material not already publicly available from official sources.

## Dependency security

`requirements-lock.txt` is the pinned Python environment used by CI. CI installs that snapshot and runs `pip-audit` before the test/evaluation stages. Dependency updates should regenerate the lock file and rerun the complete core and browser verification jobs.

## Publication safeguards

`tools/publication_guard.py` enforces key release invariants, including verified-gold metadata, required publication files, and the absence of URL-based admin-token examples in the public tree.

## Reporting

If you find a security issue, report it privately to the repository owner rather than opening a public issue containing exploit details, credentials, or sensitive data.
