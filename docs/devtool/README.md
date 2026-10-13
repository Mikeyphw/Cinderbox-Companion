# Cinderbox Companion — Devtool

This repository declares a first-class **Android application** target named
`cinderbox` for Devtool. The default build is **debug-only**. No release
keystore, Steam credential, root privilege, device installation, or publishing
permission is granted by this configuration.

## Commands (Termux or desktop Linux)

```sh
cd ~/Code/Cinderbox-Companion
./devtoolw security              # offline source-contract regression
./devtoolw quick                 # security + Android JVM tests
./devtoolw build                 # security + assembleDebug + structural APK check
./devtoolw lint                  # Android Lint for Debug
./devtoolw validate              # Android-aware validation; lint/test/debug APK
./devtoolw full                  # ordered security + test + lint + debug APK workflow
./devtoolw format-check          # ktlintCheck, never formatting source
./devtoolw device                # explicitly requested connected-device tests
```

For direct Devtool commands, the equivalent is `devtool --repo "$PWD"
--target cinderbox build`. Inspect the execution plan with `devtool --repo
"$PWD" --target cinderbox plan` and configure with `devtool --repo "$PWD"
--target cinderbox doctor` (the latter may inspect local SDK/toolchains).

`./devtoolw` automatically finds the installed `devtool` executable and
preserves the current checkout's repository root. It does not install Devtool.

## Android build authority

- Gradle wrapper 8.11.1, AGP 8.10.1, Kotlin 2.1.0, JDK 17, compileSdk 35.
- `:app:testDebugUnitTest`, `:app:lintDebug`, `:app:assembleDebug` are real
  tasks in the checked-in project. No imaginary combined Gradle task or
  release-signing configuration is introduced.
- Native Termux is preferred (`prefer_native_termux = true`). Devtool auto
  selects its ARM64 SDK/build-tools providers. Use `devtool --chroot androidos
  --repo "$PWD" --target cinderbox build` if native toolchains are unavailable.
  Provider/bootstrap downloads follow your trusted global Devtool policy.
- Limit Gradle to 2 workers; reuse the build cache and daemon; use bounded
  JVM heap/metaspace for low-RAM phones; keep conservative free-disk cleanup.
- A build's APK is not a signed release. Publishing and app installation are
  separate, explicit operations.
- Device instrumentation is **disabled by default** and only runs through
  `./devtoolw device` with an authorized device attached.

## Workflows

| Workflow | Contract |
| --- | --- |
| `security` | Python standard library static checks; no Gradle or Android needed |
| `quick` | Security gate then JVM unit tests |
| `full` | Security, unit tests, lint, and debug APK, in order |
| `format-check` | Kotlin formatting check, no automatic formatting |
| `device` | On-device connected Android tests, explicit only |

The native `validate` command uses Devtool's Android validation phases and
persistent evidence/rollback behavior. It is deliberately not synonymous
with a release gate. The `build` / `full` wrappers additionally check the
actual APK ZIP structure and report its SHA-256. Review the reported task results before sharing APKs.

**Security note:** static contract checks only catch selected regressions in
M0/M1. The Gradle suite and Android Lint are separate mandatory signals for a
qualified debug build; no statement of APK safety follows from this check alone.
