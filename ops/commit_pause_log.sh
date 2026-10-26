#!/usr/bin/env bash
# Story R1b2: the last step of every workflow that can reach a paced host. A run appends its pause transitions to a
# git-ignored run-local file (so no tracked file is dirty while the other committers pull); this merges those rows into
# the committed log after its own pull, commits and pushes. It sets the hooks path and the identity itself (the
# record scan always runs), and it never fails the run's data: the workflow marks the step continue-on-error.
# Note: `git push origin HEAD:main` pushes the whole branch, so it also publishes any commit the run made earlier and
# has not pushed (the Python committers push their own; this step is last, after them).
set -u
LOCAL="research/data/resilience/.run/paced-hosts.csv"
LOG="research/data/resilience/paced-hosts.csv"

if [ ! -s "$LOCAL" ]; then
  echo "pause log: no transitions this run"
  exit 0
fi
git config core.hooksPath .githooks
git config user.name "omenix-pause-log"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"

for attempt in 1 2 3; do
  if ! git pull --no-rebase --no-edit origin main; then
    echo "pause log: pull failed (try $attempt)"
    git merge --abort 2>/dev/null
    continue
  fi
  if [ ! -f "$LOG" ]; then head -n 1 "$LOCAL" > "$LOG"; fi
  tail -n +2 "$LOCAL" | while IFS= read -r row; do
    grep -qxF -- "$row" "$LOG" || printf '%s\n' "$row" >> "$LOG"
  done
  git add -- "$LOG"
  if ! git diff --cached --quiet; then
    git commit -q -m "R1b2: pause log rows $(date -u +%FT%TZ)" -- "$LOG" || exit 1
  fi
  if git push origin HEAD:main; then
    rm -f "$LOCAL"
    exit 0
  fi
  echo "pause log: push failed (try $attempt)"
done
exit 1
