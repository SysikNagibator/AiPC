# aipc-sysik (npm)

AiPC by SYSIK — local MCP server + terminal menu: gives Claude and other
AI assistants eyes and hands on your PC. This npm package is a thin wrapper:
on install it downloads the prebuilt binary for your OS from
[Releases](https://github.com/SysikNagibator/AiPC/releases) and exposes
the `aipc` command.

[Русская версия](README-RU.md)

```sh
npm i -g aipc-sysik
aipc            # menu (first run sets everything up itself)
aipc mcp        # MCP command for your IDE
```

Full documentation (EN/RU), risks and platform matrix — in the
[main repository](https://github.com/SysikNagibator/AiPC#readme).

## How it works

`postinstall` (`install.js`) detects `process.platform`/`process.arch`,
downloads the matching `v1.1.1` release file (`AiPC_Win_*.exe`, `AiPC_macOS_*`,
`AiPC_Linux_*`) into `bin/` and makes it executable. The `bin/aipc.js` shim
passes arguments through to the binary one-to-one.

> Newer npm versions (11+) may block postinstall scripts — no problem:
> the shim downloads the binary itself on first `aipc` run.

Supported: Windows x64, macOS ARM64, Linux x64. Everyone else —
`pip install aipc-sysik` or a binary from Releases. Offline install:
`AIPC_SYSIK_SKIP_DOWNLOAD=1`.

## Versions

The npm package version tracks AiPC releases (`1.1.3` = release `v1.1.1`).
The OS → file map lives in `platforms.js` and is updated with each release.

## GitHub Packages mirror

The primary registry is npmjs (`npm i -g aipc-sysik`, no login needed).
Additionally, every release tag is published to GitHub Packages as
`@sysiknagibator/aipc-sysik` (workflow `gh-packages.yml`; GitHub itself
requires the scoped name). Installing from there requires authentication:

```sh
# ~/.npmrc:
@sysiknagibator:registry=https://npm.pkg.github.com/
//npm.pkg.github.com/:_authToken=YOUR_PAT_WITH_READ_PACKAGES
npm i -g @sysiknagibator/aipc-sysik
```

License: MIT. Author — SYSIK.
