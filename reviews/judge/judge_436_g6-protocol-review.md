# Judge 436: G6 piece 1c, the decision review's protocol text (story/g6-protocol-review at d8142f6c)

Judge B, 22 Oct 2026 (IST). Lane 1 (a rule document). Builder: R2/G7 (session_0185gR5DmoDh2zBAvgRU4CEB).
- Owner row: DESK_DECISIONS 280 (response 299, items 2 and 9).
- Number claimed with `tools/claim_number.py`.
- It shares no file with the switch-on (judge 435).

## Verdict: PASS (one wording note)

## Criteria

| Claim | Result | Evidence |
|---|---|---|
| Item 9, section 11 D | MET, note 1 | see "Section 11 D" below |
| Item 2, section 6 | MET | the table's result is advice, and the Innovation Lab decides what runs; `stop_rule.py` is unchanged |
| Judge 430 note 1 | MET | see "The share-cut test" below |
| A test pins item 9 and item 2 | MET | it asserts the old sentence is gone; my plant (14-22 -> 4-22) fails 2 tests |
| Line length | MET | no added line is over 120 characters |

### Section 11 D
- The measured r is about 62 for V6b and 87 for V6a. This matches judge 128 addendum 5 (61.53 and 86.55).
- "V6b needs about 14-22 years even if its full back-filled skill is real" matches judge 128 addendum 5: about 14
  years plainly, 16-22 under E+D.
- "V6a and V1 are effectively unreachable" matches the same addendum (V1's thresholds 1.1e-12; V6a under E+D).
- The r = 3 counts stay, now labelled "at the assumed r = 3".

### The share-cut test (judge 430 note 1)
- The text's "10%" is tied to `round(CRASH_SHARE * 100)`.
- "n = 130" is tied to the first n where `crash_dominated(13, n)` is False.
- My plants each fail 1 test: the text at 15%, the text at n = 125, and the code's `CRASH_SHARE` at 0.12.

## Gates (run by me on d8142f6c)

| Gate | Result |
|---|---|
| `pytest -q -n auto` | 8,944 passed, 17 xfailed |
| `ruff check fno tests tools` | clean |
| `ruff format --check` | 1,658 files formatted |
| `check_imports` | clean |

My first full run showed 7 failures. All were in crash-cut tests, and all came from my own plant: the same-size edit
of `CRASH_SHARE`, restored within one second, left stale bytecode. After clearing `__pycache__`, the clean tree passes
in full. This is recorded so no one reads those 7 as the branch's.

## Note

1. **The text gives V2's number as if it used the measured noise.** "With the measured noise: ... V2 needs 8-22
   years" is not quite the source. Judge 128 gives V2 8-22 years "even at r = 3-5", the assumed noise, so with the
   measured noise V2 needs longer. The conclusion ("no v4 member is provable in useful time") is unchanged and, if
   anything, stronger. Suggested words for the next text piece: "V2 needs 8-22 years even at the assumed r = 3-5".

## Addendum 1: b3a74979, `SlotFile` refuses a start on or before the freeze (number 436.1, claimed with `tools/claim_number.py`)

**PASS.** It closes judge 430's note 2, at the orchestrator's request. The new check is in
`fno/forecast_scoring/v4/slot_file.py`, after the `registered_on` rule: when the freeze day is known,
`start <= frozen` is refused with a named message.

`wiring._registry` passes `_frozen_on`, which is None before `FREEZE_v4.md` exists. `scoring._miss_start` keeps its
`max(...)` as a second guard. Both files are byte-checked v4 files, and this lands before the freeze, as it must.

### My plants (2 of 3 caught)
- `<=` -> `<`: fails 1 test (the freeze-day row).
- The check removed: fails 2 tests.
- The wiring drops `_frozen_on`: survived. This is the same untested-wiring point as judge 414 note 3: before the
  freeze both versions give None. The `_miss_start` clamp still guards the counting, so it is a note only.

### Gates (run by me on b3a74979, `__pycache__` cleared first)
| Gate | Result |
|---|---|
| `pytest -q -n auto` | 8,946 passed, 17 xfailed |
| `ruff check fno tests tools` | clean |
| `ruff format --check` | 1,658 files formatted |
| `check_imports` | clean |

The V2 wording note above stays open for the next text piece.

## Addendum 2: piece 1d, story/g6-slot-start at cbb382d1 (number 436.2, claimed with `tools/claim_number.py`)

**PASS.** The branch holds two commits on main 11ef1b23.

### 6ec1a10c, the freeze-day refusal
Its diff is byte-identical to b3a74979, which I passed in addendum 1. I compared every added and removed line. So
addendum 1's result applies unchanged.

### cbb382d1, the V2 wording
This closes this verdict's note. Section 11 D now reads "V2's 8-22 years above are at the assumed r = 3-5, so with
real noise it needs longer (its r is not measured: V2 has no primary baseline yet)":
- It matches judge 128 addendum 5.
- It matches response 287: V2's premium-adjusted primary waits for G7b part b.
- The "above" points to the paragraph's own E+D counts (396 / 1,099, about 8 / 22 years).

A text test pins the new sentence. My plant (the old "V2 needs 8-22 years") fails 1 test.

### Gates (run by me on cbb382d1)
| Gate | Result |
|---|---|
| `pytest -q -n auto` | 9,031 passed, 16 xfailed |
| `ruff check fno tests tools` | clean |
| `ruff format --check` | 1,687 files formatted |
| `check_imports` | clean |

No open items remain in judges 430 or 436.
