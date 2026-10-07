# AiPC Platform Support

Status: **Windows 10/11 full; macOS/Linux — core features work**
(`pip install aipc-sysik` or `npm i -g aipc-sysik`), full control stays Windows-first.
Code seams live in `aipc/platform/`
(`base.py` interfaces, `win32.py` full backend, `posix.py` partial).

## Capability matrix

| Group | Windows | macOS | Linux |
|---|---|---|---|
| Screen capture (`screen_see`, …) | ok (mss) | ok (mss) | ok under X11 |
| Files, terminal, processes | ok | ok | ok |
| Browser via CDP | ok | ok (same Chrome flag) | ok |
| Text clipboard | ok | ok (`pbcopy/pbpaste`) | ok (`xclip`/`xsel`) |
| Mouse & keyboard | ok | blocked: needs Accessibility permission grant | blocked: Wayland compositors ignore synthetic input; X11 works |
| Window mgmt, UIA tree (`ui_snapshot`, `window_*`) | ok (uiautomation) | no (needs AXUIElement port) | no (needs AT-SPI port) |
| Audio loopback | ok (WASAPI) | no (needs ScreenCaptureKit/BlackHole) | no (needs PipeWire monitor) |
| Installer (Program Files/PATH/UAC) | ok | n/a (`pip install`) | n/a (`pip install`) |
| IDE MCP configs | ok | ok (XDG/Library paths) | ok (XDG paths) |
| Self-update | ok (exe + SHA256) | ok (asset + SHA256, manual install) | ok (asset + SHA256, manual install) |

## Rules

- New platform-dependent code goes behind `aipc/platform/base.py` + two
  backends — not as inline `if os.name` in tool modules.
- `require(group)` gate returns clean `not_supported` instead of tracebacks.
- The platform badge in README changes only when a platform really works
  (matrix row mostly `ok`, CI green on that OS).

## Known hard limits

- **Wayland**: synthetic mouse/keyboard is rejected by design. Options: X11
  session, `ydotool` daemon (root), or compositor-specific APIs. Not planned.
- **macOS**: Accessibility + Screen Recording permissions are per-app prompts;
  unsigned exe triggers repeated dialogs. Signed build first (see SIGNING.md).
