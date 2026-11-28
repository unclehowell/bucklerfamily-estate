#!/usr/bin/env python3
"""Fail-closed contract check for the daily app-refresh registry."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
manifest = json.loads((ROOT / "split-repos.json").read_text())
registry = json.loads((ROOT / ".github/daily-refresh/apps.json").read_text())
odd = (ROOT / ".github/daily-refresh/odd.py").read_text()
ghf = (ROOT / "workers/ghf-status/worker.js").read_text()
ready = (ROOT / "workers/agent-ready/index.js").read_text()

canonical = {}
for app in manifest.get("apps", []):
    repo = app.get("repo")
    if not repo:
        raise SystemExit("split-repos.json contains an app without a repo")
    if repo in canonical and (canonical[repo].get("mode"), canonical[repo].get("deploy")) != (app.get("mode"), app.get("deploy")):
        raise SystemExit(f"conflicting manifest entries for {repo}")
    canonical[repo] = app

daily = registry.get("apps", [])
daily_repos = set()
for app in daily:
    repo = app.get("repo")
    if repo not in canonical:
        raise SystemExit(f"daily registry has an unknown repo: {repo}")
    source = canonical[repo]
    if app.get("mode") != source.get("mode"):
        raise SystemExit(f"mode mismatch for {repo}: daily={app.get('mode')} manifest={source.get('mode')}")
    if app.get("deploy") != source.get("deploy"):
        raise SystemExit(f"deploy mismatch for {repo}: daily={app.get('deploy')} manifest={source.get('deploy')}")
    if app.get("lane") not in {"github", "cloudflare"}:
        raise SystemExit(f"invalid lane for {repo}: {app.get('lane')}")
    daily_repos.add(repo)

missing = sorted(set(canonical) - daily_repos)
if missing:
    raise SystemExit("apps missing from daily refresh registry: " + ", ".join(missing))

if 'x.get("deploy") == "repo"' not in odd:
    raise SystemExit("odd.py must skip legacy-branch sync for direct-deploy apps")
if "bucklerfamily-estate/main/.github/daily-refresh/apps.json" not in ghf:
    raise SystemExit("ghf-status does not read the successor daily registry")
if "feedLatest('unclehowell/bucklerfamily-estate', 'main', 'data/core')" not in ghf:
    raise SystemExit("ghf-status does not read the successor catalogue")
if "const keyOf = a => [a.repo, 'main'];" not in ghf:
    raise SystemExit("ghf-status must read dedicated app main branches")
if "bucklerfamily-estate/main/web/ebooks/supplement/cedwyn-supplement-2026-10-25.pdf" not in ready:
    raise SystemExit("agent-ready does not serve the successor-hosted identical supplement")
if "unclehowell/cedwyn/main" in ghf or "unclehowell/cedwyn/main" in ready:
    raise SystemExit("an active Worker source still points to the retiring repository")

print(f"daily refresh registry OK: {len(daily)} entries / {len(daily_repos)} app repositories / {len(canonical)} canonical repositories")
