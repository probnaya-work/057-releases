# 057 releases

Official distribution files for [057](https://057.probnaya.work), a local computational activity instrument.

Download signed and notarized macOS installers from [Releases](https://github.com/probnaya-work/057-releases/releases).
The macOS app verifies updates with Developer ID and Sparkle signatures. CLI / Web is published as
[`@probnaya/057-cli`](https://www.npmjs.com/package/@probnaya/057-cli).

This repository contains distribution files, release notes and checks of published installers.
Application source code is maintained separately. Tags here identify distribution records; each `release.json` records the source
commit and version used to build the actual software. Existing artifact bytes are preserved
when migrated from the previous download host.

Each release provides a DMG, update ZIP, signed appcast, manifest and SHA-256 checksums.
A packaged CLI tarball may also be provided. This repository never contains private telemetry,
credentials, debug symbols or build logs. Publication here does not change the software license;
see the license and notices included in each distribution.

## Installation checks

The manually triggered **Verify published Mac installation** workflow tests the released 1.6.0
DMG on fresh standard Apple silicon runners running macOS 15 and 26. It downloads public bytes;
it does not rebuild the app or access the private source repository. No signing credentials or
user data are supplied. The script refuses to run outside this repository's disposable CI.

It checks the pinned DMG hash, signatures/tickets, installation, default first-run storage,
native app/Core startup, empty-history Analysis, second launch and restart. An explicit
Gatekeeper assessment is recorded separately. Failure to pass a gate fails the workflow.

This is an automated, online test with direct executable launch. It does not replace a browser
download with quarantine, Finder installation, first-open dialog, visual inspection or an offline
first launch. Those manual checks must be reported separately.
