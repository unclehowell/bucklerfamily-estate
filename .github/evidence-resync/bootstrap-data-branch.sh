#!/usr/bin/env bash
set -euo pipefail
DATA_DIR="${1:-data}"
: "${OPS_REPO:?Set the private operations repository name, e.g. unclehowell/bucklerfamily-ops-private}"
: "${OPS_REPO_TOKEN:?OPS_REPO_TOKEN is required}"
echo "::add-mask::$OPS_REPO_TOKEN"
mkdir -p "$DATA_DIR"
git -C "$DATA_DIR" init -q
git -C "$DATA_DIR" config user.name "bucklerfamily-private-evidence-resync"
git -C "$DATA_DIR" config user.email "41898282+github-actions[bot]@users.noreply.github.com"
git -C "$DATA_DIR" remote remove origin 2>/dev/null || true
git -C "$DATA_DIR" remote add origin "https://x-access-token:${OPS_REPO_TOKEN}@github.com/${OPS_REPO}.git"

if git -C "$DATA_DIR" ls-remote --exit-code --heads origin evidence-resync >/dev/null 2>&1; then
  git -C "$DATA_DIR" fetch --quiet --depth=1 origin refs/heads/evidence-resync:refs/remotes/origin/evidence-resync
  git -C "$DATA_DIR" checkout -q -B evidence-resync refs/remotes/origin/evidence-resync
else
  # Create a genuinely orphaned, small data branch in the PRIVATE operations repository.
  git -C "$DATA_DIR" checkout -q --orphan evidence-resync
  find "$DATA_DIR" -mindepth 1 -maxdepth 1 ! -name .git -exec rm -rf {} +
  cat > "$DATA_DIR/README.md" <<'EOF'
# Private BucklerFamily operations data

This orphan branch holds private daily Gmail/NVIDIA review candidates, catalogue-resync candidates,
and refresh snapshots. It is not a deployment branch and is never served by Cloudflare Pages.
Raw Gmail bodies, message IDs, attachments, OAuth credentials and personal contact details must
never be committed here.
EOF
  git -C "$DATA_DIR" add README.md
  git -C "$DATA_DIR" commit -q -m "Bootstrap private evidence-resync data branch"
  git -C "$DATA_DIR" push --quiet -u origin HEAD:evidence-resync
fi
