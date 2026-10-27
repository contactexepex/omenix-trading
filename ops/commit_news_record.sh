#!/usr/bin/env bash
# Stories P2b3 and P2d: the commit step of the news record workflows (news-promote.yml, news-cluster.yml). One definition
# of the guard, so the two workflows cannot drift. Env: MANIFEST (the csv this run extends), RECEIPTS (space-separated
# receipt folders), COMMIT_MESSAGE.
#
# A run killed mid-write can leave a torn last line in the manifest; it must never reach main. The guard judges the FILE
# (`check-manifest`), never the command's exit code, so a mere rejection still commits the good rows. Receipts are
# always committed: they keep the original evidence time of each Drive file, and the next run re-adds the missing rows.
# A broken manifest is discarded from the working tree (so the next pull is clean), not committed, and turns the run red.
set -e
if python -m fno news check-manifest "$(dirname "$MANIFEST")" --file "$(basename "$MANIFEST")"; then
  git add "$MANIFEST"
  broken=0
else
  git checkout -- "$MANIFEST" 2>/dev/null || rm -f "$MANIFEST"
  broken=1
fi
# A killed run can leave a half line last in a receipt batch file; it must never reach main either. The fragment (never a
# whole line) is cut off, the good lines are committed, and the run ends red.
python -m fno news repair-batches receipts/_batches || broken=1
for folder in $RECEIPTS; do
  if [ -e "$folder" ]; then git add -- "$folder"; fi
done
git diff --cached --quiet || git commit -m "$COMMIT_MESSAGE $(date -u +%FT%TZ)"
# `A && B` under `set -e` does not stop the script when A fails, so each is checked on its own: a run that pushed
# nothing must never end green.
git pull --no-rebase --no-edit origin main || exit 1
git push origin HEAD:main || exit 1
exit "$broken"
