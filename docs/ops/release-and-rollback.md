# BucklerFamily.estate release, verification and rollback runbook

**Applies to:** `unclehowell/bucklerfamily-estate`  
**Cloudflare Pages project:** `cedwyn`  
**Production source branch:** `site`  
**Canonical host:** `https://bucklerfamily.estate`  
**Last verified release baseline:** 25 November 2026

## 1. Release architecture

The repository's production flow is:

1. A change is merged into `main`.
2. The `build-cedwyn` GitHub Actions workflow runs the full generation pipeline: preflight, theme assembly, catalogue checks, data views, link rewrite, self-containment, database build, evidence/Q&A checks and Pages file-limit check.
3. After a successful build, the generated `dist/` output is committed to the repository's `site` branch.
4. Cloudflare Pages project `cedwyn` deploys from `site` to the configured production hostnames.
5. The build stamp at `/_cedwyn/reports/build.json` records the `main` SHA used to generate the published site.

**Do not push source files directly to `site`.** The `site` branch is generated output, not the source of truth. Do not change the Pages production branch away from `site`.

## 2. Normal release checklist

Before merge:
- Confirm the PR's required editorial/evidence/scope checks are green.
- For changes under `tools/**`, `web/**`, `data/**`, `themes.json`, `split-repos.json`, `sections.lock` or relevant build files, require the full read-only generated-site build check once the PR build gate is merged and operational.
- Confirm no generated data, secrets, private task content or unintended records were added to public pages.

After merge:
1. Open Actions → `build-cedwyn` and confirm the run corresponds to the new `main` commit.
2. Confirm every required build step completed successfully, including:
   - forensic catalogue publication guard;
   - built SQLite catalogue and hierarchy verification;
   - strict outbound-link guard;
   - strict self-contained check;
   - app-page and Q&A completeness guards;
   - nav validation;
   - Pages 20,000-file limit.
3. Confirm the `Publish to branch site` step succeeded or correctly reported no changes.
4. Read `/_cedwyn/reports/build.json` from the production host. Its `commit` value must equal the `main` SHA built by Actions.
5. In Cloudflare Dashboard → Workers & Pages → Pages → `cedwyn` → Deployments, confirm the newest production deployment has status `success`, branch `site`, and the expected site commit SHA.
6. Verify production:
   - `https://bucklerfamily.estate/`
   - `https://bucklerfamily.estate/research/parcel-separation-possession-scope-1916-1987/`
   - `https://bucklerfamily.estate/parcels/`
   - `https://bucklerfamily.estate/_cedwyn/reports/build.json`
   - `https://bucklerfamily.estate/x78s8jej33i8f8rrj4is88/flow-health.json`
7. Confirm the public flow-health endpoint returns HTTP 200 JSON with schema `cedwyn.flow-watch/1.0`; confirm the OIDC event signal completed successfully.

A successful GitHub build alone is not proof of deployment. The `site` commit, Cloudflare production deployment and public response checks must agree.

## 3. Emergency rollback: Cloudflare Pages

Use a rollback when the current production deployment is harmful or materially broken and the last known-good production deployment is still retained.

### 3.1 Identify a safe target

1. Pause merges and avoid triggering another production build while investigating.
2. Query the latest production deployment list:

   ```http
   GET /accounts/{account_id}/pages/projects/cedwyn/deployments?env=production&per_page=20
   ```

3. Select a deployment only if all are true:
   - `environment` is `production`;
   - `latest_stage.status` is `success`;
   - its `deployment_trigger.metadata.branch` is `site`;
   - its site commit is identified;
   - its deployment URL and important pages have been checked;
   - the target has not been deleted.
4. Do not use a preview deployment as a rollback target. Cloudflare only permits successful production deployments that remain available.
5. Record the current bad deployment ID, proposed rollback target ID, both site commit SHAs, the associated `main` build SHAs and the reason for rollback in the incident record.

### 3.2 Execute rollback

**Dashboard method (preferred during an incident):**

1. Open Cloudflare Dashboard → Workers & Pages → Pages → `cedwyn` → Deployments.
2. Find the selected previous successful production deployment.
3. Open its actions menu and choose **Rollback to this deployment**.
4. Review the deployment ID and commit one final time, then confirm.

**API method (for an authorised operator):**

Cloudflare documents the Pages rollback endpoint as:

```http
POST /accounts/{account_id}/pages/projects/cedwyn/deployments/{deployment_id}/rollback
Authorization: Bearer <CLOUDFLARE_API_TOKEN>
```

Use the **previous successful production deployment ID** as `{deployment_id}`. The required token permission is **Pages Write**. Do not put tokens in the repository, issue text, workflow logs or chat.

Source: Cloudflare, *Roll back a Pages deployment* (API reference, accessed 25 November 2026): https://developers.cloudflare.com/api/resources/pages/subresources/projects/subresources/deployments/methods/rollback/.

### 3.3 Verify rollback

After the rollback request:
1. Query the production deployment list again.
2. Confirm Cloudflare reports the rollback target's deployment/commit as the current successful production deployment and that its aliases include the canonical production hostnames.
3. Fetch `/_cedwyn/reports/build.json` and check the main SHA represented by the restored site.
4. Probe the homepage, parcel page, Q&A and key evidence catalogue routes.
5. Probe the public flow-health endpoint. Worker route changes may be independent of Pages content; check them rather than assuming rollback restores Worker configuration.
6. Re-run the authenticated flow-watch signal or confirm its next scheduled run.
7. Record the rollback time, previous and restored deployment IDs, both site commit SHAs, main build SHA and probe results.

Cloudflare's Pages rollback changes the production deployment; it does **not** rewind the Git repository's `main` or `site` branch. Keep the bad source commit available for diagnosis and make a corrective PR.

## 4. Recover and roll forward

1. Identify the regression from the failed build log, deployment logs or production probe.
2. Fix the source on a topic branch and open a PR. Do not hot-edit the `site` branch.
3. Require the relevant CI and full read-only site build to pass before merging when the full PR gate is available.
4. Merge the fix to `main`.
5. Allow the serialized `build-cedwyn` pipeline to build and publish. Do not start competing manual builds while a production build is active.
6. Repeat the post-merge checks in section 2.
7. Once the corrected production deployment is verified, the rollback target can remain in deployment history as a known-good point until normal Cloudflare retention removes it.

For a manual rebuild without a new merge, use Actions → `build-cedwyn` → Run workflow on `main`. Keep `dry_run=false` only when a production publish is intended. A dry run must never be described as a deployment.

## 5. Verified 25 November 2026 release record

The corrected parcel research release is recorded as:

| Layer | Identifier | Result |
|---|---|---|
| Source PR | #60 | Merged |
| Source `main` build SHA | `766ef8331db73087f929ee0249b445cfeb98b195` | Built successfully |
| Generated `site` commit | `0aa21c6191ec5b8a694d64bd2edc0c97cdb7d74d` | Published |
| Cloudflare Pages deployment | `d309298d-ddf0-4c8b-8a51-79e990e097fe` | Production deploy successful |
| Prior successful production deployment | `0d76e19a-927b-4c23-9d1e-efb9ef0585ab` | Retained at time of verification |

This is an example release record, **not** a permanent rollback instruction. Always query current deployment state and verify the chosen target at the time of an incident.

## 6. Operational boundaries

- `main` is source; `site` is generated production output.
- The production build is serialised; keep `cancel-in-progress: false`.
- Never bypass the full build by manually pushing generated files to `site`.
- Never give PR code Cloudflare tokens or a `contents: write` publisher token.
- Do not close an incident until the public site and deployment state have been verified.
- Keep this runbook updated when the deployment workflow, Pages project, domains or build-check names change.
