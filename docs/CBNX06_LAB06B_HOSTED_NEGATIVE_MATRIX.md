# CB-NX06 LAB06B — Synthetic only: hosted rejection and rollback-replay matrix

LAB06B executes **five** source-pinned negative cases on a disposable hosted
Android API36 emulator. It deliberately operates only in the **private** data
root of `com.sdvsync.cbnx06lab`; it is not Nexus authentication, real browser
pairing, a physical device, or production-game qualification.

The tests independently check: altered staged ZIP bytes cannot be installed;
forged Nexus provenance in a receipt is rejected; wrong archive approval key
cannot write Mods; an interrupted `INSTALLING` intent blocks both install and
rollback until human review; a completed synthetic rollback cannot be replayed
or reinstalled. The previous LAB05 positive UI journeys remain separate.

For independence, the hosted emulator runner clears ONLY the disposable LAB
application data before each named case. It checks that `com.sdvsync` production
is absent and refuses non-API36/non-emulator targets. No physical ADB, real
Nexus network, root permissions, signed release or personal game files are used.

The artifact contains only five pass/fail categories, redacted code-site hints,
exact source SHA, run ID, and LAB/test APK digests. Raw instrumentation is
removed from the runner's temporary directory on exit. A green workflow means
emulator synthetic negative evidence only; **physical** and live Iceraven
readiness remain deferred and **not Nexus**-qualified. This does not grant
release or merge approval.

This milestone extends the deferred LAB06 readiness process without overriding
its separate qualification gates. Run the Python/Rich ZIP's `--offline-test`,
then `--yes` and `--resume-only` to monitor real GitHub workflows.
