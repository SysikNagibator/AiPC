# Contributing to AiPC

## Ground rules

1. **No commits/pushes without maintainer approval** — open a PR, wait for review.
2. **Tests for every behavior change**, especially security ones (including
   negative/bypass tests). Run `python -m pytest tests -q` before pushing.
3. **Config compatibility**: never wipe user additions in `~/.aipc/config.yaml`.
   New keys go through `DEFAULTS` + `safety.version` merges.
4. **No heavy dependencies without justification** (state why in the PR).
5. **Docs in sync**: `README.md` ↔ `README_RU.md`, `SKILL.md` ↔ `SKILL_RU.md`.
   After each change: `python tools/gen_tools_table.py --check`.
6. **CHANGELOG.md** gets an entry per change (`[Unreleased]` section).

## Workflow

```bash
pip install -r requirements.txt
python -m pytest tests -q
python tools/gen_tools_table.py --check
```

## PR checklist

- [ ] Tests added/updated, suite green
- [ ] CHANGELOG updated
- [ ] Docs synced (EN/RU)
- [ ] No secrets in code or logs (see `aipc/audit.py:mask_secrets`)
- [ ] Security behavior changes reviewed against `docs/THREAT_MODEL.md`

Russian version: [CONTRIBUTING_RU.md](CONTRIBUTING_RU.md).
