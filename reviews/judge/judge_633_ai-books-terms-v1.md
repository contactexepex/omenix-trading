# Judge 633: the AI books' terms v1, Book 2's envelope and Book 3's constitution (story/ai-books-terms-v1 @ 7d44b51e2)

**PASS (2 minor, 1 note). Lane 1** (what a book may trade). Judge F, own session (session_01A8XfbTUVgeeEpqatHaWbtP).
Labels: strong, some, reasoning only.

## Criteria

| # | Check | Result | My evidence |
|---|---|---|---|
| 1 | Envelope = the 16 Oct terms and Q9 | MET | `b0-monthly-sc-v1.yaml`: follow_rule, choose_strategy, no_trade, choose_width, reduce_lots, all `allowed`, nothing else; DESK_DECISIONS 229 (5) "envelope v1 narrow" and 345 (2) Q9, word for word |
| 2 | Constitution = the 16 Oct terms and Q10 | MET | `constitution-v1.yaml`: NIFTY, monthly, structures BF CCS CDS LC LP PCS PDS SC SF (= C4's nine defined-risk codes, `STRUCTURES` + `STRUCTURES_ONE_SIDE`), `max_holding_days: 21`; rows 229 (1)-(3) and 345 (3). The Rs 10,000 cap is by reference: `risk: risk.profiles.books`, whose `max_loss_per_trade_rs: 10000` (`config.yaml:57`); D5 refuses a number in its place |
| 3 | They parse with D4's and D5's own parsers | MET | `parse_envelope` → `('b0-monthly-sc', 1)`, five `allowed`; `parse_constitution` → v1, the nine codes, 21; `ConstitutionFiles.by_sha256` and `EnvelopeFiles` accept the file names |
| 4 | Inert until registered in D6 | MET | C4's Book 3 mode takes the constitution only by the D6-registered SHA-256 and fails closed otherwise (`validity_constitution.py:34-40`); Book 2's `EnvelopeMode` is wired with the same `RegisteredComponents` (`checks/wiring.py:88-97`); this branch registers nothing (two files only) |
| 5 | The playbook named is a registered candidate (Q11) | MET | `playbook/registry.csv`: `b0-monthly-sc,1,...,research`, the only registered playbook |
| gates | | MET | trial merge with main 28035ce00 (clean): **16,543 passed, 1 skipped, 14 xfailed** (token kept); ruff, format, `check_imports`, `check_records` (9,276 files) clean |

## Minor

1. **The registration must pin exactly these bytes.** Edits that still parse but break the owner's terms (14 days
   instead of 21; `choose_width: forbidden`) pass all 1,578 tests that touch books, envelopes and playbooks. That is
   by design: D6's SHA-256 is the lock. So the D6 registration commit must name exactly
   `constitution` = `6d54094c32ae9737adf8c81433dc85b47cc7fb9562fb9aaa542c9a8c05d071c5` and
   `trade_envelope:b0-monthly-sc-v1` = `dfdc5a5447918aad710749b978b529f4f9e9924b3136d8141e160741c6323b7a`, and its judge
   checks those hashes against this verdict.
2. No story text or Claims for these two files (quality rules 1-6). They are data the owner approved, validated by
   D4's and D5's judged parsers, and broken edits are caught (my plants: a 22-day limit and an unknown status each fail
   a test). Accepted for two approved data files; put a line in D's story when it is next touched.

## Note (risk manager and red team, not a finding)

`b0-monthly-sc` is a measurement shadow. Its own file says P1 lost Rs 34,486 over 60 opportunities in 2019-23 and
"can never show an edge" [strong: research/2026-10-12-experiment-1/RESULTS.md]. Under Q11 Book 2 may now paper-trade
it, labelled "strategy not yet passed", with D2's one-open-trade limit. That is the owner's decision. Expect Book 2's
paper results on this envelope to be negative, and do not read them as evidence for or against the AI.

## Plants

4 planted on the merged tree: **2 caught** (a 22-day constitution; an unknown envelope status), **2 survived by
design** (a 14-day constitution; `choose_width: forbidden`), which D6's hash lock covers (minor 1).

## Addendum 1

**story/ai-books-terms-v1 @ 1a694643c (the approved files plus their D6 rows), judge F: PASS (1 minor). Lane 1.** It
supersedes the hashes in minor 1 above: the files changed one comment line each ("DRAFT" → "Approved by the owner on
25 Oct"), so their hashes changed; nothing else changed (`git diff 7d44b51e2 1a694643c -- book3 playbook`).

| Check | Result | My evidence |
|---|---|---|
| Each D6 hash = its file's hash | MET | `sha256sum`: constitution `645a383c23999837b21fef91e32802c5affeb4798fd662809d61df1e3f38b985`, envelope `94749b4ef1b117395362ff7b84521c3dc24cdf14ffe9876e6f5ce919d0034362`; the same in `journal/versions.csv` rows `book3_ai,1` (`constitution`) and `book2_hybrid,1` (`trade_envelope:b0-monthly-sc-v1`), and the same bytes at `registered_in_commit` 1f4f16ea7 |
| Nothing applies before 26 Oct | MET | both rows start 2026-10-26; `RegisteredComponents` takes only rows with `starts_on <= day` |
| `fno versions check` clean | MET | on the trial merge it lists both rows; a short commit ID planted is refused |
| Nothing trades | MET | the branch changes no code and no config; Book 2's and 3's trading code (F1t, F5, F6) is not on main; the D6 rows are read only by C4 (a Book 2/3 proposal), Book 1's version keeper (Book 1 only) and the scoreboard's file hash |
| A merge commit, never squash or rebase | CONFIRMED | `books/versions.py:74` counts a version only when both the row's commit and `registered_in_commit` are ancestors of the decision's commit; a squash or rebase gives 1f4f16ea7 and 1a694643c new IDs, so every Book 2/3 decision would be unscored. Merge with `git merge --no-ff` (or the PR's "Create a merge commit") |
| Content still = Q9, Q10 and 16 Oct | MET | as above (the body of judge 633) |

Gates on a trial merge with main ade79b9d7 (clean): **16,570 passed, 1 skipped, 13 xfailed** (token kept); ruff, format,
`check_imports`, `check_records` (9,293 files) clean.

**Minor.** No test compares a registered component's hash with its file. My plant editing one byte of the
constitution passed all 1,908 related tests; the envelope's hash typo was caught only by the append-only test, not by a
hash check. After merge, an edit to either file would pass CI and make C4 refuse every Book 2 or 3 trade ("no
constitution file matches the registered D6 component"): fail-closed, but silent to CI. Add a test that each active
D6 row's file components equal their files' SHA-256 (as A17f pins TWSE's file), in F1t or a follow-up.

**Plants (4):** the envelope's D6 hash typo (caught, append-only test); the row started 24 Oct (caught); a short
commit ID (refused by `versions check`, 4 failed and 28 errors); one constitution byte edited (**survived**, minor).
