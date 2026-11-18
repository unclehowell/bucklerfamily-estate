# Watchtower release — 18 November 2026

This marker triggers the central assembly build after the Watchtower dedicated-repository release.

Canonical app source: [unclehowell/cedwyn-watchtower PR #13](https://github.com/unclehowell/cedwyn-watchtower/pull/13), merged to main.

Release contents:
- Evidence-linked party and institutional coverage register (15 role-distinct entities).
- Public panel with role/status filters and live lookups from Watchtower's existing absence and Wayback feeds.
- Version-controlled archive Worker source using the canonical `cedwyn-watchtower/main/public/data/targets.json` feed rather than the retired central `cedwyn` repository.
- Worker v1.0.2 deployed to `bfe-watchtower-archive`; existing `CLOCK` and `WB` bindings retained and usage model kept at `bundled`.

The build report must confirm that the `watchtower` split source is the merged commit from `cedwyn-watchtower`. Do not infer publication from this marker alone.
