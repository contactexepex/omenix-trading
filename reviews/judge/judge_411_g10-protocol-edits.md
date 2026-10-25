# Judge 411: G10's seven PROTOCOL_v4 edits (story/g10-protocol-edits at 77877f37)

Judge B, 21 Oct 2026. Lane 1, because this is a rule document before the freeze. The builder is the G10 builder
(session_01VK88LxJvV1Gi7Wbr3D4fzp). Number claimed with `tools/claim_number.py`. Coordination: R2/G7 withdrew its
duplicate (freeze piece 1, f7d61380, judge 409) in favour of this branch, and the A2 code drop stays in G10 part 2b. One
version each, so there is no duplicate.

## Verdict: FAIL (1 should-fix)

The text is right. All seven edits match story G10's list, and every number matches its source. The one finding is in
the new test. It does not pin the 15:10 deadline, which is the drift that G10's criterion 1 asks it to catch.

## Criteria

| Criterion | Result | Evidence |
|---|---|---|
| Edit 1, the 1.2 cutoff | MET | story G10's words; G1 v2 keeps 15:00 |
| Edit 2, 1.4, 1.5 and 3.1 read "the pack's" | MET | no 15:00 spot, quote, future or IV30 is left; the 5% limit is unchanged |
| Edit 3, the pack / EOD ratio and `proxy_drift` | MET | as written in the story |
| Edit 4, section 1.6 | MET | see "Section 1.6 against the code" below |
| A2 dropped | MET | `A` and `system_late` only, with the 16 Oct reason. These are the three facts I confirmed in A16's code (judges 274 and 282.2). "No release record at all" counts as `system_late` (judge 282.2, (b2)'s catch-up) |
| Edit 5, section 4 | MET | system_late is excluded and counted apart; received after 15:10:00 is a miss; every report gives label counts and flagged days |
| Edit 6, section 8 | MET | the back-fill uses closes, live uses the pack's values, the cohorts are never pooled |
| Edit 7, section 10 | MET | X frozen (value, n, revision, convention) and `Frozen on:` in `FREEZE_v4.md` |
| Criterion 1: the test checks 14:30, 14:40 and 15:10 against `terms.py` | **PARTLY MET** | 14:30 and 14:40 are pinned; 15:10 is not (should-fix 1) |

### Section 1.6 against the code
- The table's times equal `terms.py:85-88`: 14:30, 14:40, 15:10 and 15:15.
- X = 0.006104597099330481, n = 1,661 and revision 1d68c447 equal `terms.py:92-94` and
  `research/forecasts/v4_moved_after_cutoff.json`. The JSON records quantile 0.95, nearest rank, strictly above X, and
  83 of 1,661 history days flagged (5.0%).
- "A capture whose clock was not checked ok before and after is not used" is true. A4e's `CaptureLog` checks the clock
  before the first request and after the last (`fno/quotes/capture_log.py:3`, `clock_status` takes the worst result),
  and (b2)'s `PackBuilder` requires `clock_ok`.
- "An incomplete capture retries" is true: `recorder.py` retries every 60 s inside the window.
- "One pack, one hash ... another or an empty hash is refused; a forecaster that commits before the pack exists names
  none" matches the guard keyed by forecaster (`PACK_READERS`, judge 277).

## Should-fix 1: the deadline in `terms.py` can drift from the text and the test stays green

The new test checks each time like this:

```python
for moment in (V4_CAPTURE_START, V4_PACK_WINDOW_END, V4_DEADLINE, V4_COMMON_SNAPSHOT):
    assert f"| {moment:%H:%M}" in TEXT
```

`"| 15:15"` is already in the text, in the common-snapshot row.

**Plant:** `V4_DEADLINE = time(15, 15)` in `terms.py`. All 19 tests pass. The text still says the deadline is 15:10:00,
while the code would accept commitments up to 15:15.

The literal `"after 15:10:00" in TEXT` check does not help. It pins the text, not the code.

**Why this is a normal path, not an imagined one:** these times have moved by owner and orchestrator decisions before.
v2's deadline is 15:15, and G10 itself moved 15:00 to 14:30-14:40. G10's criterion 1 exists so that such a change
cannot leave the frozen text and `terms.py` apart. The deadline decides which commitments count, which makes it a
scoring rule.

**Fix:** pin the whole table cell, for example `f"| {moment:%H:%M:%S} |"` for the three to-the-second rows and
`"| 15:15 |"` for the snapshot. Each plant above should then fail. R2/G7's withdrawn test caught this plant by matching
the table's own row.

## Planted mutations (14; 11 caught)

| Plant | Result |
|---|---|
| table 14:30:00 -> 14:35:00 | caught |
| table 14:40:00 -> 14:45:00 | caught |
| table 15:10:00 -> 15:15:00 | caught |
| table 15:15 -> 15:20 | caught |
| X rounded to 0.0061 | caught |
| n 1,661 -> 1,660 | caught |
| source revision, last character changed | caught |
| `terms.V4_PACK_WINDOW_END` -> 14:45 | caught |
| section 4's system_late exclusion removed | caught |
| an `A2` label put back into 1.6 | caught |
| `> X` -> `>= X` | caught |
| **`terms.V4_DEADLINE` -> 15:15** | **survived** (should-fix 1) |
| "95th percentile" -> "90th" | survived (note 1) |
| `ceil(0.95 n)` -> `ceil(0.90 n)` | survived (note 1) |

## Notes (one line each)

1. The quantile convention is not tested against the JSON's `"quantile": 0.95`. Section 10 freezes it, so one assertion
   would cover it. This is a text-only edit risk, so it is a note, not a finding.
2. Four new prose lines run over 120 characters (diff lines in 1.4's question and ATM bullet, 1.5's frozen bullet, and
   3.1's raw implied). This is the same kind of issue as judge 156's note 2. Cosmetic.
3. Until G10 part 2b lands, main's code still accepts an `A2` day file (`days.LABELS`, `PACK_LABELS`), which this text
   now forbids. Nothing on main writes one, because no release code is merged, so there is no running path. Part 2b
   has to land before the freeze (judge 282.3 and judge 409's order).
4. Section 4's miss start ("from the forecaster's first forecast") is not touched here. That is response 157's item,
   paused with the v4 freeze. When it comes, use "after the freeze", as judge 409 should-fix 1 says.

## Gates (run by me on 77877f37)

| Gate | Result |
|---|---|
| `pytest -q -n auto` | 8,099 passed, 18 xfailed, 2 failed |
| `ruff check fno tests tools` | clean |
| `ruff format --check` | 1,458 files formatted |
| `check_imports` | clean |

The 2 failures are main's known red tests: `test_g7_series` (V1 rows) and `test_forecast_history_page`. Both reproduce
on `origin/main` (judge 409), and the main steward owns them (story/main-green).

## To pass

Should-fix 1, plus my re-run of the deadline plant and the gates.

## Addendum 1: story/g10-protocol-edits at 73394828, the should-fix (number 411.1, claimed with `tools/claim_number.py`)

**PASS.** The text is unchanged since 77877f37; only the test changed.

### The fix
`test_the_days_clock_and_x_in_the_text_match_the_code` now pins each row of section 1.6's table, with its own label,
to its own constant:
- `| {V4_CAPTURE_START:%H:%M:%S} | The pack's capture starts`
- `| {V4_PACK_WINDOW_END:%H:%M:%S} | **The pack's cutoff:**`
- `| {V4_DEADLINE:%H:%M:%S} | **One deadline:**`
- `| {V4_COMMON_SNAPSHOT:%H:%M} | **Common snapshot**`

The failure message names any row that is missing.

### My plants (6 of 6 caught, 1 failed each)
In `terms.py`:
- `V4_DEADLINE` -> 15:15 (the survivor in judge 411)
- `V4_CAPTURE_START` -> 14:35
- `V4_PACK_WINDOW_END` -> 14:45
- `V4_COMMON_SNAPSHOT` -> 15:20

In the text:
- the deadline row -> 15:15
- the snapshot row -> 15:10

### Gates (run by me on 73394828, main merged at a4f2b09a)
| Gate | Result |
|---|---|
| `pytest -q -n auto` | 8,134 passed, 18 xfailed, 2 failed |
| `ruff check fno tests tools` | clean |
| `ruff format --check` | 1,465 files formatted |
| `check_imports` | clean |

The 2 failures are main's known red tests, owned by the main steward. Main now carries G10 part 2b's A2 drop (d4e2a454),
so note 3 of the verdict above no longer applies: the code and the text both say A and `system_late` only.

### Still notes, not findings
- The quantile convention is untested (note 1).
- Four new lines run over 120 characters (note 2).

## Addendum 2: story/g10-protocol-edits at a831e2ce, the notes (number 411.2, claimed with `tools/claim_number.py`)

**PASS stands; this is the head to merge.** One commit sits on top of 73394828, and it addresses both open notes.

### Note 2: the long lines
- Section 1.4's question and its ATM bullet, section 1.5's frozen bullet and section 3.1's raw implied are rewrapped.
- The words are unchanged. I compared the word sequence of the two versions of `PROTOCOL_v4.md` and it is identical.
- None of the added lines is over 120 characters. The 1.6 table rows stay long, because a table row cannot wrap.

### Note 1: the quantile convention
- The test now reads `v4_moved_after_cutoff.json` and asserts that quantile is 0.95 and x equals
  `terms.MOVED_AFTER_CUTOFF_X`.
- It also checks that the JSON's convention is "nearest rank" and that the text says "nearest-rank 95th percentile (the
  `ceil(0.95 n)`-th".

### My plants (4 of 4 caught)
- "95th" -> "90th" in the text
- `ceil(0.95 n)` -> `ceil(0.90 n)` in the text
- the JSON's quantile -> 0.9
- the 411 deadline plant, `V4_DEADLINE` -> 15:15, re-run

### Gates (run by me on a831e2ce)
| Gate | Result |
|---|---|
| `pytest -q -n auto` | 8,134 passed, 18 xfailed, 2 failed |
| `ruff check fno tests tools` | clean |
| `ruff format --check` | 1,465 files formatted |
| `check_imports` | clean |

The 2 failures are main's known red tests (`test_g7_series`, `test_forecast_history_page`); I confirmed them by name.
