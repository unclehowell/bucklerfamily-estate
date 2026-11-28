# Release notes — preservation email archive backfill

Date: 28 November 2026  
Repository: unclehowell/bucklerfamily-estate  
Branch: feature/issue-85-preservation-email-backfill

## Changes
- Added four recovered sent preservation-request emails as EV-2051–EV-2054:
  - EV-2054 — Loosemores, 26 May 2026 (earlier preservation request referenced by EV-1922).
  - EV-2051 — Treescene, 17 September 2026 (public-safe extract; five original attachments not copied).
  - EV-2052 — Companies House, 10 October 2026 (verbatim public-safe transcript).
  - EV-2053 — BP Legal, 16 October 2026 (sender email address redacted).
- Added public-safe transcript backfills for EV-1922, EV-1926, EV-1933, EV-1940 and EV-1947. EV-1922 and EV-1926 are verbatim; EV-1933 is an extract omitting quoted earlier correspondence and a project redirect; EV-1940 and EV-1947 omit a project redirect.
- Updated the email index, redaction flags, part count and email archive README. The archive now contains 1,147 email records across 25 parts.

## Integrity and privacy
- New EV IDs are assigned in ingestion order; historical message dates remain in the index. Existing IDs are not renumbered.
- Original Gmail messages and attachments are not stored in this repository or modified by this change.
- Public-safe extracts are explicitly labelled. Personal identifiers, sender email address and nonessential narrative are omitted where noted.
- No email was sent as part of this change.

## Dependency
This is the companion data change for the Cedwyn catalogue preservation-coverage feature (cedwyn-catalogue issue #53 / app v0.22.0). The app preview reads this branch with the query parameter emails=preservation-staged. Merge this data PR before deploying the app release to production.
