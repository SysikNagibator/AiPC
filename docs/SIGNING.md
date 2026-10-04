# Signing and SmartScreen — An Honest Guide

## Why Windows shows the blue screen “Windows Defender protected your PC”

`AiPC_Win_1.0.5.1.exe` has no **code-signing digital signature** and no **SmartScreen reputation**.
Windows does not know the publisher → it errs on the side of caution. This is normal for new
unsigned programs; it is not a virus.

This screen can be completely removed only by a **code-signing certificate**.
A self-signed certificate **will not help** — SmartScreen does not trust it.

## Certificate options

| Option | Price | Effect |
|---------|------|--------|
| **EV Code Signing** | ~$300–500/year | SmartScreen trust **immediately**; no blue screen from the very first download |
| **OV Code Signing** (Sectigo/Comodo through resellers) | ~$80–200/year | The signature is there immediately; the blue screen disappears **as downloads accumulate** (reputation) |
| **Certum Open Source** | ~€25/year | Cheap OV for open-source projects — AiPC qualifies (public repository, MIT). The most sensible start |

You will need a PFX file + password. Store it outside the repository!

## How to sign a release

```bat
set AIPC_CERT=C:\certs\sysik.pfx
set AIPC_CERT_PASS=your_password
tools\sign.bat
```
The script will sign `dist\AiPC_Win_1.0.5.1.exe` (and `AiPC-Setup.exe`) via `signtool`
with a DigiCert timestamp and verify the signature. You need the Windows SDK installed
(that is where `signtool` lives).

## Free steps (do them in any case)

1. **Submit the file to Microsoft for review:**
   https://www.microsoft.com/en-us/wdsi/filesubmission —
   select “Software Developer”, attach `AiPC_Win_1.0.5.1.exe`. This removes
   false Defender detections and speeds up SmartScreen reputation accumulation.
2. **Do not change the file name** between releases (`AiPC_Win_1.0.5.1.exe`) — reputation
   is tied to the name + signature.
3. **Accumulate downloads** — SmartScreen learns: the more people
   run the file and click “Run anyway”, the faster the
   warning disappears on its own.
4. The exe already has an icon and version info embedded (publisher SYSIK in the
   “Details” tab of the file properties) — this also helps trust.

## After purchasing a certificate

1. Sign the exe via `tools\sign.bat`.
2. Release a new version (for example, v1.0.2) with the signed file.
3. EV will give a clean launch immediately; OV — a clean launch after reputation accumulates.
