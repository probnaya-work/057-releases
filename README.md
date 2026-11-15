# 057 releases

Official distribution files for [057](https://057.probnaya.work), a local computational activity instrument.

Download signed and notarized macOS installers from [Releases](https://github.com/probnaya-work/057-releases/releases).
The macOS app verifies updates with Developer ID and Sparkle signatures. CLI / Web is published as
[`@probnaya/057-cli`](https://www.npmjs.com/package/@probnaya/057-cli).

This repository contains distribution files and release notes only. Source code is maintained
separately. Tags here identify distribution records; each `release.json` records the source
commit and version used to build the actual software. Existing artifact bytes are preserved
when migrated from the previous download host.

Each release provides a DMG, update ZIP, signed appcast, manifest and SHA-256 checksums.
A packaged CLI tarball may also be provided. This repository never contains private telemetry,
credentials, debug symbols or build logs. Publication here does not change the software license;
see the license and notices included in each distribution.
