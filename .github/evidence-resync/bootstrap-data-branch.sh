#!/usr/bin/env bash
set -euo pipefail
DATA_DIR="${1:-data}"
: "${GITHUB_REPOSITORY:?GITHUB_REPOSITORY is required}"
: "${GH_TOKEN:?GH_TOKEN is required}"
echo "::add-mask::$GH_TOKEN"
mkdir -p "$DATA_DIR"
git -C "$DATA_DIR" init -q
git -C "$DATA_DIR" config user.name "bucklerfamily-estate-evidence-resync"
git -C "$DATA_DIR" config user.email "41898282+github-actions[bot]@users.noreply.github.com"
git -C "$DATA_DIR" remote remove origin 2>/dev/null || true
git -C "$DATA_DIR" remote add origin "https://x-access-token:${GH_TOKEN}@github.com/${GITHUB_REPOSITORY}.git"
if git -C "$DATA_DIR" ls-remote --exit-code --heads origin evidence-resync >/dev/null 2>&1; then
  git -C "$DATA_DIR" fetch --quiet --depth=1 origin refs/heads/evidence-resync:refs/remotes/origin/evidence-resync
  git -C "$DATA_DIR" checkout -q -B evidence-resync refs/remotes/origin/evidence-resync
else
  git -C "$DATA_DIR" checkout -q --orphan evidence-resync
  find "$DATA_DIR" -mindepth 1 -maxdepth 1 ! -name .git -exec rm -rf {} +
  cat > "$DATA_DIR/README.md" <<'EOF'
# Private workflow data branch

This orphan branch holds daily privacy-filtered evidence-resync and webapp-refresh review files.
It is not a deployment branch and is not served by Cloudflare Pages. Raw Gmail message bodies and
attachments must never be committed here.
EOF
  git -C "$DATA_DIR" add README.md
  git -C "$DATA_DIR" commit -q -m "Bootstrap private evidence-resync data branch"
  git -C "$DATA_DIR" push --quiet -u origin HEAD:evidence-resync
fi
