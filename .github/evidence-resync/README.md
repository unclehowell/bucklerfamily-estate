# Daily Gmail / NVIDIA review intake and webapp refresh

Scope: BucklerFamily.estate and the Cedwyn research apps only. DATRO is out of scope.

This site-wide workflow PR is labelled `site-wide`, as required for changes targeting `main`.

## Important storage boundary

The source repository `unclehowell/bucklerfamily-estate` is public. It must contain workflow code only, never Gmail-derived summaries, message hashes, raw email or review queues.

Create a separate **private** GitHub repository named `unclehowell/bucklerfamily-ops-private`. It stores all review data on an orphan branch called `evidence-resync`. The branch is not a Pages deployment branch and is not connected to Cloudflare Pages. If the private repository is missing or inaccessible, the scheduled jobs stop at the bootstrap step; they must not fall back to storing data in the public repository.

## Daily flow

1. At 06:20 UTC, GitHub Actions queries only selected GHF/Cedwyn Gmail labels using an owner-authorised OAuth grant with the read-only `gmail.readonly` scope.
2. `gmail_export.py` fetches up to 25 matching recent messages. It never modifies Gmail, sends mail, changes labels, reads attachment content or stores raw message bodies. It redacts common personal/contact details, signatures and quoted chains before sending the remaining text to NVIDIA NIM.
3. NVIDIA classifies relevant correspondence and proposes a neutral summary and routing hint for `that-old-chestnut` and/or `dartboard`. Outputs that fail the safety checks are discarded.
4. The exporter writes only to the private operations checkout: a hashed message key, date, organisation, type, title, summary, target app(s), direction, attachment-presence flag and review-required marker.
5. `resync.py` deduplicates mail, spill and online candidates, then appends them to the private operations review queue. The public issue comment and Actions log contain counts only, never candidate titles or summaries.
6. Every candidate remains a proposal. Nothing is published into either app's public data and no email is sent. Human review and an app-source change are required before publication.

Only SHA-256 hashes of processed Gmail message IDs are retained (60 days) to avoid repeatedly processing the same message. The original message IDs, raw bodies and attachment content are never saved. The exporter records only whether an attachment was present; a person must inspect the original attachment before promotion.

## App publication path

- **That Old Chestnut:** reviewed changes go to the dedicated source repository `unclehowell/cedwyn-that-old-chestnut`. The central `bucklerfamily-estate` build assembles it into the Cedwyn Pages site.
- **Dartboard:** reviewed changes go to `unclehowell/cedwyn-dartboard`. Its Cloudflare Pages project deploys from `main`.
- The central daily change-gated refresh and existing Pages integrations handle deployment once source changes are merged. AI candidates themselves never trigger publication.

## Required private operations repository setup

Create `unclehowell/bucklerfamily-ops-private` as **Private**, with an empty initial README or other default branch. Then create a fine-grained GitHub token restricted to that repository with **Contents: Read and write**. Do not grant access to other repositories or administration.

In the public source repository `unclehowell/bucklerfamily-estate`, add this Actions secret:

| Secret | Purpose |
|---|---|
| `OPS_REPO_TOKEN` | Fine-grained token with Contents read/write on the private operations repo |

Add this Actions variable (optional; the workflow defaults to the suggested repo name):

| Variable | Purpose |
|---|---|
| `OPS_REPO` | Private repository in owner/name format |

The workflows bootstrap or fetch the orphan `evidence-resync` branch in that private repository using this token. They never push data to a branch of the public source repository.

## Required Gmail and NVIDIA Actions secrets

In `unclehowell/bucklerfamily-estate` → Settings → Secrets and variables → Actions → Secrets, add:

| Secret | Purpose |
|---|---|
| `NVIDIA_API_KEY` | NVIDIA API Catalog hosted NIM key |
| `GMAIL_CLIENT_ID` | Google OAuth client ID |
| `GMAIL_CLIENT_SECRET` | Google OAuth client secret |
| `GMAIL_REFRESH_TOKEN` | Owner-authorised offline refresh token for Gmail read-only access |

The only Gmail scope needed is `https://www.googleapis.com/auth/gmail.readonly`. Do not grant send, compose, modify, labels or full-mailbox access. Do not paste credentials into this repository, an issue, a PR comment or chat. Store them only as GitHub Actions secrets.

Google's Gmail API requires OAuth 2.0 credentials; offline access is needed for the scheduled workflow to refresh an access token while you are not present. Google classifies `gmail.readonly` as a restricted scope, so Google Cloud's consent/verification requirements may apply to the OAuth app. Do not leave an external OAuth consent screen in **Testing** for a long-running schedule: Google says refresh tokens issued in Testing expire after seven days. Move the app to an appropriate production state and complete any verification Google requires before relying on unattended daily runs.

## Optional Actions variables

| Variable | Purpose |
|---|---|
| `NVIDIA_MODEL` | NVIDIA model ID; defaults to `google/gemma-3-12b-it` |
| `GMAIL_QUERY` | Override the default project-label query |

The current default query is limited to vetted GHF automatic replies, GHF authority/action/evidence labels and Cedwyn case/institution labels. It excludes Sales, Social, Receipts and general inbox mail. Confirm the selected labels before first live use; amend the query if labels are renamed or recreated.

## Human-in-the-loop rules

- Check the original Gmail message and any attachment before promoting a candidate.
- Confirm the institution, date, sender role, direction, official reference, wording, document and correct app.
- For That Old Chestnut, confirm that the item belongs to the FOI/EIR or records-disclosure register and fits the curated list.
- For Dartboard, confirm the party, applicable avenue/ring, outcome/status, evidence reference and any deadline by hand.
- Keep artifact, evidence, allegation, institutional position and inference distinct. An AI summary is an index aid, not evidence or a finding.
- Never publish private contact information, private family/health details, unredacted attachments, AI inference or a finding of wrongdoing on the strength of the model output alone.

## Schedules and manual test

- `evidence-resync-daily`: 06:20 UTC every day; workflow dispatch supports `dry_run=true`.
- `webapps-refresh-twice-weekly`: 06:40 UTC Monday and Thursday; a manual dispatch defaults to dry-run.
- Test the daily workflow with `dry_run=true` first. A dry run prints counts only and writes neither the export nor the processed-message watermark.
- Only run a normal dispatch after the private repo, token, Gmail OAuth and NVIDIA key are configured and the default Gmail label query has been checked.

— BucklerFamily.estate evidence-resync
