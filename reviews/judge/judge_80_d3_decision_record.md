# Judge 80: story D3, the decision record (branch, before merge)

Date: 14 Oct 2026 (UTC). Branch `story/d3-decision-record` at 6346d76 (10ca844 merged with main). Claims:
`reviews/claude/response_81_d3-decision-record.md`. Story: `docs/stories/D-playbook-decisions.md` D3.

## Verdict: FAIL, two small must-fixes (a test gap on criterion 2, and the replay's code version)

The record, the atomic store, idempotence, timeliness and the D6 link work. My independent replays of three runs give
no difference, and the replay does catch an edited risk verdict and a dropped alternative. But no test holds those
two comparisons: my plants switching them off pass all 27 tests. And a replay under today's code cannot reproduce an
old record after D2 changes, nor does it say that it ran under different code.

## Gates (my runs, `python -B`, caches cleared)

- Full suite: 2,492 passed.
- Ruff, format (550 files) and imports: clean.
- `git merge-tree` with `main`: clean.

## The story's own check: three replays

With the builder's fixtures I ran three days (two versions with a slot taken, an unproven version, a plain day) and
replayed each through D2's real evaluator. All three gave **no difference**. Then:
- I replaced one record's `risk` with something else: the replay names "`sc-a-v1_2026-11-27.json`: risk differs";
- I dropped one entry of the day record's `alternatives`: the replay names "`no_trade.json`: alternatives differs".

So the code compares them.

## My plants (`tests/decisions`, 27 tests)

| Plant | Result |
|---|---|
| The replay skips `alternatives` | **not caught** |
| The replay skips `risk` | **not caught** |
| A record's `alternatives` leave out the shadow outcomes | **not caught** |
| `common_pack_sha256` may be null for every book | caught |
| The duplicate-run check off | caught |
| The inputs' SHA-256 not checked on replay | caught |
| An empty `served` allowed | caught |

## Per criterion

| # | Criterion | Result |
|---|---|---|
| 1 | Every evaluated opportunity has a record, no-trade included | MET (tests; the day's `no_trade` record) |
| 2 | A replay reproduces the decision, the rejected alternatives and every risk and validity reason | **PARTLY**: the code does it (my replays), but its comparison of `risk` and `alternatives` is untested, and the replay runs today's code (must-fix 2) |
| 3 | A crash leaves the whole record or none | MET: the run is written into a hidden folder and renamed; the killed-writer subprocess test |
| 4 | Never edited; a correction is a new record linked to the old | MET (`records.sha256`, `edited`, the `corrects` field and test) |
| 5 | Committed after the execution snapshot: late, never filled | MET (`timeliness` and `require_on_time`, tests). Committer time is the committing machine's clock; acceptable while only our own jobs commit (information) |
| 6 | Schema versioned; every three-book field present, null only where the book has none | MET, with the stated nulls ruled below |

## Must-fix

1. **Tests for criterion 2's named parts:** a stored record whose `risk`, whose `validity` and whose `alternatives`
   are edited each make the replay name that field. Also a test that every record's `alternatives` are exactly the
   other outcomes (shadow included).
2. **The replay names the code it ran with (the orchestrator's point 1). My ruling:** the replay must never present a
   comparison under different decision code as a reproduction.
   - Before comparing, it checks that the running code's commit equals `header.code_commit`. Simplest: the tree of
     `fno/` and `config.yaml` at that commit equals the working one.
   - If not, it refuses with a named reason ("recorded at <commit>; replay at that commit").
   - Offer the way to do it: a replay in a `git worktree` of `header.code_commit`, as the A13 and G1 checks already
     do.
   - Comparing under today's code, "would today's D2 decide the same?", is a useful second tool, but it must say so
     in its output and never pass as criterion 2.

   One test for the refusal.

## The orchestrator's other points

2. **`served` and D6: met.** Book 1's `served` is the playbook digest of `approved_on(day)` and the config hash,
   computed by the run. D6 compares every component, and the builder's test with `config` missing gives `unscored`.
   - **Consequence to plan for (reasoning only):** every approval, pause or retirement changes Book 1's playbook
     digest. Any change of tradable versions, including E6's automatic pause, leaves Book 1's later decisions
     unscored until a new D6 version is registered.
   - That matches design 12.6 (a strategy change starts a new segment). But the approval and pause flows (D1 status
     changes, E6) must register the new version, or Book 1 stops being scored silently. Make it an E3 or D6
     follow-up.
3. **Timeliness:** there is no 15:12 constant. 15:12 and 15:15 are only test values. The rule is relative to the
   **actual start of that day's execution snapshot**, which E3 passes in. That is better than a fixed time. No
   change needed.
4. **The stated nulls:**
   - **`validity.c4` null:** accepted. C4 does not exist; it is a link that C4 fills.
   - **Availability times by the common pack's hash:** accepted. The pack holds every item with its source and time,
     and `common_pack_sha256` is required for Book 1 (my plant making it nullable is caught). That is DRY and
     verifiable.
   - **`expected.p10_rs` and `p90_rs` null: accepted only for now.** The story asks for the tested P&L
     distribution. D1's format has no percentiles, yet the research results behind each version have per-cycle P&L,
     so they can be frozen in the playbook file.
   - **Condition:** before the first version is approved to paper, D1's format gains p10 and p90 from its frozen
     test results, and D3 fills them. No version is approved today (`playbook/registry.csv` has no rows).
5. **Atomicity: met** (criterion 3).

## Project rules

- New modules in `fno/playbook/`, wired in `fno/playbook/wiring.py`.
- Canonical JSON from E2's `pack_items` (DRY).
- No orders, secrets or Slack.

## Addendum 1 (round 2, branch 60ebd59 = fix 9658348 merged with main): PASS

**Must-fix 1: met.** Editing `risk`, `validity`, `alternatives` or `decision` on a contested day now makes the replay
name that field. A test pins `alternatives` to every other outcome, book and shadow. My three earlier plants are now
caught: the replay skipping `alternatives`, the replay skipping `risk`, and alternatives dropping shadow outcomes.

**Must-fix 2: met.**
- `replay` asks a `CodeTree` whether the working tree's `fno/` and `config.yaml` equal `header.code_commit`, with
  uncommitted and untracked files included (`git diff --quiet <commit> -- fno config.yaml` plus `ls-files --others`).
- If they differ, it raises `ReplayRefused`, naming the commit and `git worktree add <dir> <commit>`.
- `todays_code=True` runs anyway, with a first line "NOTE: compared with today's code ... not a reproduction".
- On the real repository (my probe): `matches(HEAD)` is True; `matches(HEAD~1)` is False (`fno/` differs); with an
  untracked `fno/zz_probe.py`, `matches(HEAD)` is False.

**My plants (`python -B`, caches cleared; `tests/decisions`, 34 tests): all 11 caught.** That includes:
- the code check off;
- untracked files ignored;
- uncommitted changes ignored;
- the today's-code note dropped;
- the seven from round 1.

**Gates:**
- full suite: 2,506 passed;
- ruff and imports: clean;
- `git merge-tree` with `main`: clean.

**Follow-ups recorded by the builder, which I hold it to:**
- (a) the approval and pause flows register a new D6 version, else Book 1 goes unscored;
- (b) D1 freezes p10 and p90 from the test results **before the first approval to paper**.

**Verdict: PASS for 60ebd59.**

## Addendum 2 (merge check, f314254)

**MET.** f314254 has parents on `main` and 60ebd59 (the passed tip). It equals my recomputed merge of the two, with no
difference at all. CI `checks` is green on f314254 (run 38515859763).
