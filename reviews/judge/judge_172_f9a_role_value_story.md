# Judge 172: story F9a, role-value scoring code (story text, quality rule 1; judge F)

**Commit judged:** `642c3f73` on `story/f9-role-value`, the head when I judged. The orchestrator named 3832311e; this
commit is the next one. The claims are in response 162, which the builder is renumbering to 166. Builder:
session_01SFDjjZx7JYziM3jqJytG2z. Lane 1 (a new story; scoring code that S1 hashes).

A renumber-only commit does not change this verdict. Any change of text does.

**Verdict: FAIL (text).** 2 blocking, 4 should fix, 2 minor.

What is sound:
- The split: F9a scores records now, and F9b fires the shadow sessions in slice E.
- Valuing both actions through S3's `standard_unit.py`, read only, not stored nets: correct. A stored net misses the
  time exit and E7 settlement.
- The rotation, the 30-changed minimum, the review gate and the control-role counts from C4's log.

## Blocking

1. **A unit's allocated cost has no source in normal running (strong evidence).**
   - Roles run as sub-agents inside the book's one session (`docs/stories/F-ai-layer.md:98`, F2: "each role runs as a
     separate sub-agent").
   - F8 writes one usage row per (session, day) with one `role_or_bundle` (`F-ai-layer.md:370`;
     `fno/budget/usage_ledger.py:25,48`).
   - So the `(books_and_roles, book, unit)` share F9a reads never gets minutes. `allocate` then has no entry for it,
     and the text does not say whether that is zero or unknown.
   - S1 (`role_value_minimum_sample`) and design 3.1 ("after the role's own running cost") need that cost in the
     interval. A zero would make every role look free and push verdicts toward "earns its cost" in frozen code.
   - Fix (the builder's choice, kept simple):
     - (a) name who records each unit's own minutes (F2 or F9b, one usage row per sub-agent), or
     - (b) a declared split of the book session's allocated share across the units consulted that day.
   - In both cases, a unit with no measured share is "unknown", with no verdict, and a criterion tests it.
2. **No gap list (quality rule 2).** The story maps no design requirement to a criterion or to "out with a reason".
   Requirements in neither list:
   - design 3.1, "abstentions and rejected trades count": a shadow or real no-trade is never said to be a decision
     valued at 0, or to count in "changed";
   - design 3.1, "lower risk can justify lower profit": not scored and not ruled out;
   - design 3.1, "joint tests where roles interact": only declared bundles are covered;
   - design 10 and §254, "roles added one at a time": out of F9a? Say so.

   Each needs a criterion or an "out" line with its reason.

## Should fix

1. **Holm is not defined, and contradicts criterion 7.**
   - The orchestrator relays that the owner decided Holm across a book's units. The text still says "if the owner
     chooses it".
   - S3's revision 2 already defines Holm on bootstrap one-sided p-values: sorted ascending, the i-th of m passes
     while p < 0.05/(m − i + 1) (`S-scoreboards.md` on `story/s3-scoreboard-a`, lines 158-165).
   - F9a must use the same definition, and the same code once S3 merges (DRY).
   - It must also say which claims enter Holm. "Drop" (upper end < 0) and "earns" (lower end > 0) are opposite
     one-sided claims, and a unit can make at most one.
   - With Holm, the verdict comes from adjusted p-values, so criterion 7's fixed 5th and 95th percentiles are only the
     printed interval, not the rule. Say so.
2. **The provisional constants cannot be pinned "against S1's text" yet.** S1 states none of 5th and 95th, cost per
   consulted day, or blocks of 20 opportunities. It says "blocks of 20 ablation days of that role", and nothing on the
   cost denominator. Criterion 7's test can only read what S1 contains. State that these values enter S1's text, with
   its owner's agreement, before the F9a code round, or pin them in F9a and list them as S1 changes.
3. **The third bootstrap.** Response 162, claim 3, rejects reuse because `uncertainty.py` is a ratio. S3 revision 2
   now adds a bootstrap with p-values for paired daily differences. Reuse it if it takes a plain series; if not, give
   the reason in the text. The engineering rules forbid duplication.
4. **The source of the review dates.** "Only on a `review_dates` date": S1's item is a rule (the last session of the
   sixth month after the common start, then every 3 months), and no code computes it today. `fno/scorecard/review.py`
   reads a playbook plan's own dates. Name the function or input F9a uses, and test it.

## Minor

1. Criterion 1 checks that the real and shadow snapshot ids are equal. Also require that both equal the day's
   execution snapshot in the run log (the standard unit's input). Otherwise an equal but wrong snapshot passes.
2. Rotation: S1 says "a day the book is unavailable does not advance"; F9a says "a day without a real decision".
   Say that a no-trade decision is a real decision and advances the cycle.

## Checked and correct
- S1's text (`research/evaluation/PROTOCOL.md:249-282`) matches the rotation, the minimum of 30 differing
  opportunities, the drop / earns / inconclusive rule, "owner decides", and seed and resamples 20261014 / 10,000.
- F8's shares are keyed `(purpose, book, role_or_bundle)` (`fno/budget/allocation.py:21`): true. See blocking 1 for
  why that key is empty for roles.
- C4's failure log, one row per failed check with `opportunity_id`: as claimed.
- C3 keeps no per-book refusal log: accepted as a known limit.
- `standard_unit.py` does not exist yet (S3 is still story text). The code round waits for S3's merge, as stated.
- Work register: the row is added, with no overlap. `fno/scoreboard/` is untouched.
- Engineering rules: about six small modules planned (reasoning only until built).

## Addendum 1: revision at 4d61fb8c (story text; response 166)

**Verdict: PASS (text), with one required delta before code.** This is the orchestrator's go of 15 Oct. The branch
diff against main is docs only: the F9 section, response 166, its README row and the work-register row.

| Finding | Fix | Judge's check | Result |
|---|---|---|---|
| B1 unit cost source | A declared split. The book's daily allocated cost is F8's month allocation of its `books_and_roles` shares, times the day's minutes over the month's minutes (F8's `allocate`, imported). It is split equally across the consulted units, to the paisa, with F8's remainder rule. The decider takes none, so it is labelled "upper bound". A missing usage row or a missing plan cost makes it "unknown", with no verdict and no Holm entry (criterion 5; split-sums test) | Honest and simple; works with F8 as built (one row per session). Measured sub-agent minutes later become a new protocol version (Known limits) | Fixed |
| B2 gap list | A table covering design 3.1, 10 and 13.6 and S1. Abstentions are criterion 9; joint tests via bundles, pairwise out with a reason; risk out with a reason; one at a time out with a reason | Every requirement I listed is mapped, in or out with a reason | Fixed (see the delta below for risk) |
| SF1 Holm | S3 revision 2's definition and code (`S-scoreboards.md:158-165` on `story/s3-scoreboard-a`, read): one-sided bootstrap p-values, step-down 0.05/(m − i + 1). Two claims per unit, "earns" (share of means ≤ 0) and "drop" (the negated series), all 2m claims in one list. The verdict follows the passing claim; the 5/95 interval is printed only (criteria 7, 11) | Consistent. The orchestrator accepted the owner's "stricter only" answer (Q7) | Fixed |
| SF2 constants | S1 pending edit 3, in register row "S1 text" (read at 4d61fb8c, line 38). They enter S1's text before the code round; criterion 11's test pins both | Pinnable once S1's edit lands; the order is stated in Depends | Fixed |
| SF3 third bootstrap | S3's resampler is reused with a risk column of 1, exactly S3's own paired construction (`S-scoreboards.md:155-157`). Claim 3 is withdrawn | No second bootstrap | Fixed |
| SF4 review dates | `review_dates(common_start, calendar, through)` in `fno/evaluation/review_dates.py`, with S1's text owner's agreement (register row F9a, no file overlap with RM1's `gate.py`). Holiday month-end test (criterion 4). The common start is a CLI input until S1 fixes it | Codes only S1's current scheduled-review rule, as stated | Fixed |
| m1 snapshot ids | Both ids must equal the run log's execution snapshot, through S3's `CommittedRuns.snapshot_ids` (criterion 1) | | Fixed |
| m2 no-trade advances | Stated in scope and criterion 1 | | Fixed |

**Required delta before the code round (owner, 15 Oct, `DESK_DECISIONS` row added in d6628c90: "Money only, risk
shown").** The verdict stays money only, which the text already has. The decision also says a role's effect on worst
month and maximum loss is **printed beside the verdict and never decides**. The text and the gap-list row say "lower
risk: out of the verdict" but print nothing.
- Add to the report: per unit, the with-minus-without difference in worst month and in maximum loss.
- Add one criterion: the figures are shown, and changing them never changes the verdict.
- Turn the gap-list row into "in (shown, never deciding), owner 15 Oct".

The orchestrator allowed this as a small delta. I check it in the code review; no new text verdict is needed if it
is only that.

Gates: docs only, and the builder's run of the same code tree is 5,992 passed. I did not re-run the suite for a
text-only change.

**Delta checked (36f6b0fa, docs only; the diff from 4d61fb8c touches only the F9 section and response 166):** the
owner's "money only, risk shown" is now in.
- **Risk shown:** per unit, the worst calendar month of paired differences and the mean one-lot maximum-loss
  difference over changed opportunities, the latter from S3's code, imported.
- **Never deciding:** neither figure enters Holm or the verdict, and "drop proposed" is printed as a proposal.
- **Tests:** new criterion 12 tests that changing only these figures leaves the verdicts and p-values unchanged.
- **Gap list:** the "lower risk" row now points to criterion 12.

The required delta is met. **F9a text: PASS at 36f6b0fa.** Code may start once S1's pending edit 3 and S3's three
files are on main.
