#!/usr/bin/env bash
# Regenerate the codelab HTML from index.lab.md using claat.
# Output goes to codelab/managed-agents-gemini-api/ (claat's export dir, named after the codelab id).
#
# Prerequisites: go install github.com/googlecodelabs/tools/claat@latest
#
# Preview locally with: claat serve (from this directory)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DOCS_DIR="$REPO_ROOT/docs"

cd "$SCRIPT_DIR"

rm -rf managed-agents-gemini-api
claat export index.lab.md

echo "Copying to docs/..."
rm -rf "$DOCS_DIR"
mkdir -p "$DOCS_DIR"
cp -r managed-agents-gemini-api/. "$DOCS_DIR/"
touch "$DOCS_DIR/.nojekyll"

echo "Done. Codelab at $DOCS_DIR/index.html"
