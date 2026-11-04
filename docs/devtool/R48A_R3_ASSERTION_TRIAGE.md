# R48A R3 — Real-activity test correction and bounded failure checkpoints

## Verified CI inputs

- PR #54, branch `feature/r48a-real-activity-acceptance`, base commit
  `a9cd5a6eefdea176ba9c2f6bba57ff635ad575c3`.
- GitHub run `41861809689`: R40/source and debug APK build passed; AVD booted
  after R2 disk preflight; real Activity instrumentation 2/4 passed.
- Failed: `realOfflineFiveTabNavigationAndPrivatePreviews` and
  `realOperationCenterReadOnlyReturn`. No raw assertion stack traces or
  test-stage data were retained, so their precise failing assertions were
  unproven. Do not claim the application was functionally broken or qualified.

## R3 changes

- The old tab test always expected `Your saves` and `Managing mods` guide text.
  The actual Dashboard and ModManager source renders those guides only in
  populated list branches; a fresh offline CI emulator can instead show
  loading, no-saves/no-mods, or controlled error states. The corrected test
  validates one actual, allowlisted state and preserves primary tab semantics,
  re-entry and the five real UI screenshot requirements.
- The Operation Center test retains title, read-only guidance, back and Home
  tab requirements. It waits for the transition to complete instead of
  presuming immediate composition.
- Both tests emit only predefined text checkpoints to isolated debug app-private
  storage. On failure the collector reads the exact allowlisted checkpoint
  filename and emits only a fixed allowed step value. Unknown/non-ASCII or
  oversized data is replaced with `not_recorded`; no raw logs or paths uploaded.
- No production app code, signing, root, Steam, update gate or file sync changes.

## Acceptance remains gated

The hosted API36 emulator must pass all four actual Activity tests and produce
all five independently verified real UI PNGs with intact APK provenance. The
host-only R48 gate, R47 gate, R43C denial, policy false flags, APK identity and
non-device/non-release receipt remain required. Merge only after verified CI.
Physical-device TalkBack, real account, game updates and publication remain out
of scope.
