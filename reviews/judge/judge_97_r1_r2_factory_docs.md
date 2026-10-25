# Judge 97: R1 factory documents and R2 registration: `story/r1-factory-docs` 2ea0ded (lane 1, response 98)

**What I did:**
- read every changed file in full: `FACTORY_RULES.md`, `ideas/TEMPLATE.md`, `ideas/R2.md`, `DATA_SPEND.md`, R2's
  `PROTOCOL.md`, `FREEZE.md` and `README.md`, the ledger rows, the test change and response 98;
- checked the commit order and the protocol hash;
- checked the design v2 text the documents implement (`03` §3.1, REPLAN slice A items 4-5, the R1 and R2 stories);
- ran the full gates on the branch tip; checked that it merges cleanly with `main`.

## Gates

On a worktree at 2ea0ded (full history, not shallow), with the Slack token unset: **3161 passed**; `ruff check` clean;
`ruff format --check` clean (705 files); `check_imports` clean. `git merge-tree origin/main 2ea0ded` merges cleanly,
and `main` has no code, test, ledger or config change since the branch base 07113cb. Largest new file 190 lines.

## Claims vs reality

| Claim | Status | Evidence |
|---|---|---|
| Protocol committed first, then trial 53 and FREEZE | MET | 93a19c3 adds `PROTOCOL.md` (parent 07113cb); 1d76c75 adds ledger row 53 and `FREEZE.md` naming 93a19c3; the protocol is unchanged from 93a19c3 to 2ea0ded (empty diff); its SHA-256 is `89947b4c...e40a6b`, as `FREEZE.md` says |
| No stock-option data read | MET as a statement (some evidence) | Only the builder's word, as response 98 says. Nothing in the branch contains stock-option numbers; the manifests named are metadata (URLs, dates, hashes). I can check no more than that |
| Cost wall: expected net > 0 on a conservative bound, 2x a warning | MET in `FACTORY_RULES.md` §2 | Rule, definition of "conservative bound", worse-of tail rate, measured pads, screened-out ideas kept in the count, 2x only `thin margin` |
| Cumulative Holm per question, p = 1 for unfinished | MET | §3 rules 3-5. Statistically sound: unfinished or stopped hypotheses enter at p = 1, so they sort last and only enlarge m; Holm stays valid and conservative |
| One test changed, stricter | MET | `test_ledger_guard` now expects 53 rows and asserts trial 53 is prospective and names 93a19c3; nothing loosened |
| R2 covers the story | PARTLY | Point-in-time F&O list (both FUTSTK and OPTSTK listed on the entry session), lot values, near strikes, cheapest defined-risk structures against Rs 10,000, one Groww snapshot, physical settlement (expiry at least 5 sessions after the reaction session, second-month pushes counted), effective clusters with within-week correlation (Kish count), early failure by stages, no P&L on outcomes: all present. **Bid/ask depth**: the snapshot records best quantities (§6.2), but no report line names them; see follow-up 1 |
| Ledger `hypothesis = no` | MET | `ledger.py`: the flag counts hypothesis tests; a feasibility study is not one |
| Merge must keep 93a19c3 | Noted | The guard refuses the row otherwise; I check it at the merge |

Checks of the numbers: n = (1.645 x 0.60 / 0.05)^2 = 389.6, so 390 units, 130 a year over 3 years: correct as written.
The legacy lot-size derivation can be validated as claimed: the two manifests overlap from 1 Jan 2024 (new format) to
5 Jul 2024 (last legacy file).

## Must-fix

**1. R2's 5% edge is not a "conservative bound" under R1's own rule, and the two documents contradict each other on
day one.** `FACTORY_RULES.md` §2 says an idea with no source for its gross edge is screened out ("no stated edge"), and
that the conservative bound is the lower end the source supports ("for arithmetic: the least favourable input"). R2's
card says the gross edge is "Unknown; the study uses a conservative bound of 5% (reasoning only)", and the protocol
says published studies "disagree on its sign and size". The least favourable value of that evidence is zero or below,
not +5%. So, read literally, R1 screens R2 out, and R2's YES would be described as "positive expected net on a
conservative bound", which overstates what it tests. What R2 actually tests is a **cost hurdle**: are round-trip costs
below 5% of the structure's price (with e\* printed per structure). That is a sensible feasibility question; it needs
the right name.

Fix (no protocol change, so no new trial): in `FACTORY_RULES.md` §2, add the case of a **cost-hurdle feasibility
study**: a study that measures costs and fit may use an assumed edge, labelled "assumed hurdle, reasoning only, not a
conservative bound"; it prints the break-even edge; its YES never counts as G1 pass for any later idea, which still
needs a sourced edge. In `research/ideas/R2.md`, call the 5% an assumed hurdle, not a conservative bound, and say the
results report will use that name (the protocol's wording stays frozen; the report states the difference, as §11
already allows).

## Follow-ups (not blocking)

1. **Depth.** The story asks R2 to report bid/ask depth. The snapshot records best quantities; the results report
   should print them per bucket, descriptively (no decision role). State this in the script's freeze commit.
2. **"130 clusters a year".** The annualisation (clusters in the decision window divided by its length in years, or a
   per-calendar-year minimum) is not written. `study.py` must state it, and its hash goes into `FREEZE.md` before the
   run; I will check it then.
3. **Power.** n = (z x SD / net)^2 gives 50% power at the assumed effect. At 80% power the R2 count would be
   (1.645 + 0.842)^2 x 144 = 891 units, about 297 a year. The same formula is in design v2's G3 and in
   `FACTORY_RULES.md` G3, so it is a design-level point, not this branch's: a later lane-1 change should add the power
   term. I passed design v2's G3 row without catching this; that miss is mine.
4. **Nit:** `DATA_SPEND.md` cites "section 6 of the R2 protocol" for the within-week correlation; it is section 7.
5. **Survivorship of sectors and ban days** are listed as limits (§10). Fine as limits; the report should count events
   in the `unknown` sector.

## Project rules

Lane 1 (rule documents, ledger, frozen protocol, a test). No `fno/` code. No secrets, emails or model names. Files
under 350 lines. Labels on every threshold.

**Verdict: FAIL for 2ea0dedf5471e9ee3b256d8b2d8bb4431505f7b1**, on must-fix 1 only. Everything else passes; a re-check
needs only `FACTORY_RULES.md` §2 and `research/ideas/R2.md`. The protocol must not change (its hash stays
`89947b4c...e40a6b`), and the merge must be a merge commit.

## Addendum 1 (15 Oct 2026): bec0e33d1932b8af50748f7728aceb783e7581ac (2ea0ded..bec0e33)

One commit (parent 2ea0ded), three research documents, nothing else.

| Item | Status | Evidence |
|---|---|---|
| Must-fix 1 | MET | `FACTORY_RULES.md` §2 now has the cost-hurdle feasibility case. An unknown edge's least favourable value is at most zero, so the idea itself cannot pass G1. The assumed edge is an **assumed hurdle** (reasoning only, never a conservative bound), and an earlier frozen protocol's phrase is read that way. e\* is printed. A YES never counts as a G1 pass for a later idea. `ideas/R2.md` uses "assumed hurdle" in its edge, screen and sample-plan rows |
| Protocol unchanged, no new trial | MET | `PROTOCOL.md` SHA-256 is still `89947b4c...e40a6b`; `ledger.csv` is unchanged |
| Follow-up 4 (section number) | MET | `DATA_SPEND.md` now cites section 7 |
| Follow-up 2 (annualisation) | Open, as agreed | Waits for `study.py`; I check it when its hash goes into `FREEZE.md` |

The gates of judge 97 stand: the change touches no code, test or ledger file.

**Verdict: PASS for bec0e33d1932b8af50748f7728aceb783e7581ac.** Merge it as a merge commit so that 93a19c3 stays in
`main`'s history. After the merge I check the recomputed merge, the ledger guard and CI.

## Addendum 2 (15 Oct 2026): merge check, R1/R2 merged to main as 3856f90

- **Merge is exact.** 3856f90's parents are 78e9723 (main) and bec0e33 (the passed tip). Recomputing the merge with
  `git merge-tree --write-tree 78e9723 bec0e33` gives a tree identical to 3856f90's (empty diff).
- **Branch files arrived unchanged.** `git diff bec0e33 3856f90` is empty on every file the branch touched.
- **The freeze holds.** 93a19c3 is an ancestor of 3856f90, so it is in history. `PROTOCOL.md` hashes to
  `89947b4c...e40a6b` on `main`. `tests/research` (the ledger guard included) passes on `main`: 22 passed.
- **No unjudged change since.** Nothing was pushed to `main` after 3856f90 at the time of checking.
- **CI.** The parent 78e9723 is green. The run on 3856f90 was in progress; its result is in my report.

**Verdict: merge check PASS.**
