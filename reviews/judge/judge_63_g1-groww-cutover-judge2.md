# Judge 63: G1 Groww cutover plan (text, lane 1), judge #2

Frozen SHA `af42b79` (branch `story/G1-groww-cutover`): `docs/GROWW_CUTOVER.md` (new, 90 lines) and one link line in
`docs/RUN_LOCATIONS.md`. Reviewed `git diff origin/main af42b79`. No Groww call was made (market hours).

**Gates (text only):** the doc-reading tests passed (79); `check_numbers` is clean; both files are under 500 lines.

## Checked and correct

- **Commands:** `--help` exits 0 for `quotes record` (with `--window` and `--source`), `intraday backfill`, `intraday run`
  (`--until`), `intraday rv`, `intraday heartbeat-check`, `preopen record` and `groww-check`.
- **Setup files:** `ops/routine_setup.sh --groww` uses `requirements-groww.lock` with hashes.
- **Read-only client:** `ReadOnlyGroww` is at `intraday/read_only.py:24`.
- **Secrets:** the four `GROWW_*` names are in `fno/shared/constants.py:14-17`. Names only, no values.
- **Sign-in code:** one sign-in per process and token day, a 06:00 IST token day, back-off of 5 then 10 minutes
  (`FIRST_WAIT * 2 ** (failures-1)`), `TRIES_A_DAY = 3`, and the first failure of each token day alerted once.
  All match `providers/groww_sign_in.py:22-23,33,52,90,98`.
- **Tally arithmetic:**
  - 21+10+1+4+2 = 38 and 7+5+1+4+2 = 19, both correct.
  - 19/150 = 12.7% and 38/150 = 25.3%, so the doc's "13 to 25%" is right.
  - 38 x 3 = 114, which is 76% of 150, with a margin of 36.
  - The docstring's 38 ("a normal day: about 38") does include the reruns, as the doc says.
- **Other sources:**
  - The candle routine is at about 21:40 IST, and the one-time 2020 backfill is by hand (`GROWW_CANDLE_ROUTINE.md:42,76`).
  - The A4/A4b and A16 deferrals, the 78 slot files and A4c from 19 Oct all match `DATA_USE_MAP.md:14-17`.
  - Pre-open runs 08:36 to 09:12 IST (`preopen/cli.py:1,9`).
  - R1d2 is parked (`R1d...md:120-123`).
- **Hard lines:** the market-hours wording matches CLAUDE.md, including that a failed scheduled command may be re-run
  only as the same command. The doc holds no secret values and nothing private.
- **The link line:** the `RUN_LOCATIONS.md` addition is one line plus a link, with no duplication.

## Findings

1. **F1 (must fix): wrong command and window for the index recorders.** Row 1 of the section 3 table gives
   `python -m fno quotes record` for both NIFTY (A4, A4b) and the BANKNIFTY, FINNIFTY and MIDCPNIFTY slots (A4c). It
   also says "the recorders run in the 15:01-15:13 window". In the code:
   - A4c is `python -m fno quotes record-indices`, and its window is 15:01-15:13 IST (`quotes/cli.py:46`,
     `quotes/indices.py:2`).
   - `quotes record` is NIFTY's command, and its window is 14:55-15:10 IST (`quotes/cli.py:37`, `config.yaml:13`).

   An owner who follows this cutover table points the A4c routine at the NIFTY command, so the three index chains are
   not recorded. Fix: give the two commands and the two windows separately.
2. **F2 (must fix): the list of single-provider roots is misquoted, and its evidence grade contradicts itself.**
   - Line 58 says it follows `R1d-groww-and-the-rest.md`. That list (R1d lines 48-50) names nine sites: `cli.py:87`,
     `providers/groww_check.py:15`, `intraday/wiring.py:63`, `intraday/feed_wiring.py:51`,
     `intraday/backfill_wiring.py:46`, `quotes/index_wiring.py:20`, `quotes/window_wiring.py:28`, `composition.py:53`
     and `preopen/wiring.py:80`.
   - The doc lists seven. It leaves out `cli.py`, `intraday/feed_wiring.py` and `composition.py`, and it adds
     `providers/__init__.py`, which is the factory `get_provider` (line 10), not a composition root. I confirmed each
     site by grep at this SHA.
   - Line 58 says a named test for this is "planned, not built". Line 88 grades the single-provider roots as "strong
     (code read and tested)".

   Fix: copy R1d's list, or link to it instead of restating it (the one-owner rule). Grade this point "some evidence
   (code read; the test is not built)".
3. **F3 (must fix): the restart-storm margin is given only for the best case.** Line 81 says "about 110 extra
   processes" break the cap. That holds only when every sign-in succeeds: 150 - 38 = 112 sign-ins left. A storm is
   most likely when sign-ins are failing, and then each process can spend up to 3 tries.
   - On a day when everything is failing (114 tries used), 36 tries are left, which is about **12** extra processes.
   - On a normal day (38 used), restarted processes that fail spend 3 tries each: (150 - 38) / 3, about **37**
     extra processes.

   The doc's own worst case leaves a margin of about 12 processes, not 110. That changes how strongly "no ledger
   needed" can be stated. I agree with the conclusion for the *planned* load (reasoning only). The restart-storm
   sentence must give the range: about 12 to 110 extra processes, depending on whether sign-ins are failing.
4. **F4 (should fix): the 150-a-day source is not in this repository.** The docstring cites
   `research/school/probes/2026-10-22-p0-1-groww-chain.md`, and that file is not in this repository; `git log --all`
   has no history for it either. `R1-resilience.md:87` and CLAUDE.md state 150 a day without a source. Lines 55 and
   89 should say the probe note is not in this repository and that the figure is the owner's, also in CLAUDE.md.

## Not blocking

- Section 5 restates the sign-in behaviour that `R1d-groww-and-the-rest.md:22` and the `groww_sign_in.py` docstring
  already describe. The tally is new, and this doc owning it is fine. The behaviour itself could be one line and a
  link to R1d.
- "Pre-open reads Groww for the 09:15 value through `preopen/wiring.py`": `preopen/wiring.py:80` builds a
  `GrowwProvider`, but I did not trace which value it reads.

**Verdict: FAIL** (round 1, `af42b79`). F1 to F3 are text fixes. F1 would point a routine at the wrong command.

## Addendum 1: round 2 on `15e1dad`

`git diff af42b79 15e1dad -- docs` changes only `docs/GROWW_CUTOVER.md`, which is now 97 lines. Doc-reading tests:
79 passed. `check_numbers` is clean.

- **F1 fixed.**
  - NIFTY: `quotes record`, 14:55-15:10.
  - A4c: `quotes record-indices`, 15:01-15:13 (`--help` exits 0), with a warning that `quotes record` records NIFTY
    only.
  - New row for v4: `quotes record --window v4`, 14:32-14:40. This matches `config.yaml:12,15`, and v4 has its own
    `quote-snapshots-v4` dataset.
- **F2 fixed.** The nine sites now match R1d item 4 verbatim, and the claim is graded *some evidence* (its test is not
  built), consistently at lines 58 and 88.
- **F3 fixed.** I re-derived each margin; they are correct:
  - 36 / 3 = 12;
  - (150 - 38) / 3 = 37.3;
  - (150 - 19) / 3 = 43.7;
  - 150 - 38 = 112, which the doc rounds to about 110.

  The failing case now comes first.
- **F4 fixed.** The doc says the probe note is not in this repository, and that the 150 is the owner's figure
  (CLAUDE.md:39).

**Verdict: PASS** (`15e1dad`).
