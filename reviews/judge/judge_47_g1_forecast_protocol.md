# Judge 47: story G1, forecast protocol and the 30-day ATM implied-volatility estimator

**Verdict: FAIL.** There is 1 should-fix finding (the freeze design) and 1 minor finding (process).
- **The numbers and code are right.** My hand values equal the builder's: IV30 14.4937, the holiday and muhurat
  window, both realised volatilities and the 6.18% return.
- **The freeze order is right.**
- **The multiplicity method** is named exactly (Holm, 5%, 45 comparisons, a moving-block bootstrap with L = 20 and
  B = 10,000, and seeds).

**What I judged**
- **Repository:** trading at 0dcedf8 (protocol f936156, freeze ef5b818).
- **Claims:** `reviews/claude/response_53_2026-10-13-g1-forecast-protocol.md`.
- **Story:** `docs/stories/G-forecasts.md`, G1.

## Checks run by the judge

```
$ python -m pytest -q tests/forecast tests/research/test_ledger_guard.py     48 passed
$ git merge-base --is-ancestor f936156 ef5b818                               order ok (12:56:34, then 12:57:44 UTC)
$ (full suite at 46fe709: 1215 passed; ruff and imports clean)
```

### Hand recomputations

**IV30, bracketed day** (d = 2 Mar 2026; expiries 18 Mar at 16 days and 15 Apr at 44 days):
- ATM IV of 18 Mar = (12% + 14%) / 2 = 13%; of 15 Apr = 15%.
- w1 = 0.13² × 16 = **0.2704**; w2 = 0.15² × 44 = **0.99**.
- w30 = 0.2704 + (0.99 − 0.2704) × (30 − 16) / (44 − 16) = 0.2704 + 0.3598 = **0.6302**.
- IV30 = √(0.6302 / 30) = 0.144937, so **14.4937 points**. **Equal.**

**IV30, not bracketed** (the 15 Apr put did not trade): 18 Mar alone (16 days, at least 7), so **13.0**, flagged.
**Equal.**

**A target window with a holiday and a muhurat session** (fixture holidays 26 Jan and 17 Feb, muhurat Sun 22 Feb;
d = Mon 2 Feb 2026), counted by hand:
- **d+10:** 3, 4, 5, 6, 9, 10, 11, 12, 13 and **16 Feb**.
- **d+20:** 18 Feb (17 Feb skipped), 19, 20, 23, 24, 25, 26, 27 Feb, 2 Mar and **3 Mar** (the 22 Feb muhurat
  session is skipped).
- **Realised volatilities:** next RV = √((19 × 0.0004 + 0.0016) / 20 × 252) = **34.0470**; trailing RV
  = 0.01 × √252 = **15.8745**.
- **Return:** the log change is 0.02 + 0.04 = 0.06, so e^0.06 − 1 = **6.18%**. Q2 (at least 3%) is yes, and Q3
  (34.05 > 15.87) is yes.

All equal the builder's.

## Criteria

| # | Criterion | Judge's evidence | Result |
|---|---|---|---|
| 1 | Every target equals hand-worked values, all five questions, a holiday in the window | My counts and values above; `test_targets.py` passes | MET |
| 2 | IV30 equals a hand computation on two days (bracketed and not) | Above | MET |
| 3 | Protocol frozen; its commit precedes the first scored forecast (G4 checks) | The order is checked. `require_frozen_before` is tested (an earlier commit, an edited file and a wrong version are all refused). No forecast exists. | MET (see finding 1 on what is frozen) |
| 4 | The multiplicity method is named with its exact procedure before scoring | Protocol section 8: 45 comparisons in a fixed order, p = 1 for comparisons not yet possible, a centred bootstrap p-value, Holm's step-down at 5%, only Brier tested, at least 40 paired dates. `comparisons.py` matches. | MET |

## Finding 1 (should fix): the freeze locks shared library files for the life of the forecasts

- **What is frozen:** `FREEZE.md` checks the bytes of B1's `implied_vol.py`, `volatility_features.py` and
  `close_series.py`, and `test_freeze.py` fails on any edit.
- **Why that is wrong here:**
  - Forecasts are scored continuously for months (the first review is at 6 months).
  - Those three files are shared by F1, live F1 (B7), C2's stress engine and IV30.
  - Any refactor or unrelated fix in them then turns CI red and forces a new forecast-protocol version, even when no
    forecast number changes.
  - That couples three stories to one test and pushes builders either to stop improving the library or to cut
    protocol versions for no reason. It breaks the owner's mandatory "design for change, loose coupling" rule.
- **Why the experiment 1 freeze is different:** it hashes engine files for a short window, from the freeze to the
  challenge run. This freeze has no end.
- **What must be protected is behaviour, not bytes.** Expected (reasoning only on the form):
  - Check the bytes of `fno/forecast/*` and `PROTOCOL.md` only.
  - Commit a **golden file** of the estimator's outputs, with its SHA-256 in the freeze record: IV30 (value, flag and
    expiries) and trailing RV20 for every panel day 2019 to the freeze day. Both are known at the forecast date, not
    outcomes, so they can be computed before scoring. Add the hand fixtures' values.
  - A test recomputes them with the current library and requires equality (for example within 1e-12).
- **The result:** a refactor that keeps every number passes, and a change to any number fails and needs version 2.
  The library files can then be recorded but unchecked, as the calendar and the panel manifest are.
- **One caveat to write into the protocol:** a panel rebuild that changes a past day's data (A11 revisions) would
  also move the golden values. That is correct, because the inputs changed, and it must name the A11 revision that
  explains it.

## Minor 1 (process): frozen before any outside review

**Did the G1 story allow a freeze at this stage? Yes, by its text.**
- It asks for `PROTOCOL.md` "frozen (FREEZE record with commit and hashes, like B5)" and has no review step.
- "Like B5" refers to the record's form.
- The owner's "freeze only after ChatGPT agrees" (DESK_DECISIONS, 13 Oct) is written for experiment 1's protocol.

**But it is premature against the project's practice.**
- CLAUDE.md requires every proposal to go to ChatGPT through the repository, and experiment 1's protocol needed both
  sides' agreement before freezing.
- The builder's own "choices, please challenge them" (baselines, book 1 rule, muhurat exclusion, tie rule) are
  exactly what a review would change.

**The harm is limited.**
- No forecast exists, so a version 2 before the first scored forecast loses nothing.
- What it costs is the meaning of "frozen": version 1 is effectively a draft with hashes.

**Expected:**
- Send the protocol to ChatGPT now, and record in the ledger that version 1 is superseded if anything changes.
- The orchestrator or owner should decide whether G-protocols need agreement before freezing, as experiment 1 does,
  and write that into G1's story.
- **My recommendation (reasoning only):** yes. The protocol's whole purpose is that its choices cannot be tuned
  later, so they should be challenged before they are fixed.

## Notes (agreed, or for others)

- **Muhurat sessions** are not trading days for the targets (as B1), and special weekend sessions count.
  **Cross-project inconsistency:** W11's 33 screener counts the 21 Oct 2025 muhurat session among its "250
  sessions" (judge 42 addendum 2). Both are internally consistent. A one-line project convention would prevent
  confusion.
- **IV30's flag rate** (13%, mostly 2019-20 where the next month's ATM leg did not trade) is measured and stated.
- **Book 1 = the mean of two baselines** is fixed in the protocol, as G3 requires.

## Addendum: round 2 (769fac7, then 3bd5b37 after ChatGPT review 28)

**Both findings: ACCEPTED.**
- **Why G1 is still not PASS:** criterion 3 ("the protocol is frozen") is deliberately not met now. Version 1 was put
  back to draft so ChatGPT could review it first.
- **What completes G1:** ChatGPT's agreement to the applied review-28 changes, then the freeze. I re-check the
  freeze record and its commit order at that point. That is a short check.

**Finding 1 (freeze behaviour, not library bytes): ACCEPTED (my own checks).**
- **Built after the 30 Mar 2021 change:** `research/forecasts/golden_iv30_rv20.csv` (1,921 days, 2019 to 12 Oct
  2026) was added in 769fac7, which contains B7's 0364b22. So the golden values already include the 30 Mar 2021 closes.
- **Hand check across the filled session:** trailing RV20 on 12 Apr 2021, over the 21 closes from 10 Mar to 12 Apr
  (30 Mar included), is **21.813638387166204** by my own script on NSE's index closes. That equals the golden value to
  the last digit. 30 Mar itself has no row, which is right: it has no option rows, so no IV30.
- **The behaviour freeze bites:** I changed the library's year length (252 to 252.0001): `tests/forecast` gives
  **2 failed**.
- **A refactor passes:** a harmless edit to the same file gives **44 passed**. Shared files can change; numbers
  cannot.

**Minor (process): ACCEPTED.**
- `PROTOCOL.md` is marked "draft version 1 … Not frozen: … frozen only after ChatGPT has agreed it" (orchestrator
  decision after judge 47).
- `FREEZE.md` is gone.
- Ledger trials 32-36 now carry no protocol commit, filled in at the freeze.
- ChatGPT's review 28 exists, and its two changes are answered in response 60 and applied:
  - Q5 is void on flagged IV30 days;
  - the primary family is 10 tests (Book 2 and Book 3 against Book 1).
- I did not re-judge the statistics of the new 10-test family this round, to save cost. I will check it with the
  freeze, together with the Holm procedure, against the frozen text.

**Checks:** `tests/forecast` 44 passed; my plants above reverted, and `git status` is clean.

## Addendum 2: the freeze (protocol cf489e4, freeze fd95a42)

**The freeze's content: MET. But the ancestry rule does NOT hold in CI. That is 1 should-fix, and `main`'s CI is red
because of it.**

**Content (my checks):**
- **The freeze order:** `cf489e4` is an ancestor of `fd95a42`.
- **The 10 checked files:** every SHA-256 in `FREEZE.md`'s checked table equals the file at HEAD. They are the
  protocol, the golden file and `fno/forecast/*`. **No `fno/research_engine/` file is byte-checked**: the three B1
  files are recorded only, "behaviour locked by the golden values".
- **The golden contract includes the IV30 flag:** 1,921 days, 258 flagged, 1 without IV30. My round-2 plants showed a
  value change fails and a refactor passes.
- **Review 28's two changes are in the frozen text:**
  - PROTOCOL.md line 49: Q5 is "void when IV30(d) is flagged or missing";
  - lines 67-69: flagged days are kept only as a descriptive sensitivity;
  - the confirmatory family is 10 tests (line 5 and section 8).
- **The ledger:** trials 32-36 carry `protocol_commit` cf489e4.

**Should fix: the ancestry check fails in CI's shallow clone.**
- `.github/workflows/checks.yml` uses `actions/checkout@v4` with no `fetch-depth`, so only one commit is present.
  `require_frozen_before` then cannot find cf489e4 in the history.
- **Evidence:** run 38427592927 (238, on 6917ff9, the first commit containing the freeze) failed:
  `test_the_repository_protocol_is_frozen_before_this_commit_and_unchanged` with "NotFrozen: the freeze is not in the
  history of 6917ff96b3" (1 failed, 1,398 passed).
- The last green run, 237 on 1f82a27, does not contain the freeze. Run 239 (15defa6) has the same checkout, so it
  will fail the same way.
- **Expected:**
  - `fetch-depth: 0` on the checkout in `checks.yml`, and in every workflow that runs, or later will run, G4's
    `require_frozen_before` (G4's scoring job included).
  - So that a missing history can never pass by accident: on a shallow clone the check should say "history not
    available" (it fails today, which is the safe side; keep it failing, never skip).
- **Why it matters:** "the freeze precedes the first scored forecast" is only proven where the full history is
  present. CI is that place.

## Addendum 3: protocol version 2 (1b57cb3, not frozen), against review 29's eight changes (response 63)

**PASS: ready to freeze.** All eight accepted changes are written into `research/forecasts/PROTOCOL_v2.md` and built.
Version 1 is untouched.

| # | Review 29 change (response 63) | Where in v2 | Judge's check |
|---|---|---|---|
| 1 | Each same-day field observed at or before 15:00:00 IST, else missing, so "no forecast" | §1 per-field cutoff; `live_pack.py` `CUTOFF = 15:00:00`, `_observed_by` on each quote's `response_received_at` | **My plant** (accept one second late) fails 3 tests |
| 2 | India VIX from a named, timestamped source; d−1's VIX never used | §1: A4's `india_vix` with NSE's `india_vix_time` (B7's levels), both bounds at or before 15:00 | Read in `live_pack.py:143` |
| 3 | Live-mid IV30: two-sided ATM quotes, observed by 15:00, same expiry, interpolation and flag rules | §2 | Read |
| 4 | Closes through d−1 as a hard gate (`history_stale`) | §3 (and `iv30_history_stale` for Q5's base rate) | Read |
| 5 | The pack hash covers provenance, coverage date, snapshot attempt and values | §1: values with source and time; snapshot dataset, id and the SHA-256 of its CSV and meta; closes' source, last day and SHA-256; calendar SHA-256; IV30; canonical JSON hashed into `pack_sha256` | Read |
| 6 | Its own mode, `live_1500_proxy`, never mixed with history | §1 and §4 (`input_mode`) | Read |
| 7 | A dedicated input-quality field | `schema_v2.py`: v1's 7 columns, then `input_mode`, `iv30_status`, `generated_at` | Read |
| 8 | Generated by 15:15 IST and receipt-locked by the Actions run; the Git push is transport only | §5: `on_time` at 15:15:00, and a `receipt:` line (pack and records SHA-256, generated_at) in the run log | Read; the workflow records nothing until `FREEZE_v2.md` exists |

**Checks:**
- `tests/forecast` 78 passed.
- **Version 1 untouched:** `git diff fd95a42..HEAD` over v1's 10 frozen files lists **0 files**.
- **No 2019-2023 rows** of the golden or back-fill files were opened (holdout rule).

**One thing to watch at the first live day (reasoning only):** whether NSE's VIX stamp and the snapshot's
`response_received_at` really fall at or before 15:00:00. A4's capture starts at 14:55, and B7's minor 3 found late
captures possible. v2 correctly turns a late field into "no forecast", so a late capture shows up as a run of empty
days, not as wrong numbers.

## Addendum 4: the version 2 freeze (protocol ab2e811, freeze 0fc5723)

**PASS.** The freeze checks the v2 code itself, which is judge 53's lesson applied.

**The freeze:**
- **Order:** `ab2e811` precedes `0fc5723`.
- **The 34 byte-checked files** in `FREEZE_v2.md` all equal their SHA-256 at HEAD (my script). They are the protocol,
  every `fno/forecast/*.py` (the live pack, history gates, closes source, v2 schema, capture, freeze check, command
  line and the v1 code used), `tools/forecast_live_golden.py`, and every v2 golden input and output.
- **The check runs first:** `python -m fno forecast capture` calls `require_version_frozen` before anything is
  written.
- **Shared libraries** (B1's Black-76, B7's live ATM rule, the panel and quote readers) are recorded, not
  byte-checked. The workflow covers them by behaviour: `forecast-capture.yml` runs `python tools/forecast_live_golden.py`
  **before** the capture, so a drift in any of them stops the day's run.
- **CI:** both workflows use `fetch-depth: 0`.

**The first live run's gates (response 62 addendum) are as stated:**

| Gate | Status |
|---|---|
| Freeze in history | Met |
| Both golden cases reproduce | Met (the run recomputes them) |
| Closes through d−1 | `warmup_closes.csv` holds 13 Oct (e38eabd) |
| Q5's panel IV30 within 21 trading days | Met until about 10 Nov 2026, after which the panel must be rebuilt |
| A canonical A4 snapshot committed by 15:13 IST, with quotes, futures and VIX at or before 15:00:00 | **Unproven.** No snapshot has ever been committed on `main`. |

**Honest risk (reasoning only):**
- The snapshot window is tight. A4 captures from 14:55, retries until 15:10, and must commit and push before the
  capture's 15:13 pull limit.
- A slow capture or a late push gives "no forecast" for the day, which is by design and safe.
- So expect some empty days at first. Count them in the first week's report.
- From 15 Oct on, the closes gate also needs O6's daily close job to have appended d−1 before the 14:00 start.
