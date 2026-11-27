#!/usr/bin/env python3
"""Contract checks for the read-only site generator and privileged publisher split."""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
BUILD = (ROOT / ".github/workflows/build.yml").read_text()
CORE = (ROOT / ".github/workflows/site-build-core.yml").read_text()
PR = (ROOT / ".github/workflows/build-validation-pr.yml").read_text()

def need(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit("build workflow contract failed: " + message)

def has(pattern: str, text: str) -> bool:
    return re.search(pattern, text, re.MULTILINE) is not None

# The generator is the one read-only source of truth and must never contain
# either publication step or a write-capable token permission.
need(has(r"^on:\s*\n\s+workflow_call:", CORE), "site-build-core must expose workflow_call")
need(has(r"^permissions:\s*\n\s+contents:\s*read", CORE), "site-build-core must default to contents: read")
need(not has(r"^\s+contents:\s*write\s*$", CORE), "site-build-core must not request contents: write")
need("Publish to branch site" not in CORE, "site-build-core must not contain the site publisher")
need("Reports to main" not in CORE, "site-build-core must not write reports to main")
need("actions/upload-artifact@" in CORE, "site-build-core must upload the generated site")
need("name: cedwyn-site-dist" in CORE, "generator artifact name must remain stable")
need("path: dist/" in CORE, "generator must upload dist/")

# Production is a separate, serialized, write-capable publisher that runs only
# after the read-only generator has completed successfully.
need("uses: ./.github/workflows/site-build-core.yml" in BUILD, "production workflow must call the shared generator")
need(has(r"^concurrency:\s*\n\s+group: build-cedwyn-story-image-refresh\s*\n\s+cancel-in-progress: false", BUILD),
     "production build serialization must remain enabled")
need(has(r"^  publish:\s*$", BUILD), "production publisher job is missing")
publisher = BUILD[BUILD.index("  publish:"):]
need("needs: build_site" in publisher, "publisher must depend on the generated-site job")
need(has(r"^\s+permissions:\s*\n\s+contents:\s*write", publisher), "only the publisher job may receive contents: write")
need("actions/download-artifact@" in publisher, "publisher must download the generated artifact")
need("name: cedwyn-site-dist" in publisher, "publisher and generator artifact names must match")
need("git push origin site" in publisher, "publisher must publish the generated site branch")
need("git push origin main" in publisher, "publisher must write the build reports")
need("inputs.dry_run != true" in publisher, "dry_run must suppress production publishing")

# PR caller must invoke only the read-only core and must not receive write scope.
need("uses: ./.github/workflows/site-build-core.yml" in PR, "PR caller must invoke the read-only core")
need(has(r"^permissions:\s*\n\s+contents:\s*read", PR), "PR caller must be contents: read")
need(not has(r"^\s+contents:\s*write\s*$", PR), "PR caller must not request contents: write")
need("Publish to branch site" not in PR and "Reports to main" not in PR,
     "PR caller must not include publisher steps")
need(has(r"^  pull_request:\s*$", PR), "PR gate must trigger for pull requests to main")
need(not has(r"^    paths:", PR), "PR guard checks must not disappear on docs-only PRs")
need(has(r"grep -Eq .+tools/.+web/.+data/", PR),
     "full PR build classifier must include tools, web and data paths")
need(".github/workflows/build-validation-pr.yml" not in BUILD,
     "editing the PR guard itself must not trigger a production site rebuild")

print("Build workflow contract: PASS (read-only generator; separate guarded publisher; content-only full PR build)")
