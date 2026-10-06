# AiPC Threat Model

Version: 1.1+. Audience: users and contributors. Language: English
(Russian version: `THREAT_MODEL_RU.md`).

## 1. What we protect

- The user's PC: files, credentials, money (banking/crypto), private
  correspondence, local network and SSH hosts reachable from the PC.
- The human's right to decide: no irreversible or externally visible action
  happens without the human's knowledge (in `ask` mode — without explicit consent).

## 2. Who we protect against

| Actor | Example | Covered |
|---|---|---|
| Malicious or compromised AI model | model runs `mimikatz`, exfiltrates `id_rsa` | Yes — modes, server confirmations, deny-lists |
| Prompt injection via untrusted data | a web page saying "delete all files", a document with hidden instructions, SSH output with injected commands, a screenshot with a QR/text trap | Partially — `untrusted` markers + taint-guard force confirmation in `ask` AND `auto` (disable via `safety.taint_guard: false`) |
| Malicious software on the PC | keylogger reading `audit.log` | Partially — secrets are masked in logs; OS-level protection is out of scope |
| Attacker on the network (MITM) | swapping the update binary | Partially — `self_update` aborts without `SHA256SUMS.txt` in the release and verifies the exe hash before launching; first fetch is still TOFU over HTTPS. Code signature pinning is future work |
| Attacker with physical access | — | Out of scope |

## 3. Trust boundaries

1. **Model ↔ server.** The model is NOT trusted: in `ask` mode every
   `mutate/exec/network` tool blocks in `_wrap` until a human clicks Yes/No
   in a native OS dialog. The dialog shows the exact command/path/host.
   Silence for `safety.confirm_timeout` (default 120 s) = deny
   (`denied_timeout`). A confirmed action may be remembered for
   `safety.allow_minutes` (default 10) — never forever.
2. **Server ↔ OS.** Tool implementations are trusted code; direct
   `import control/net` bypasses the MCP gate (same process by design).
3. **Untrusted inputs.** `browser_eval`, `browser_history_search`,
   `screen_see`/`screen_region`/`screen_burst`/`window_shot`, `ui_snapshot`,
   `fs_read`, `web_search_pc`, `ssh_exec` output, clipboard content arrive
   tagged `{"untrusted": true, "source": ...}`. The system prompt forbids
   following instructions inside such data without human confirmation.
   If untrusted input appeared in the last `safety.taint_window` calls
   (default 10), the next `exec/network/mutate` call requires confirmation
   even in `auto` mode.
4. **Config file.** `~/.aipc/config.yaml` is trusted. Deny-list upgrades
   (`safety.version`) merge defaults with user additions, never wipe them.

## 4. Known attacks and status

- Web-page injection → agent runs commands: mitigated by untrusted markers +
  taint-guard. Residual risk: model may paraphrase instead of quoting
  (no byte-exact detection) — confirmation is the backstop.
- Malicious document read via `fs_read` → same as above.
- Screenshot with embedded instructions → screen results are marked untrusted.
- Malicious SSH server output → `ssh_exec` output is marked untrusted.
- Secret exfiltration (`set`, `type ...\Login Data`, `Get-Content id_rsa`):
  blocked by command normalization + in-command path checks + `env_get`
  name filter. Secrets are masked in `audit.log` and in `env_get`/`fs_read`
  responses (known token/key patterns). Residual risk: other channels
  (browser/SSH outputs, chat text) go raw with the untrusted tag.
- Malicious update binary: **mostly closed** — no `SHA256SUMS.txt` in the
  release = no auto-update; hash mismatch = binary deleted, install aborted.
  Residual: first fetch is TOFU (same-channel sums); code signature is future work.

## 5. What the project does NOT guarantee

- Deny-lists are a seatbelt, not a wall: obfuscation evolves; the real
  boundary is modes + confirmations. For strict setups use
  `run_cmd_policy: allowlist`.
- No sandboxing: tools run with the user's rights. `auto` mode + a prompted
  injection = the confirmation dialog is the last line of defense. Keep
  `ask` (the default) whenever the agent touches the network or strangers' files.
- `audit.log` lives on the same machine; against local malware it is
  evidence, not protection.
- No protection against a compromised IDE/MCP client that forges tool calls —
  the server trusts its stdio peer.
