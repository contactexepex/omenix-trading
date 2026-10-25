# Judge 513: git before writes (story/git-before-writes)

**Scope:** story/git-before-writes at 68fe6d49 (builder session_013xqaNTCbSBytKgqpfaYFqZ), the diff against main.
Story and Claims: `docs/stories/O-git-before-writes.md`. Lane 1 (factory registration and freeze, the ledger, playbook
status: evaluation records), one judge: Judge J (session_01Qg4Gxun1NvGRrtS9C68Dc1). Round 1 of 2.

**Verdict: FAIL.** 1 should-fix: one of R1's owner's two recovery conditions is untested. 1 minor. The design is
right.

## Criteria
| # | Claim | Result | Evidence |
|---|---|---|---|
| 1 | Any failed git call leaves nothing written | MET | `git_failures.py` fails each git call in turn (register 4, freeze 18, run 1, status change 8). Plants caught: register's ledger write before its gate check; freeze's ledger write before its gate check; `research run` reading head after the results; the status change's `load()` after the writes; the append-only check moved to write time |
| 2 | Reruns complete a half state; anything else is refused | PARTLY | Committed and wrong-kind half registers are refused, as are a freeze at a commit outside the history and a freeze with a changed card (4 plants caught). Not caught: finding 1 |
| - | A rerun after a complete register or freeze (files not yet committed) | MET | My probe: register is refused ("already has a gate-log row"), freeze is refused ("its last gate is G4"), so no duplicate gate row |
| 3 | `mark_run` takes the commit read before the writes | MET | The plant that reads head inside `mark_run` is caught. Its only callers are `research_cli` and the ledger-guard test |
| - | Behaviour change: a hand-set `protocol_commit` completes | MET as stated | Only when it is in HEAD's history and the card is unchanged since (both plants caught). R1's owner agreed |
| - | Gates (my run, a separate worktree) | MET | pytest -n auto: 12,095 passed, 16 xfailed. ruff check and format, `check_imports` and `check_records` are clean |

## Findings
1. **Should-fix: R1's owner's field condition for completing a half register is untested.**
   - The condition: the row must match the card's experiment, description and hypothesis.
   - Removing `_require_same` from `_stopped_half_done` passes all 825 tests in `tests/{research_engine,factory,
     playbook,research}`.
   - With it removed, a half register whose card was edited before the rerun completes. The `idea` row then pairs
     with a ledger row whose experiment, description or hypothesis no longer matches the card. The hypothesis flag
     decides whether the trial is a test, so this is an evaluation record.
   - Expected: one test, with a half register, the card's hypothesis (or description) changed, and the rerun refused
     naming the field.

**Minor:**
- (a) Removing the `self.rows()` validity check from `GateLog.prepare` survives. The check was already in the old
  `append` path through `require_append_only`, so this is not new code; a test that a malformed earlier row refuses a
  new append would pin it.

## Plants
12 planted, 10 caught. The survivors are finding 1 and minor (a).

## Notes
- A completed half freeze logs G4 at the frozen commit, which may be older than G3's gate row. R1's owner accepted
  this under their two conditions; the card is unchanged since that commit, so the protocol is the one frozen.
- The builder's earlier 1 failure in 12,080 was on another head (0d206848), with a second full run going at the same
  time. My clean run on 68fe6d49 has 0 failed.
- (e), the desk's `write_no_decision`, is out of scope by the orchestrator's ruling (the desk freeze).

## Addendum 1

**Scope:** round 2 of 2, story/git-before-writes at 3cd347c7 (latest main merged). Since 68fe6d49 the branch's own
changes are two tests and the story's round-2 lines; no code under `fno/factory`, `fno/research_engine` or
`fno/playbook` changed.

**Verdict: PASS.** No findings left.

- **Should-fix 1, accepted (fixed).** `test_a_half_registration_that_no_longer_matches_its_card_is_refused_naming_the_field`
  runs with a changed description and with a changed hypothesis. My plant removing `_require_same` from
  `_stopped_half_done` is now caught.
- **Minor (a), accepted (fixed).** `test_a_malformed_earlier_row_refuses_a_new_append` covers it. My plant dropping
  `self.rows()` from `GateLog.prepare` is now caught.
- **Gates (my run, a separate worktree):** pytest -n auto: 13,415 passed, 16 xfailed. ruff check and format,
  `check_imports` and `check_records` are clean.
