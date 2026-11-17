# Evidence resync and daily Gmail/NVIDIA review intake

This workflow is for the BucklerFamily.estate/Cedwyn research apps. It does not use DATRO.

## Daily flow

1. At 06:20 UTC, GitHub Actions queries only the selected GHF and Cedwyn Gmail labels using a Gmail OAuth grant with the read-only `gmail.readonly` scope.
2. `gmail_export.py` fetches up to 25 recent matching messages. It does not modify Gmail, send mail, change labels, fetch attachment content or store raw Gmail bodies. It redacts common contact details, signatures and quoted chains before sending the remaining text to NVIDIA NIM.
3. NVIDIA returns a cautious classification and a neutral public-safe summary, with routing hints for `that-old-chestnut` and/or `dartboard`. Outputs that fail the safety checks are discarded.
4. The export contains only a hashed message key, date, organisation, type, title, summary, app routing and review flags. `resync.py` deduplicates these against prior mail candidates and the central catalogue, then adds new items to `resync/candidates/` on the orphan `evidence-resync` branch.
5. The workflow comments on the tracking issue when candidates arrive. Nothing is written into either app's public data, and nothing is sent from Gmail. Human review and an app-source change are required before publication.

The exporter keeps only hashes of processed Gmail message IDs for 60 days, so ignored or already-reviewed messages are not repeatedly sent to NVIDIA. The original message IDs and message bodies are never written to the branch. Messages with attachment content are not opened; only the presence of an attachment is recorded.

## App publication path

- **That Old Chestnut:** update its source data in `unclehowell/cedwyn-that-old-chestnut`. The central `bucklerfamily-estate` build assembles it into the public Cedwyn site.
- **Dartboard:** update `unclehowell/cedwyn-dartboard`. Its own Cloudflare Pages project deploys from `main`.
- The existing daily change-gated webapp refresh checks for source changes. The existing site build regenerates data views from the central catalogue. Neither is allowed to promote AI candidates automatically.

## Required GitHub Actions secrets

Add these under `unclehowell/bucklerfamily-estate` → Settings → Secrets and variables → Actions → Secrets:

| Secret | Purpose |
|---|---|
| `NVIDIA_API_KEY` | NVIDIA API Catalog / hosted NIM key |
| `GMAIL_CLIENT_ID` | Google OAuth client ID |
| `GMAIL_CLIENT_SECRET` | Google OAuth client secret |
| `GMAIL_REFRESH_TOKEN` | Offline refresh token authorised by the owner for Gmail read-only access |

Use the scope `https://www.googleapis.com/auth/gmail.readonly` only. Do not grant send, compose, modify, labels or full-mailbox scopes. The refresh token belongs in Actions Secrets; never commit it, paste it into an issue, or send it in chat.

## Optional GitHub Actions variables

| Variable | Purpose |
|---|---|
| `NVIDIA_MODEL` | NVIDIA model ID; defaults to `google/gemma-3-12b-it` |
| `GMAIL_QUERY` | Override the default project-label query when needed |

The default Gmail query is limited to GHF/Authorities, GHF/Action needed, GHF/Awaiting reply, GHF/Evidence & attachments, the vetted GHF auto-reply label, and Cedwyn/Case + Cedwyn/Institutions labels. Sales, Social, Receipts and the general inbox are excluded. Confirm the label set in Gmail before the first live run; if labels are renamed or recreated, update the query.

## Human-in-the-loop rules

- Check the source message and attachments yourself before promoting a candidate.
- Confirm institution, date, direction, official reference, document/attachment, wording and the app it belongs in.
- For That Old Chestnut, confirm whether it is an FOI/EIR or records-disclosure reply, and whether it belongs in the curated chestnut list.
- For Dartboard, confirm the institution, applicable avenue/ring, outcome/status, references and whether any deadline needs a hand-check.
- Do not publish private contact details, private family/health information, unredacted attachments, AI inferences or a claim of wrongdoing.
- Keep source evidence and derivative summaries distinct. An AI summary is an index aid, not evidence and not a finding.

## Private data branch

Both daily ingestion and twice-weekly catalogue snapshots use `bootstrap-data-branch.sh` to create or fetch the small orphan `evidence-resync` branch. This branch is not a Pages deployment branch and is not served publicly. It contains only the privacy-filtered review snapshots and hashed processing watermarks, never raw email.

## Manual test

Run `evidence-resync-daily` with `dry_run=true`. The exporter prints counts only and writes neither the Gmail export nor the processed-message watermark. Once the owner has added the secrets and reviewed the query, run a normal workflow dispatch and inspect the candidate file before merging any app-content change.

— BucklerFamily.estate daily evidence workflow
