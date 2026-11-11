# Evidence resync (cedwyn#582)

Two scheduled workflows keep the central catalogue's intake and the webapps moving. No one has to ask for either.

| workflow | when (UTC) | what it does |
|---|---|---|
| `evidence-resync-daily.yml` | 06:20 every day | Gathers NEW evidence/artifact **candidates** from three sources: project mail (a box-side export), spills (`/spill/api/status`) and online search (Internet Archive, TNA Discovery, Wikidata; a fixed query set). Writes them to `resync/candidates/` on the orphan branch `evidence-resync` and comments on #582 when anything is new. |
| `webapps-refresh-twice-weekly.yml` | 06:40 Mon + Thu | Snapshots the central catalogue counts. If no `build-cedwyn` run is queued or running, it dispatches ONE. The build's "Data views" step regenerates every webapp's data from `data/core`. |

**Catalogue lock.** Both workflows only ADD candidates to a review file. They never write, edit, move or delete a record. They never open or merge a pull request and never apply `owner-approved`. A candidate becomes a record only through the spill / catalogue process, as a `catalogue-change` PR. The daily job never starts a site build.

**Optional keys.** Both workflows run without any secret. If a repo secret `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` is set (Settings → Secrets and variables → Actions), the daily job asks for a one-line scope and kind label on up to 40 online candidates. Only the first key found is used. A repo variable `RESYNC_LLM_MODEL` can name the model.

**Dedupe.** The daily job checks every candidate against `/api/catalogue` (all records), the online gap finder's ledger and its own `resync/seen.json`.

**Public text.** Candidates carry titles, dates, holders and one-line summaries only. Anything with an email address, phone number, owner name, banned word or withheld date digits is dropped. The mail export already leaves out rows that need hand redaction.

**Manual runs.**
- `evidence-resync-daily`: `dry_run=true` collects and prints only.
- `webapps-refresh-twice-weekly`: `dry_run` defaults to true on a manual run, so a test never starts a build.

— Sion's Tab agent
