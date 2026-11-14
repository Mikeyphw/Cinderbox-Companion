# CB-NX06 LAB02B — Full-app transitive safety hardening and read-only identity probe

This is the **real `:app:assembleCbnxLab` variant**, not a standalone harness.
Parent source pin: `db79fcf070ff5bb35914deaa02675041d872d02a` (PR #89).

## Hardening

- Lab mode explicitly refuses Steam transport connection in `SteamClientManager.connect()` and the lower-level `startConnection()` boundary, plus credential, QR and saved-session login/reconnect paths in `SteamAuthenticator`. Production Steam flows are unchanged.
- Lab settings do not show root confirmation, Shizuku binding, SAF tree chooser, All Files Access or broad-storage prompts. The lab manifest continues to omit privileged permissions and the lab app cannot intercept NXM links.
- Lab mode visibly displays `CINDERBOX LAB - PRIVATE GAME DATA` in the full Cinderbox UI. It stores synthetic Mods, Saves and GameFiles in the private lab root, not the real game root.
- Hosted LAB02B source and negative tests are mandatory **before** Gradle and are separate from the inherited CB-NX06 source and signer gates.

## Inspection-only ADB receipt

After a new hosted artifact is available, download `cbnx06-full-cinderbox-lab-apk` and verify its `SHA256SUMS` before any device testing. The following script is read-only and **does not install** an APK:

```sh
python3 scripts/devtool/cbnx06_lab02b_device_probe.py \
 --serial localhost:5555 \
 --apk /storage/emulated/0/Download/CBNX06-LAB/app-cbnxlab-debug.apk \
 --attestation /storage/emulated/0/Download/CBNX06-LAB/LAB_ARTIFACT_ATTESTATION.json \
 --ack I_AUTHORIZE_READ_ONLY_DEVICE_PROBE
```

This merely inspects Android API/ABI, package APK bytes and production APK byte stability during the probe. Without a separately installed lab APK it reports **inspection-only, not qualified**. No `adb install`, `su`, game file read/write, rollback or network operation is performed.

A matching APK is **not** proof that Mods/Saves remained unchanged, that a Nexus file was genuinely authorized or downloaded, that rollback works, or that browser integration is qualified. LAB02C isolated browser extension and LAB03/04 synthetic operations are still pending. All live operations remain forbidden until corresponding evidence and approval exist. No auto-merge or release signing.
