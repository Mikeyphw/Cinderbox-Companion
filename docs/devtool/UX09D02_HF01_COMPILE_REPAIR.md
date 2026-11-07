# UX09D02 HF01 — single-source Kotlin compile repair

Source lock: PR #77 HEAD `8f29743fb512c0c7518cc43aa1003a5124b3d028`; exact tree `5f7df681c86ae0e6101cec8d81449b4fce1b924a`;
`Ux09D02RealRouteEvidenceTest.kt` Git blob `629d06a8450ea01f815d97716bd8962d406649ed`.

The hosted GitHub Actions `:app:compileDebugAndroidTestKotlin` build failed with
`Unresolved reference 'assertDoesNotExist'` at line 6 of the new test. Compose's
`onNodeWithText(...).assertDoesNotExist()` is an instance API, not a top-level import.
Removing only the invalid import makes the test source type-check beyond that
known error. Hosted compilation and runtime testing are **not yet confirmed** by
this source-only hotfix.

Preserved exactly: every production file, approved dark UI references, default
font size, navigation routes, Steam/Nexus safety boundaries, root/Shizuku access
controls, cloud/update/install/release gates, and all prior hosted receipts.

After installation, inspect PR #77's hosted UX09D02 run: require four actual
navigation tests at both emulator widths, ten CRC-validated PNG files, source-
bound receipts, and no native-golden or physical-device approval claims.
