# M3G: existing Devtool GitHub Actions integration

The supplied Devtool snapshot includes ACTIONS-05 plan, run, watch, artifacts, and Android collect. Cinderbox master already has `.github/workflows/devtool-android-build.yml` (Git blob `31166d27e70a1f409ef09e4c653bd1edd99d277e`) and its standard `build.yml` PR CI. M3G **extends** both with `test_m3g_*.py`; it does not replace the release or signing gates.

The existing Devtool workflow implements `workflow_dispatch` parameters `project_dir`, `module`, `variant`, `format`, uses Java 17 and Android 35, and publishes the `devtool-android-debug-apk` artifact along with source evidence. It is debug-only. Never configure release signing on a feature branch.

After applying the source-bound overlay, commit and push feature branch `feature/m3g-steam-reliability-observability`:

```sh
cd ~/Code/Cinderbox-Companion
sh scripts/devtool/m3g_devtool_ci.sh plan
sh scripts/devtool/m3g_devtool_ci.sh run
# Use exact run_id from dispatch receipt; do not redispatch uncertain or 204 responses.
sh scripts/devtool/m3g_devtool_ci.sh watch RUN_ID
sh scripts/devtool/m3g_devtool_ci.sh artifacts RUN_ID
sh scripts/devtool/m3g_devtool_ci.sh collect RUN_ID ARTIFACT_ID
```

Devtool validates the exact local pushed SHA before dispatch; actual run SHA and artifact metadata are checked separately. APK collect requires local Android `apksigner` and `aapt`/`aapt2`, stores verified APK under `.devtool/artifacts/android-verified`, still `qualified_release=false` and **never installs**. A debug APK may not share the installed release certificate. The existing manually approved `cinderbox-signed-candidate.yml` workflow remains a separate release candidate lane after merge. No credentials/signing keys needed in this overlay. Do not use an unknown local APK to update an installed signed app without certificate preflight.
