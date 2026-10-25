# Playbook (story D1)

One file per strategy version: `playbook/<name>-v<n>.yaml`. The paper desk trades only versions whose status is
`paper`. **Today nothing is approved** (experiment 1: no policy passed), so Book 1 trades nothing.

- **Format:** `fno/playbook/schema.py`. Every field is required; an unknown field, feature or structure code is
  refused with the field named. `evidence` stays `null` until approval.
- **Lifecycle:** `research` (candidate) -> `paper` (approved) -> `paused` -> `paper` ... -> `retired`. Allowed changes
  and who may make them: `fno/playbook/transitions.py` (registering a candidate: the desk or the owner; research -> paper and paused -> paper: owner only; paper ->
  paused: owner or the automatic hard-loss rule; any -> retired: owner).
- **Registry:** `registry.csv`, append-only, one row per registration or status change with the version's rule
  fingerprint (SHA-256 of every field except `status` and `evidence`). A changed rule in a registered version is
  refused: make a new version. Past rows are never edited (a test checks the file's git history).
- **Approval:** a version may be `paper` only with every evidence field filled (test results and their commit,
  red-team note, judge verdict, freeze record, owner approval date), the evidence committed before the approval
  (the row's `evidence_commit`) and unchanged since, and every live feature it uses passing its own frozen use rule
  (B7 gate, with each committed report's per-day values recomputed from the recorded data).
- **Commands:** `python -m fno playbook check` (loads everything; lists what is approved) and
  `python -m fno playbook set-status <name> <version> <status> --by owner --on YYYY-MM-DD` (appends the row and
  updates the file's status line; commit both together).

`example-sc-iv-rich-no-event-v1.yaml` is a worked example of the format only: experiment 1's policy P6, which
**failed**. It is `research` and must never be approved as it stands.

`b0-monthly-sc-v1.yaml` is **B0, a measurement** (story R3, owner decision 1 A): registered `research` on 16 Oct 2026,
shadowed from the next session to measure premium, costs and fills at real quotes. `edge_family: measurement` marks
it (`fno/playbook/measurement.py`); it is never promoted and never counted as a positive candidate. Idea card:
`research/ideas/B0.md`.
