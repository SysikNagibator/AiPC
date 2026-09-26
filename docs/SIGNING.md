> **Russian version:** [SIGNING_RU.md](SIGNING_RU.md)

# Code signing and SmartScreen — an honest guide

## Why Windows shows the blue “Windows protected your PC” screen

`aipc.exe` has no **code-signing digital signature** and no **SmartScreen reputation**.
Windows doesn’t know the publisher → it plays it safe. This is normal for new
unsigned programs; it is not a virus.

That screen can be **fully removed only by a code-signing certificate**.
A self-signed certificate **will not help** — SmartScreen does not trust it.

## Certificate options

| Option | Price | Effect |
|--------|-------|--------|
| **EV Code Signing** | ~$300–500/yr | SmartScreen trust **immediately**, no blue screen from the first download |
| **OV Code Signing** (Sectigo/Comodo via resellers) | ~$80–200/yr | Signature present immediately, the blue screen goes away **as downloads accumulate** (reputation) |
| **Certum Open Source** | ~€25/yr | Cheap OV for open-source projects — AiPC qualifies (public repo, MIT). The most sensible starting point |

You will need a PFX file + password. Keep it outside the repository!

## How to sign a release

```bat
set AIPC_CERT=C:\certs\s1steam.pfx
set AIPC_CERT_PASS=your_password
tools\sign.bat
