# Security and Privacy

EMUAdvisor is designed for local use and is not approved for public Internet deployment.

## Session isolation

Public chat creation returns a server-issued opaque session ID and a separate high-entropy capability. The browser keeps both in same-tab `sessionStorage` and sends the capability only in the `X-EMU-Session-Capability` header. Continuation, transcript read, export, and clear require the matching capability. The server stores only its SHA-256 hash. Public session enumeration is unavailable; administrative enumeration requires a configured admin token and omits message text.

This is capability-based local isolation, not full user authentication. Anyone who can read the browser tab or steal the capability can act on that session.

## Data minimization defaults

- Transcript persistence: off unless `EMU_ADVISOR_ENABLE_CHAT_PERSISTENCE=1`.
- Audit logging: off unless `EMU_ADVISOR_ENABLE_AUDIT_LOGGING=1`.
- Raw questions in audit records: off unless `EMU_ADVISOR_LOG_RAW_QUERY=1`.

When persistence is enabled, plaintext transcript content is written to the configured local path with bounded message count and TTL pruning; capability cleartext is never stored. Protect the OS account and file permissions. Existing legacy local transcript/log files are not loaded under default settings and require an explicit owner-led cleanup/migration decision.

## Source and runtime controls

Official ingestion is restricted to HTTPS on exactly `mevzuat.emu.edu.tr`, without credentials or nonstandard ports. Each redirect target is validated before request and the final response URL is revalidated. Local files are accepted only through explicit fixture ingestion and retain non-official fixture provenance.

Fixture corpus mode is limited to development/test and visibly labeled. Artifact mode requires a valid nonempty corpus. Production refuses fixture mode, requires an admin token, and retains the documented Qdrant requirement.

## Reporting

Do not place secrets, private transcript content, corpus data, or security-sensitive reproduction material in a public issue. Use the repository owner’s private contact channel.
