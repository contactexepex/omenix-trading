#!/bin/sh
# Which checks a push needs (checks.yml): prints `code=true` unless every changed file is a lane-3 path (judge and
# review files, conversation logs, decision and register rows, number claims; CLAUDE.md "Judge lanes"), then
# `code=false`. Lane-3-only pushes skip pytest, ruff and the import check; the record scan always runs, on the changed
# files.
#   sh tools/ci_scope.sh BASE HEAD [CHANGED_LIST]   # CHANGED_LIST: where to write the changed files that exist (NUL)
# Any doubt counts as code: no BASE (a new branch: all zeros), a BASE missing from history (a force-push), or no change.
set -eu
base=${1:-}
head=${2:-HEAD}
list=${3:-/dev/null}
LANE3='^(reviews/|conversations/|numbers/|docs/DESK_DECISIONS\.md$|docs/WORK_REGISTER\.md$)'

code() { echo "code=true"; exit 0; }

case "$base" in "" | 0000000000000000000000000000000000000000) code ;; esac
git cat-file -e "$base^{commit}" 2>/dev/null || code
changed=$(git diff --name-only "$base" "$head")  # deletions included: deleting a code file is a code change
[ -n "$changed" ] || code
if printf '%s\n' "$changed" | grep -qvE "$LANE3"; then code; fi
git diff --name-only -z --diff-filter=d "$base" "$head" > "$list"  # what the record scan reads: files that exist
echo "code=false"
