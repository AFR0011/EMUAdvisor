# Dependency Policy

Workflow schema: `agentic-workflow/v2`

- `requirements.txt` and `requirements-dev.txt` express direct compatible ranges.
- `requirements-lock.txt` is the exact CI/demo snapshot and must install on every declared platform.
- Platform-specific packages require environment markers; Linux-only `uvloop` must not block Windows.
- Use Python 3.12 for the current verification baseline and test both Ubuntu and Windows in CI.
- Regenerate the lock deliberately; do not bulk-upgrade majors during an unrelated batch.
- Run `python -m pip check` and a dependency audit after installation.
- Record the generator command, Python/platform inputs, and audit tool version before release.
- Optional model/Qdrant/CUDA dependencies must remain explicit and may not be implied by core CI.

## Lock maintenance

Resolve from `requirements-dev.txt` in a clean Python 3.12 environment, capture the resolved set with
`python -m pip freeze`, then review platform-specific packages before replacing the lock. Preserve
`uvloop; sys_platform != "win32"`, install the candidate lock on both Windows and Ubuntu, run
`python -m pip check`, and run the separately pinned `pip-audit==2.10.1`. Record the Python, pip,
platform, direct-input hashes, and resulting lock hash. A freeze from one platform is not accepted
until the other declared platform installs and tests it successfully.
