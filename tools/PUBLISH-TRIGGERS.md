# Publish trigger ledger

This file is deliberately metadata-only. A change under tools/ triggers the BucklerFamily.estate site build, which assembles the dedicated application repositories listed in split-repos.json. Never add email text, private names, contact details, case identifiers, or case evidence here.

## 24 November 2026 — refresh dedicated app source

Purpose: request one full site rebuild so the central published site re-assembles the latest dedicated That Old Chestnut source after its freshness/non-inference guardrail changes.

- Source repository: unclehowell/cedwyn-that-old-chestnut
- Source branch: main
- Source commit: a070a76f3e372c2af4cfcc1678b5badfd141aae8
- App version: 0.6.1
- Changed source files: public/_ui/latest-mail.a2ui.json; tools/view.template.json; VERSION; APP-README.md; CHANGELOG.md
- Previous deployed source stamp in the site's assemble report: 480667ade4169b85e8e4742fc973af293e8c13c6
- Required acceptance: build-cedwyn succeeds; the new site branch contains the static-snapshot and non-inference warning in /that-old-chestnut/; the published page and its served JSON are checked after deployment.

Dartboard is independently deployed from its dedicated Pages project and was verified at commit e5926ff0bd0b373697975285e3a6f84365d8dc7d. Its central-site route remains a separate crawl-derived output and is not claimed updated by this trigger.

No private correspondence, HubSpot text, contact details or case material is included.
