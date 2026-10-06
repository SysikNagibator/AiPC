# Security Policy

## Supported versions

Only the latest release (`main` branch) receives security fixes.

## Reporting a vulnerability

**Do not open a public issue.** Use GitHub → *Security* → *Report a
vulnerability* (private advisory), or attach your findings to a draft PR
without details in the title.

Include: AiPC version (`aipc --version`), mode (`ask`/`auto`/`read-only`),
tool name and parameters (redact secrets), `audit.log` excerpt, expected
vs actual behavior.

We aim to confirm within 7 days. Please give us a reasonable window to fix
before disclosing publicly (90 days max).

## Scope notes

- `self_update` downloads release binaries checked by MZ-header only (see
  `docs/THREAT_MODEL.md`). Binary-substitution reports are in scope and welcome.
- Prompt-injection *techniques* against the model are a known open problem;
  reports are welcome when they demonstrate a **server-side** bypass
  (missing confirmation, missing `untrusted` tag, log injection).
- `auto` mode executing a confirmed-by-design dangerous action is not
  a vulnerability — that is what `auto` means. Use `ask`.

## Russian version

См. [SECURITY_RU.md](SECURITY_RU.md).
