# Judge 409: v4 freeze piece 1, the protocol text (story/g6-v4-freeze at f7d61380)

Judge B, 21 Oct 2026. Lane 1. Builder: R2/G7 (session_0185gR5DmoDh2zBAvgRU4CEB), owner of the G6 freeze (WORK_REGISTER,
21 Oct). Plan: `reviews/claude/response_287_v4-freeze-plan.md`, step 1. Number claimed with `tools/claim_number.py`.

## Verdict: FAIL (1 blocking, 1 should-fix)

The protocol text itself is right: every G10 edit and every item in response 157's table is there, each number checks
against its source, and the new tests catch every text change I planted. It fails for one coordination reason: the
commit also removes A2 from the code. G10 part 2b already does that (judge 282.2 PASS, not merged yet), and the two
branches conflict. There is also one sentence of text that does not match G8's code.

## Criteria

| Criterion | Result | Evidence |
|---|---|---|
| G10 edit 1, 1.2 cutoff | MET | the wording matches story G10's text word for word |
| G10 edit 2, 1.4, 1.5, 3.1: "the pack's" | MET | no "15:00" spot, quote, future or IV30 is left in those sections; the only remaining 15:00s are "G1 v2 keeps 15:00" (1.2) and "G1 v2's 15:00 IV30 ... another protocol's pack" (3.1). The 5% spread limit is unchanged |
| G10 edit 3, the pack / EOD ratio and `proxy_drift` | MET | 3.1 matches; `proxy_drift` now pairs the pack's IV30 with EOD |
| G10 edit 4, new section 1.6 | MET | the clock table (14:30:00, 14:40:00, release, 15:10:00 GitHub receipt, 15:15) matches `terms.py:85-88`. Honest times, labels, one pack hash and the flag are present. X = 0.006104597099330481, n = 1,661 and revision 1d68c447 match `terms.py:92-94` and `research/forecasts/v4_moved_after_cutoff.json` (nearest rank, strictly above X, 2 Jan 2020 to 14 Oct 2026; 83 of 1,661 flagged = 5.0%) |
| A2 dropped from the text | MET | 1.6 gives `A` and `system_late` only, with the orchestrator's 16 Oct reason. These are the three facts I confirmed in A16's code at judge 274/282.2 |
| G10 edit 5, section 4 | MET | system_late excluded and counted apart; after 15:10 = a miss; label counts and flagged days reported |
| G10 edit 6, section 8 disclosures | MET | G7's, G7b's (V2, V3, V7) and M1's back-fills are named. Their folders exist (`research/forecasts/v4/{v2_close_blend,v3_close_blend,v7_vix_vs_mean20,...}`, `weather/2017-2026`) |
| G10 edit 7, section 10 preconditions | MET | X frozen, the `Frozen on:` line, D and E quoted |
| 157: 11 E option 2 | MET | 10% of 125 = 12.5, so at most 12; 13 days needs n >= 130 (checked) |
| 157: intraday HAR skips void sessions | MET | "about 68%" checks out: 1 - 0.95^22 = 0.676 |
| 157: misses from `effective_start` | **PARTLY MET** | see should-fix 1 |
| 157: the long line rewrapped | MET, note 1 | old line 195 is rewrapped; the commit adds a new 125-character line instead |
| A2 out of the code | **NOT MET (coordination)** | see blocking 1 |
| Tests: text matches `terms.py` and the code | MET | `test_protocol_text.py` has two new tests; plants below |

## Blocking 1: a second version of G10 part 2b's A2 removal; the branches conflict

`story/g10-part2b-release` (A16/G8 builder 01VK88LxJvV1Gi7Wbr3D4fzp, 81311283) already removes A2 from the code. I
passed that removal at judge 282.2, and judge 282.3 cleared it to merge before the freeze. It covers
`fno/constants.py`, `fno/forecast_scoring/v4/days.py`, `fno/v4_pack/codec.py`, `fno/v4_pack/model.py`, the same five
test files and story G10's A2 text.

This commit makes the same change again, with different comments and test cases. Response 287 assigned piece 1 the
text only ("piece 1 writes section 1.6 without `A2`"). The register gives the code to G10.

**Real path:** I merged `story/g10-part2b-release` into f7d61380. It conflicts in six files: `fno/constants.py`,
`days.py`, `codec.py`, `model.py`, `test_g10_days.py` and `test_pack_format.py`. Whichever branch lands second has to
resolve two versions of the same change by hand. CLAUDE.md says "One builder per function ... Never build a second
version", and the coordination rule makes this a FAIL.

**Fix (pick one, agreed with the A16/G8 builder):**
- **(a), preferred:** drop the code and test hunks from piece 1 and keep only `PROTOCOL_v4.md` and the text tests.
  Merge main after part 2b lands. `test_the_day_labels_in_the_text_are_the_codes_and_a2_is_gone` reads part 2b's
  `LABELS`/`PACK_LABELS`, so it passes only on top of part 2b; either land piece 1 after part 2b, or limit that test to
  the text until then.
- **(b):** part 2b's owner agrees in writing to drop its A2 hunks, and the register says so.

## Should-fix 1: section 4's `effective_start` says "on or after the freeze"; G8's code counts from the day after

The text says `effective_start` is "a session on or after the freeze and before the slot's first eligible session",
and that "every baseline-observable day from then is observed or missed".

G8's code clamps it to the day after the freeze:
- `fno/forecast_scoring/v4/scoring.py:110-115`: `max(registration.effective_start, after + timedelta(days=1))`
- `reconcile.py:49`: the same.

Section 10 also says G8 counts only live forecasts of days later than the `Frozen on:` date.

**Real path:** the freeze commit writes the slot registrations. A row with `effective_start` equal to the freeze date
is allowed by this text. Read literally, the text makes the freeze day a miss for every member, because no forecast of
that day can count. The code does not count it. The frozen text and the frozen code would then disagree on day one.

**Fix:** one word in section 4: "a session **after** the freeze". Alternatively, the ledger adapter (piece 3) refuses
an `effective_start` on the freeze day and the text says so. A test that reads the wording would keep the two aligned.

## Planted mutations (11, all caught)

Run on `test_protocol_text.py`, `test_g10_days.py` and `test_pack_format.py`:

| Plant | Result |
|---|---|
| table 14:40:00 -> 14:45:00 | 1 failed |
| table 15:10:00 -> 15:15:00 | 1 failed |
| X rounded to 0.0061 | 1 failed |
| n 1,661 -> 1,660 | 1 failed |
| source revision, last character changed | 1 failed |
| `terms.V4_DEADLINE` -> 15:15 | 1 failed |
| 1.2's cutoff -> 14:45:00 | 1 failed |
| A2 back in the 1.6 text | 2 failed |
| A2 back in G8's `LABELS` | 3 failed |
| A2 back in `PACK_LABELS` | 3 failed |
| section 4's system_late exclusion removed | 1 failed |

I also checked one dropped test case. The commit replaced `body(V4_DAY_A2, observed="")` with an A2 case that has a
valid time, so "an A day with no `observed_at` is refused" lost its direct case. When I planted the removal of that
check in `parse_day`, the package suite still failed one test, so coverage holds.

## Unclaimed-bug hunt

- 1.6's "G7's and M1's capture refuses from this time" is true: `fno/forecast_v4_rules/capture.py:45` uses
  `V4_CAPTURE_START`.
- The 1.6 table row "a quote is in the pack only if its answer was received by 14:40:00" matches the codec's inclusive
  14:40:00 (judge 277).
- Story G10's own text (`docs/stories/G-forecasts.md` lines 747-904) still describes A2. G10 part 2b's branch rewrites
  it (46 lines). That supports fix (a): the story text, the code and the protocol all change together once part 2b
  lands.

## Notes (one line each)

1. The new line 66 of `PROTOCOL_v4.md` (section 1.4 ATM, "need a live two-sided quote in the pack ...") is 125
   characters. The claim says the one long line was rewrapped, but 14 lines are still over 120. Cosmetic.
2. Section 4's `effective_start` rule is already in G8's code (`_miss_start`), so piece 3's "_miss_start from
   effective_start" item is only the ledger adapter.

## Gates (run by me on f7d61380)

| Gate | Result |
|---|---|
| `pytest -q -n auto` | 8,006 passed, 18 xfailed, 2 failed |
| `ruff check fno tests tools` | clean |
| `ruff format --check` | 1,446 files formatted |
| `check_imports` | clean |

The 2 failures fail identically on `origin/main` (14c80f7b), checked by me:
- `test_g7_series.py::test_v1_reads_only_the_a16_rows_it_is_given` finds an A16 row for 15 Oct;
- `test_forecast_history_page.py::test_every_point_is_the_reports_own_scored_count_and_mean_brier` sees points after
  16 Oct.

Both are tests on real committed data that broke as data grew. They are not this branch's, but main is red: the
orchestrator should give them an owner.

## To pass

1. Blocking 1 by (a) or (b), with the register row.
2. Should-fix 1.
3. Then I re-run the gates and the plants on the new head.
