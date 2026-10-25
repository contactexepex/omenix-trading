# Judge 108: A16 15-minute quote recorder: story text at `story/a16-groww-15min` db26fd7 (lane 1, quality rule 1)

Judge D. Scope: `docs/stories/A16-intraday-quote-recorder.md` and response 108 (part 1) at
db26fd7a329fc6605438db839ac8a66ad1634db3, parent `main` 32262d4. Text only; no code is pushed.

**What I did:**
- read the story and claims in full;
- checked them against design v2 (REPLAN_new_stories A16, 2.1, 4.2, 4.4, 5.2, 6.5, 6.6), the owner's 15 Oct rows (host
  "1 - A", Groww terms, "6 A" raw quotes Drive only) and `fno/providers/groww.py`;
- checked every criterion for good, bad, boundary and empty cases.

I cannot repeat step 0 myself. This session has no Groww key, and `requirements-groww.txt` does not install here
(`clint`/`args` wheels fail). So step 0's numbers rest on the builder's word: some evidence.

## What is right

- **The RV definition matches design 5.2.**
  - 26 marks, k = 0..25, and 25 intraday squared log returns.
  - An overnight return from the previous recorded session's 15:30 to 09:15, with muhurat skipped.
  - Units: a daily variance, not annualised, with `vol_pct = 100 sqrt(RV)` (0.0001 is 1.00%, correct).
  - Void, never interpolated. The 120 s staleness limit is design 5.2's 2 minutes. The 5% void flag is there.
  - It is a versioned strategy (`rv-quote-15m-v1`), labelled `quote_snapshot`.
- **Gaps are never filled.** `missed` is never taken later, every due slot gets one ledger row, and the 120 s boundary
  is tested at, 1 s under and 1 s over.
- **Raw data stays private.** Raw quotes go only to the owner's Drive, with first-version-wins and A11 revisions. The
  repository holds no price, bid, ask or level (criterion 11, owner "6 A").
- **Clock contract (4.4) in full:** UTC with offset, the source time kept apart, skew checks against GitHub and Slack,
  5 s WARNING, `clock_unchecked`, `source_ahead_of_host`.
- **Alerts and heartbeat:** one alert per streak, at most one an hour, with the 60-minute boundary stated; a heartbeat
  check at 30 minutes (4.2).
- **Gap list complete.** Every requirement of the A16 paragraph and of 4.4 maps to a criterion or to a stated
  out-of-scope reason.
- **The candle finding is useful and honest.** Index 15-minute candles exist from 1 Jan 2020, with holes listed. A
  candle-close RV is a different measure, so A16b is rightly separate.
- **The doubts are stated:** the routine is untested, the checker is not independent, the install fails.

## Should-fix

**1. The freshness rule, on which criteria 5 and 6 depend, is not yet defined.** "Groww's own timestamp for the index,
rule fixed by the in-session check": the index `last_trade_time` was empty pre-market, and the in-session check is
"to be added". Until it is written, the `stale` status and the void rule cannot be judged or tested. Fix: run the
in-session check, write the exact source-time rule into Definitions, and write what happens if Groww gives no index
time (the builder's candidate is the latest 1-minute candle's time). Re-check that commit before code.

**2. "A level identical to the previous slot is stale" biases the target.**
- NIFTY prices in steps of 0.05, and a 15-minute move is often 20-30 points. So two equal levels 15 minutes apart are
  rare, but real: at roughly 0.1% per interval, about 2% of sessions would have one (reasoning only; the rate depends
  on volatility).
- Treating equality as stale voids exactly the calmest intervals. That removes zero returns, biases the kept RV
  sessions upward, and spends the 5% void budget on calm days.
- Fix: decide staleness by the source time (should-fix 1). Report a repeated value as a flag, without voiding, unless
  its source time is also old.

**3. The trigger design is not yet shown to be reliable enough for the target, and its prompt cannot run as written.**
- **The arithmetic.** Seven hourly fires at HH:10 each record their own hour, and nothing overlaps. One fire that
  starts more than about 7 minutes late, or fails, loses 1-4 marks. Any lost mark voids that session's RV
  (`RV_intraday` needs all 25 intervals). With 7 fires a day, design 5.2's 5% void ceiling needs each fire to fail less
  than about 0.7% of the time (5% / 7), before any API failure. Nothing measures that. The owner's 14 Oct forecast
  routine ran hours late (DESK_DECISIONS 15 Oct, "8 A").
- **The prompt.** It runs `pip install -r requirements-groww.txt`, which the builder says fails in a container. The
  maximum length of a routine session (about 55 minutes are needed) is not stated.
- Fix, in the text:
  - (a) Overlap: fire earlier (for example HH:00, running to HH+1:05), so each boundary mark has two runs. The
    first-version store and "already recorded" already make the second run harmless, and that should be tested.
  - (b) A tested install line (or a fixed `requirements-groww.txt`, its own lane-1 change).
  - (c) A measured trial before the recorder counts as live: for example 5 sessions through the routine, with slots
    good / missed / late and void sessions reported.
  - (d) The stated consequence: if the void share stays above 5%, design 5.2's "new version" applies and the host
    question returns to the owner. Design 6.6 allows option (b) only "if Groww offers a data-only key".

**4. The no-order guard is a deny-list over one folder, but the client it wraps can trade.**
- `GrowwProvider` holds a full `GrowwAPI` object (`fno/providers/groww.py:115-127`), and that SDK has order methods.
  Design 6.6: "A key that can trade".
- Criterion 10 only greps `fno/intraday/` for order words and fakes an API whose order methods fail. Neither stops a
  call through the shared provider or any other module the package imports.
- Fix:
  - A read-only allow-list wrapper: the intraday source gets an object exposing only the named read calls (`get_quote`,
    `get_option_chain`, `get_expiries`, `get_contracts`, plus sign-in). Any other attribute raises.
  - Tests: the wrapper refuses every other attribute; the source can reach the client only through it; and the grep
    covers the whole import closure of `fno/intraday/`.

**5. Drive failure is not defined.** The snapshot's only home is the owner's Drive, but no criterion says what a failed
Drive write does. Fix: the slot is `failed` with a named failure (`drive_write`, the error type only, as in A4b); the
raw document is never written to the repository and never spooled inside the checkout; one alert, through criterion 7's
streak rule. Add a test, and add the Drive settings to the routine prompt's prerequisites.

## Minor

1. **Process (quality rule 1).** The orchestrator reports that this builder wrote code locally before this check. Rule 1
   says code starts only after the story check passes. Nothing unpushed is judged. Any evidence taken from it must be
   reproduced on the pushed code.
2. **The heartbeat checker runs on the same platform** (stated). The text should say that GitHub's push receipt of
   `heartbeat.json` is the off-platform witness the post-mortem reads.
3. **For the orchestrator, not this story.** Groww's index candles from 2020 (step 0) could give V1's intraday HAR
   baseline its 250 sessions at once, instead of about a year after A16 goes live (design 5.3). Prioritising A16b, and
   letting G6 decide the label, is worth considering (reasoning only).

## Project rules

- Lane 1: a new story, outside services.
- New composition root `fno/intraday/wiring.py`. `fno/storage/wiring.py` is at 345 lines; I checked, it is 345 on main.
- Constants and env names placement stated; files under 350 lines planned. No secrets or model names in the text.

**Verdict: FAIL for db26fd7a329fc6605438db839ac8a66ad1634db3** (story text), on should-fixes 1-5. Code may not start until
a revised text passes. A re-check needs the story file and response 108 only.

## Addendum 1 (15 Oct 2026): story text revision at 83f3614886f0ebe9d4c63f20f7511679662fb71a (db26fd7..83f3614)

One commit: the story file and response 108 part 1b. Text only. The work-in-progress code on
`wip/a16-groww-15min-code` (5355b29) is not judged; see the process note.

| Item | Status | Evidence |
|---|---|---|
| Should-fix 1: source-time rule | PARTLY (see should-fix A) | Primary: the index quote's `last_trade_time` (seconds, or milliseconds above 10^11). Fallback: the end of the latest 1-minute index candle. Neither: stale (`index_time_missing`), never assumed fresh; `index_time_basis` is recorded; both branches built and tested. The rule is now fixed before code |
| Should-fix 2: repeats | MET | `index_repeated` is a flag and voids nothing; only an old or missing source time is stale |
| Should-fix 3: trigger | MET as a design, with one new defect (should-fix B) | Seven fires at HH:00, each running to HH+1:05, so every hour boundary is covered twice. The trial (criterion 15: 5 consecutive sessions, per-mark statuses, void share, each fire's delay and length) runs before anything counts. The consequence above 5% is stated, alternatives are left to the owner, and the routine's unknown maximum length is to be measured. The install line is stated as tested, with fixing `requirements-groww.txt` named as its own change |
| Should-fix 4: read-only guard | MET | `ReadOnlyGroww` exposes `get_quote`, `get_option_chain`, `get_expiries`, `get_contracts`, `get_historical_candles` and constants; anything else raises `ReadOnlyViolation`. It is built only in the composition root, and the source never holds the client. Tests: refusal over the SDK's public names, a whole session with a fake whose order methods fail, and a grep over the import closure |
| Should-fix 5: Drive write failure | MET | `failed` with `drive_write: <type>`; the document is dropped, never in the repository or the checkout; the loop goes on; the streak alert fires; test with a raising store |
| Additions | ACCEPTED | `heartbeat-check` reads GitHub's copy, so a host whose pushes fail looks silent. `rv` settles an unfinished previous session. Alert holds and retries are stated. Per-chain emptiness counts. Dry run refused inside the repository. The commit refuses without `core.hooksPath` |

## Should-fix

**A. In the fallback, the level and its time come from two different calls.** The level is the quote's `last_price`,
while its "source time" is the end of a 1-minute candle fetched in a separate call. A live candle feed proves the
feed is running, not that this quote's value is fresh. A frozen quote beside fresh candles would be called fresh, and
catching that is exactly what the staleness rule is for (design 5.2, "a stale quote repeated"). Fix, one of:
- in fallback mode take the level from the same source as its time (the latest 1-minute candle's close, labelled
  `candle_1m_close`, which is also sampled at the minute mark);
- or require the quote's level to lie inside that candle's low-high range, else `stale`.

Also state that the candle's start time is IST text without an offset (step 0) and how it is parsed.

**B. Two overlapping runs live in two different checkouts, and the ledger has no rule for that.**
- Each fire is a separate routine container with its own clone. At every boundary mark (HH:00) both runs take the
  mark and both append that slot's row to the same daily `slots/.../nifty_<day>.csv`, then pull and push.
- Two appends at the end of one file conflict in git (no `merge=union` there). The story's commit "aborts a failed
  pull's merge", so the push fails, "NOT committed" follows, and the hand-commit step runs, every hour.
- Even a clean merge would leave two rows for one mark, against criterions 1 and 5's "exactly one ledger row". The test
  "two recorders on one store and ledger" shares one ledger, so it cannot show this.
- Fix: define the reconciliation and test it with two git clones of one bare repository:
  - for example, the ledger row for a mark is written only by the run whose Drive put created the first version (the
    `FirstVersionStore` already decides this); the other run records nothing for that mark;
  - or the slots file is merged by slot with the first-stored row kept (a merge driver or a union merge plus a
    dedupe), so a conflict never blocks a push.

## Process note (quality rule 1)

The builder kept writing code after the first FAIL and pushed it to `wip/a16-groww-15min-code` (5355b29). Rule 1 says
code starts only after the story check passes. Pushing to a separate branch, which nobody merges or judges, keeps the
story branch clean. It is still a breach of the rule's intent, now in two builders (A4b too). Not blocking, because
nothing unjudged reaches `main` and the code will be judged fresh. The orchestrator should tell builders to stop
writing code until the text passes.

**Verdict: FAIL for 83f3614886f0ebe9d4c63f20f7511679662fb71a** (story text), on should-fixes A and B. Should-fixes
2-5 of judge 108 are met, and 1 is met apart from A. A re-check needs only the Definitions (source time) and the trigger
design and criteria 1 and 5 (ledger reconciliation).

## Addendum 2 (15 Oct 2026): story text at 27f7b55419b74874420180d8462052dda9752e8c (83f3614..27f7b55)

The story file and response 108 part 1c only. Text only.

| Item | Status | Evidence |
|---|---|---|
| Should-fix A: fallback level and time from one record | MET | In fallback the level is the latest **finished** 1-minute candle's close and its time is that candle's end. A candle still forming is never used. The quote's `last_price` is kept but never the level. Naive candle text gets an explicit +05:30, and text with an offset or unparseable text is `index_parse`. `index_basis` is on the document and the ledger, and `basis_counts` on the RV row, so a session that mixes the two sources is visible |
| Should-fix B: two checkouts, one ledger | MET | One file per mark, per RV session and per revision index, so the runs never append to the same file. A taken mark's row is written only by the run whose Drive write made the first version (`FirstVersionStore.put` reports it). A pull comes before settling marks. A same-path race (both writing one `missed` row or the heartbeat) merges with GitHub's copy winning (`-X theirs`, in this committer, which commits only this folder, so it can only decide between two first versions of one file). Criterion 1's test uses two clones of one bare repository: one row per mark on `origin/main`, no conflict markers, both commits succeed |

I traced the races:
- A run takes a mark and the other later settles it as missed: the second run sees the Drive file and skips it.
- Both runs fail one mark: the first push wins, and both rows were bad anyway.
- Both write the heartbeat: the first pushed wins. Both runs are alive then, so the silence check is unaffected.

`-X theirs` cannot touch files outside this folder, because the committer stages only this folder, so only this
folder can conflict. That makes it safe as scoped.

**Verdict: PASS for 27f7b55419b74874420180d8462052dda9752e8c** (story text). Code may start on the story branch. The code
check covers every criterion, the trial (criterion 15) and the in-session amendment. The work-in-progress code on the
side branch is judged only once it is on the story branch.

## Addendum 3 (15 Oct 2026): the code and story amendment 1 at a471f44f14cd1080206b81d0622dad59ad14a857

A16's own commits are 059fd07 (code), a5ed4b9 (amendment 1 and claims) and a471f44 (claims); the rest of the range is
`main` merged in.

## Gates

- Full suite at a471f44: **4,059 passed** (Slack token unset). `ruff check`, `ruff format --check` and `check_imports`
  are clean.
- A trial merge with today's `origin/main` conflicts only in `reviews/claude/README.md` (index rows; keep both).
- Every new file is under 350 lines (largest: `recorder.py`, 209). There is a new composition root,
  `fno/intraday/wiring.py`, and it is listed in `CLAUDE.md`.

## My own live check (read-only Groww, 15 Oct 2026, 10:00 IST mark)

My session has the Groww key and TOTP in its environment. The SDK installed with the story's `--no-deps` line, which
works. I ran `python -m fno intraday snapshot --dry-run <scratch folder outside the repository>`:
- `10:00 good: 220 of 220 contracts (220 two-sided), index answered 0.8 s after the mark`.
- The index quote's `last_trade_time` was empty, the basis was `candle_1m_close`, and the source time equalled the
  mark. Chains were 19 and 27 Oct; the document finished 54 s after the mark; `clock_ok`.
- The marks 09:15-09:45 got `missed` rows (my run started at 09:54), and the streak alert went through the dry-run
  sender ("NOT sent: dry run").
- The worktree stayed clean. The raw document exists only in the scratch folder. Only reads were made, and no order
  call is reachable (below).

## Safety checks (the special-care items)

| Item | Result |
|---|---|
| No order path to Groww | MET. The source holds only `ReadOnlyGroww` (allow-list: `get_quote`, `get_option_chain`, `get_expiries`, `get_contracts`, `get_historical_candles`, four constants). It is built in `wiring.py` around `GrowwProvider.api`, and `__setattr__` is refused. My plant I1 (allow-list off) is caught. `listed_expiries`, moved into `providers/groww.py`, uses only `get_expiries` |
| Secrets | MET. Credentials come from the environment through `GrowwProvider`. Failures keep exception class names only (`_call`, `_take`, `cli`). Covered by the builder's planted-secret test |
| No raw quotes in the repository | MET. Repository files hold times, counts, statuses, SHA-256 values and the realised variance. The raw document goes to Drive or a dry-run folder, and a dry run inside the repository is refused (plant I14 caught) |
| Gaps never filled | MET. A `missed` row is written only after mark + 120 s (I9 caught). A failed mark has a row and no file and is never retaken. Both RV parts are void on any missing level (I7 caught) |
| Clock contract | PARTLY: see should-fix 2 |

## Story amendment 1 (the 09:15 open rule): ACCEPTED, with one condition

- **The problem is real.** I saw the same live behaviour: no index time, the candle fallback always runs. At 09:15 no
  session candle has finished, so under the passed rule every session's RV would be void.
- **Fairness.** The open of the 09:15 1-minute candle is NIFTY's first value at or after 09:15:00, the level set by
  the pre-open call auction. That is the index's opening level, a fair 09:15 sample.
- **Staleness.** A forming candle exists only if ticks arrived in that minute, and its open cannot change afterwards.
  So it cannot carry a previous session's value, provided Groww builds candles only from ticks (some evidence: one
  day).
- **Scope in the code.** `index_reading.candle_reading` takes the open only when the latest finished candle ends
  before the mark and the candle starting at the mark is present. At later marks the close of the candle ending at the
  mark is used. My plant I3 (open rule first) is caught.
- **Condition.** In the criterion 15 trial, and then weekly in the post-mortem, compare each session's 09:15
  `candle_1m_open` with NSE's official NIFTY 50 open (the index-close file's open value, already archived by A1).
  Report every difference above 0.05 points. A systematic difference is a new version. This makes the rule checkable
  instead of assumed.

## My mutations: 21 of 24 caught; 1 plant was invalid

- **Caught:** I1-I5, I7-I17, I19-I21, I23, I24 (allow-list, forming candle, open-rule order, 120 s boundary, early
  request, void rule, muhurat skip, missed timing, streak length, alert hour, heartbeat 30 min, skew 5 s, dry-run
  guard, hooks check, `-X theirs` scope, candle offset, second copy writing a row, heartbeat from GitHub, quote price
  without time, the 6% band, empty chain).
- **Invalid:** I6 (a no-op plant of mine).
- **Survived:** I18 (gzip `mtime=0` dropped: "same document, same bytes" is untested) and I22 (row files' write-once
  check removed: the ledger's write-once is tested only through settle skipping existing rows). Both minor.

## Should-fix

**1. Two runs can create two Drive files with the same name, after which every read of that mark fails.**
- `GoogleDriveUploadStore` says it is "meant for one writer at a time": `put` looks for the file, then creates it.
  The trigger design puts two writers on one path at every hour boundary.
- If both runs finish a boundary mark within the second or two between look-up and create, Drive holds two files
  named `nifty_<day>_<HHMM>.json.gz`.
- From then on, every `get` of that path raises `RawFileConflict` ("2 items named ... in one Drive folder",
  `google_drive.py:78`). That includes the next mark's settle (`_previous_level`) and the session's RV (`_readings`).
  The rest of the day's runs stop with an alert, the session's RV is lost, and the duplicate stays for good.
- How likely: the later fire usually starts late, so it is rare. But nothing prevents it. The two-clone test uses a
  local folder as "Drive", so it cannot show this.
- Fix, one of:
  - (a) each run stores under a run-unique name (for example with its run id or SHA-256), the first-pushed ledger row
    names the file, and readers and the RV read the file the row names;
  - (b) after its put, a run looks for duplicates of the name and resolves them deterministically (earliest Drive
    `createdTime` stays the raw file; the other is moved to `revisions/` with its index row), both in the recorder and
    in readers;
  - (c) drop the boundary overlap and accept the trial's measured void share.

  Add a test with a fake Drive that interleaves two runs' look-up and create.

**2. The host clock is never checked against GitHub, and the clock code repeats T1's two fixed defects.**
- `fno/intraday/clock.py` uses `GITHUB_TIME_URL = "https://api.github.com"`. Through this environment's proxy that
  answers 400 with no `Date`: my `HttpDateClock("github", ...)` gives `None`, while Slack gives +0.26 s. So "GitHub"
  is always unchecked, and `clock_ok` rests on Slack alone.
- It also takes a `Date` header from any status, including an error answer from a proxy.
- Both are exactly judge 101's should-fixes 1 and 4 on T1, fixed in `fno/cards/clock.py` (2xx/3xx only; the
  repository path `api.github.com/repos/exepex/trading`).
- The claim "host clock against GitHub and Slack within 0.5 s" does not hold for GitHub here.
- Fix: use one clock module for both stories (DRY), with T1's checks, and a test for an error answer carrying a
  `Date`.

## Minor

1. When the alert send fails, one settlement can try the same streak alert several times. My dry run printed the
   3-mark alert twice after the 2-mark one; that is harmless, but one attempt per settlement would do.
2. Tests for I18 (equal documents, equal bytes) and I22 (a ledger row file is never rewritten).
3. `manifest_commit.py`, shared by every manifest job, now refuses to commit without `core.hooksPath`. Every workflow
   that commits sets it (I checked all 12), and routines do per `CLAUDE.md`. Correct, but outside A16's own folder;
   say so in the claims.
4. Open items, stated by the builder and not blocking the code: the `requirements-groww.txt` fix (its own change), the
   routine set-up by the owner, and the criterion 15 trial. Nothing counts as recorded history before the trial
   (criterion 15).

**Verdict: FAIL for a471f44f14cd1080206b81d0622dad59ad14a857**, on should-fixes 1 and 2. Amendment 1 is accepted with
its NSE-open check, and everything else is verified, including a live read-only snapshot. A re-check needs the store
race design and its test, and the shared clock with its test.

## Addendum 4 (15 Oct 2026): the fixes at 84e80eb6110fa4acc6a216c533869e219d8bde37 (a471f44..84e80eb)

A16's own change is 79a981c, plus the claims commit 84e80eb. The rest of the range is `main` merged in. The story text
gains "amendment 2" (the store and clock rules below) and the 09:15 condition.

## Gates

- Full suite at 84e80eb: **4,126 passed** (Slack token unset). `ruff check`, `ruff format --check` and `check_imports`
  are clean.
- A trial merge with today's `origin/main` conflicts only in `reviews/claude/README.md` (keep both rows).
- No reference to the removed first-version store remains. `fno/server_clock.py` is 109 lines.

| Item | Status | Evidence |
|---|---|---|
| Should-fix 1: two writers, one Drive name | MET | Each copy is `nifty_<day>_<HHMM>_<SHA-256 first 16>.json.gz` (`document.snapshot_path`). `SnapshotFiles` saves copies and reads only through the ledger row (`used`). A due mark without a row takes the smallest-named copy (`unrowed_copy`), a fixed rule. The `InterleavingDrive` fake reproduces Drive's look-up-then-create. My plants J1 (one shared name again), J4 (largest copy instead of smallest) and J6 (reads ignore the row) are all caught |
| Should-fix 2: one shared clock | MET | `fno/server_clock.py` trusts 2xx/3xx answers only and asks GitHub at `api.github.com/repos/exepex/trading`. A16's `ClockCheck` adds `clock_partial`. **Live, from this session:** `clock_ok {'github': 0.0, 'slack': 0.0}`, so GitHub is now really checked (it was `None` at a471f44). My plants J2 (status check off), J3 (root URL) and J5 (partial counted as ok) are caught |
| Minors 1-2 | MET | One alert send per settlement (my J7 caught). I18 and I22 now caught |
| Minor 3 (shared committer) | MET | Stated in the claims; 12 of 13 workflows commit and all set `core.hooksPath` |
| `document.py` against the claims (the builder's checkout slip) | MET | At 84e80eb it has `snapshot_folder`, `snapshot_path(source, day, mark, data)` with the SHA-256 in the name, `mark_prefix`, and `gzip.compress(..., mtime=0)`, as the claims say. The intraday tests that depend on them pass, and my J1 and I18 plants bite on this file |

## The orchestrator's two questions

**(1) Can two runs make byte-identical copies, and so collide on one name again? Not in practice.**
- Every document stores each call's `request_sent_at` and `response_received_at`, plus `finished_at`, from the host
  clock to the microsecond. My 10:00 dry-run document has 222 such times (e.g. `04:30:05.413325`, `04:30:54.611155`).
- Two independent runs would need all of them, and every quote, equal to the microsecond. That is not reachable.
- The only way to repeat the same bytes is one run retrying its own save, and A9's store already handles that (same
  bytes change nothing; reserved IDs stop a second create).
- A run id in the name would add nothing (reasoning plus the evidence above).

**(2) Is the shim `fno/cards/clock.py` dead code? No.** T1's production code imports through it (`fno/cards/issue.py:14`,
`fno/cards/wiring.py:25`), as do T1's tests. It is a used re-export that leaves the passed T1 files untouched.
- Minor: `fno/cards/wiring.py` now imports `GITHUB_TIME_URL` from `fno.server_clock` and `HttpDateClock` from
  `.clock`, two paths to one module. Pointing T1 at `fno.server_clock` directly and deleting the shim would be cleaner,
  at the cost of touching passed T1 files. That can be a follow-up, not a finding.

## Amendment 2 (story text): ACCEPTED

- Unique content-addressed names replace the first-version store and its revisions index. Nothing can be written over,
  so design 4.4's "kept under A11's revision rule" holds by construction.
- The ledger row decides which copy counts, the first-pushed row wins, and an unused second copy stays in Drive,
  harmless.
- `clock_partial` is a clearer reading than calling a one-server check "ok".
- The 09:15 condition from addendum 3 is now in the text: compare with NSE's official open, report differences above
  0.05 points, and treat a systematic difference as a new version.

**Verdict: PASS for 84e80eb6110fa4acc6a216c533869e219d8bde37.** Open items for after the merge, not in this code:
1. The `requirements-groww.txt` fix (its own lane-1 change; the `--no-deps` line works, verified here).
2. The owner sets up the routine (no builder creates a schedule).
3. The criterion 15 trial (5 sessions, void share, each fire's delay and length, and the 09:15 NSE-open comparison).
   Nothing counts as recorded history before it is reported.
4. Merge keeping both index rows, run the full suite on the merged tree, and rule 8's end-to-end record. A dry run like
   mine is the right shape: no Drive writes and no Slack posts outside the owner's routine.

## Addendum 5 (15 Oct 2026): merge check, A16 merged to `main` as 72fc707

- **Parents.** 72fc707's parents are 80c03a8 (`main`) and 84e80eb (the passed tip).
- **It equals my recomputed merge, apart from the expected conflict.** `git merge-tree --write-tree 80c03a8 84e80eb`
  differs from 72fc707's tree only in `reviews/claude/README.md`: the conflict markers are removed and both index rows
  kept, as asked.
- **The passed files arrived unchanged.** `fno/`, `tests/`, the A16 story file and `CLAUDE.md` are identical between
  84e80eb and 72fc707.
- **Nothing unjudged after it.** `main` was still at 72fc707 when I checked.
- **Gates.** The orchestrator reports 4,126 passed on 72fc707, which matches my run on 84e80eb, whose code tree is
  identical. CI on 72fc707 is not read from here.
- **Rule 8.** The builder's live `intraday snapshot --dry-run` on merged `main` is still owed; the orchestrator will
  forward its line. My own read-only dry run on 84e80eb's parent code (a471f44, 10:00 IST: 220/220, candle basis)
  shows the shape it should have.

**Verdict: merge check PASS.** It becomes complete once the rule 8 line is recorded.

## Addendum 6 (15 Oct 2026): the rule 8 record

The builder ran the live, read-only dry run from a clean worktree of `main` at 72fc707 (started 10:55 IST, exit 0):
- printed: "11:00 good: 220 of 220 contracts (220 two-sided), index answered 0.8 s after the mark";
- ledger row: basis `candle_1m_close`, `clock_ok`, worst skew 0.0 s (GitHub at the repository path, and Slack);
- the raw file carries the content-addressed name `nifty_20261015_1100_5a3dccc4dbb99db2.json.gz`;
- the earlier marks got `missed` rows, with "alert NOT sent: dry run".

It is logged in `conversations/2026-10-15.md`. It matches my own 10:00 run in shape and figures, and now shows the
merged naming and clock.

**Verdict: merge check complete.** A16 is done as built. The recorder counts only after the owner's routine and the
criterion 15 trial (with the 09:15 NSE-open comparison).

## Addendum 7 (15 Oct 2026): A16c at 04371e8 (Groww install flag, clock shim removed)

**Verdict: PASS.** No blocking or should-fix findings. Two notes below, neither blocks.

Checked on exact SHA `04371e8cb49fa65227883c041579dada9d9e7f05` and on a trial merge with `origin/main` (4806156).

| Criterion | Result | Evidence (all run by me) |
|---|---|---|
| 1. Command installs into an empty folder; without the flag it fails | MET | System pip 24.0, Debian setuptools 68.1.2. Without the flag: `pip install --no-cache-dir --no-deps --target <empty> clint args` fails with "Failed to build clint args", `AttributeError: install_layout`. With `--use-pep517`: both install. The full documented command `pip install --no-cache-dir -q --use-pep517 --target <empty> -r requirements.txt -r requirements-groww.txt` returns 0; `growwapi` 1.5.0, `clint` and `args` import from that folder. |
| 2. Test catches a documented install line without the flag; the requirements file states the command | MET, with note 1 | Planted: flag removed from CLAUDE.md, from README.md, from the requirements header, and a `python -m pip install … -r requirements-groww.txt` line in docs without the flag: all caught. |
| 3. Test fails if the shim returns, if T1/A16 import the clock elsewhere, or if `HttpDateClock` is defined elsewhere | MET | Planted: `fno/cards/clock.py` re-export back; a second `class HttpDateClock` in `fno/cards/`: both caught. No `cards.clock` import is left in `fno/` or `tests/`. `fno/cards/clock.py` is not in any freeze list. |
| 4. T1 and A16 tests pass with only the import path changed | MET | The T1 test diff is two import lines. `tests/cards`: 63 passed. Full suite: 4,129 passed on the SHA and 4,129 on the merged tree (`FNO_SLACK_BOT_TOKEN` unset). ruff check, ruff format --check and check_imports are clean on both. |

**Questions from the orchestrator:**
- **Network.** The isolated build fetched `setuptools>=40.8.0`, which resolved to 84.0.0, from PyPI here. It uses the same index the routine already needs for `requirements.txt`, so no new host is involved. I cannot see the routine's network policy from this session. If PyPI is reachable for `requirements.txt`, it is reachable for this.
- **Pinning (note 2).** Nothing pins the build setuptools; it floats to the newest release. A future setuptools could stop building `clint` 0.5.1's `setup.py`. That failure would be loud (pip errors at step 1), not silent, but it would cost that day's recording. If it happens, the fix is a constraint such as `PIP_CONSTRAINT` with `setuptools<N` on the install line; pip applies that to isolated builds too. I do not require it now: no second need yet (KISS), and the story puts pinning out of scope.
- **What the test scans (note 1).** It scans `CLAUDE.md`, `README.md`, `AGENTS.md`, `docs/`, `.github/` and `.claude/`, and only lines matching `pip install … -r requirements-groww.txt`. These forms dodge it (each planted, each passed unnoticed):
  - `pip3 install -r requirements-groww.txt`;
  - `--requirement requirements-groww.txt`;
  - a backslash-continued multi-line command;
  - a script outside those folders (e.g. `tools/setup_env.sh`).

  No such line exists today, and a dodged line fails loudly at install time. Suggested hardening for a later change: match `pip3?` and `(-r|--requirement)`, join continued lines, and scan all tracked files except `reviews/` and `conversations/`.
- **Owner item, unchanged.** The routine prompt outside the repository also needs `--use-pep517`. No test here can see it.

**Claims vs reality:**
- Response 108 part 4 and the story's root-cause text match what I reproduced.
- One claim I did not verify: "in a fresh virtual environment (pip 26) they build fine". It is not a criterion.

## Addendum 8 (15 Oct 2026): merge check, A16c merged to `main` as d29c9b3

**Verdict: merge check complete, matches the PASS.**

- **Parents.** `d29c9b3` has parents `fdaf4f6` (main) and `04371e8`, the SHA I passed, and it is on `origin/main`.
- **Same change.** The merge's change against its main parent has the same stable patch-id as the branch's own diff (`bd9c4a41…`): the same 12 files, 124 lines added, 26 removed. Nothing else came in with the merge.
- **Gates on d29c9b3, run by me.**
  - Full suite with `FNO_SLACK_BOT_TOKEN` unset: **4,614 passed**. Main grew since my trial merge.
  - ruff check, ruff format --check and check_imports: clean.
  - The A16c tests plus `tests/cards`: 66 passed.
  - `fno/cards/clock.py` is gone.
- **Rule 8, my own run.** `python -m fno card daily` (dry, token unset) printed `NO TRADE (no_approved_strategy)` for 15 Oct and left the tree clean. The orchestrator's install run into an empty folder matches my addendum 7 run. It is logged in `conversations/2026-10-15.md`.
- **Still open.**
  - The owner's routine prompt needs `--use-pep517`.
  - The scanner hardening is queued as optional.

## Addendum 9 (15 Oct 2026): A16d at 274adb1 (amendment 3: the official-open comparison)

**Verdict: PASS.** It is text only: A16 amendment 3 and response 108 part 5. There are no blocking or should-fix findings and one minor.

This replaces my addendum 3 condition: I compared the wrong value. The 09:15 open is the first continuous trade. NSE's official open is the pre-open auction's result. They differ on most days, so my condition would have flagged normal market behaviour as a source fault.

**My own read-only check (data, not the builder's figures).**
- Method:
  - Groww 1-minute NIFTY candles (08:55-09:20) through `ReadOnlyGroww` with this session's Groww credentials;
  - NSE's `ind_close_all_<ddmmyyyy>.csv` "Open Index Value" fetched directly from NSE's archive;
  - nothing written anywhere; my own picks of 17 dates.
- Picks: 2019 to 2026, including stress days (2020-03-23, 2022-02-24, 2024-06-04, 2025-04-07) and three special Saturday sessions (2024-01-20, 2024-03-02, 2025-02-01).
- Results:
  - Last pre-open candle close minus official open: **0.00 on 15 of 15** sessions that have one. On 2025-04-07 and earlier the last pre-open candle is 09:07; from 2025-09-15 it is 09:14. Both match the text.
  - 09:15 open minus official open: it differs by more than 0.05 on **15 of 15**, from -25.90 to +57.60. The smallest gaps are -0.25 (2026-08-20) and -0.45 (2026-10-14). This fits 67 of 74 and the A16b random-sample count.
  - Two sessions have **no candle before 09:15**. 2019-03-12 has no candles at all, not even at 09:15. 2022-10-24 was the Diwali muhurat evening session. The new "no pre-open value, never filled from 09:15" rule is exactly what these need.
- Cross-checks:
  - The A16b recount is commit 0adc455 on `story/a16b-candle-backfill`: 40 of 40 plus 74 of 74 exact, which is 114. The 09:15 open differs on 40 of 40 random sessions and on 67 of 74 recent ones.
  - The builder's 12 of 12 and 10 of 12 add up from its own two tables.

**Orchestrator's questions.**
1. **Is it testable before the trial code?** Yes. The value is defined without ambiguity: the close of the last Groww index candle starting before 09:15, a 0.05-point threshold, and a named outcome when there is none. I computed it with a 40-line read-only script.
   - Minor finding: criterion 15's trial paragraph lists what the claims addendum must report, and the comparison is not on that list. It lives only in the Definitions condition, which says it applies "in the criterion 15 trial". The condition binds the trial anyway, so this is not blocking.
   - Expected fix, the next time this text is touched: add "per session, the pre-open comparison (difference, or 'no pre-open value')" to the trial paragraph's list.
2. **Do the realised-volatility (RV) wording changes alter a passed criterion?** No.
   - `RV_overnight = (ln(S_0 / S_prev))^2` and `RV_s` are unchanged, with S_0 still the 09:15 level. The 09:15 rule and criterion 6 are unchanged.
   - Design 5.2 and V4 (frozen in G6) refer to `RV_s` only.
   - The removed "usual open-to-close split" wording was wrong. The new text correctly says the overnight part includes the move from the auction to the first trade. No number changes.

**Gates.** A trial merge with `origin/main` is clean. The tests that read stories and responses, plus the code-size test: 893 passed.

**For A16b, information only:** Groww returned no 1-minute candles for 2019-03-12. Its backfill should not assume 1-minute history goes back to 2019 without checking.

## Addendum 10 (15 Oct 2026): merge check, A16d merged to `main` as eaa66df

**Verdict: merge check complete, matches the PASS.**

- **Parents.** `eaa66df` has parents `c2e631c` (main, which carries my addendum 9) and `274adb1`, the SHA I passed, and it is on `origin/main`.
- **Same change.** The merge's change against its main parent has the same stable patch-id (`5cf9a151…`) as the branch's diff from its base `04547f2`. It touches 2 files, +71/-7, both text: the A16 story and response 108.
- **Gates on eaa66df, run by me.** Full suite with `FNO_SLACK_BOT_TOKEN` unset: 4,614 passed. ruff check and check_imports: clean.
- **Rule 8.** Not applicable: there is no code path. This is recorded in `conversations/2026-10-15.md`.
- **Still open.** The criterion 15 minor (list the pre-open comparison in the trial report) is queued for the next A16 text change.

## Addendum 11 (15 Oct 2026): A16e story text at a59b8be (committer adds only A16's own paths)

**Verdict: FAIL.** There are two should-fix findings. Everything else is correct.

The criterion 15 minor from addendum 9 is met: the comparison is now in criterion 15 and in the trial paragraph.

**Checked and correct (scratch Git repository, my own runs):**
- **Pathspec boundaries.** `git add -n -- d/rv` and `-- d/rv/` match `d/rv/2026/r.csv` but not `d/rv-candle/2026/c.csv`. `-- d/heartbeat.json` does not match `d/heartbeat.json.tmp`. The text's claim holds.
- **Partial commits.** `git commit --only -- <owned>` with `rv-candle/…csv` staged commits only the owned file and leaves the stray file staged.
- **No manifests.** A16 writes no manifest rows: the wiring uses the bare `AreaStore(drive, RAW_AREA)`. The builder's correction of the brief is right.
- **Existing behaviour.** Today's committer already commits by pathspec (`commit -m … -- <folder>`, Git's default `--only`), so the change narrows the pathspec. It does not change the commit mode.
- **The push risk left out of scope.** I accept leaving it to the planned shared push guard, as decided under 51(b). One guard instead of a copy per writer is the better design.

**Should-fix 1: an owned path that does not exist yet breaks every commit.**
- Evidence: `research/data/intraday/` does not exist on `main` today. On the first live session, `rv/` first appears at the 15:30 mark. In my scratch repository with `rv/` absent:
  - `git add -- d/slots d/rv d/heartbeat.json` gave `fatal: pathspec 'd/rv' did not match any files` (exit 128) and added nothing;
  - `git commit --only -- … d/rv …` gave `error: pathspec 'd/rv' did not match any file(s) known to git`.
- As written, every mark from 09:15 to 15:15 on the first session would print "NOT committed". The heartbeat would not reach GitHub, and the heartbeat-silence check would fire.
- Criterion 1's fixture already contains an `rv/` file, so it cannot catch this.
- Expected fix:
  - the text says the committer passes only owned paths that exist in the working tree or are tracked;
  - a criterion covers a fresh folder with no `rv/` (slot row plus heartbeat committed, no error);
  - a broken-code proof shows the naive add fails that criterion.

**Should-fix 2: the staged-file check looks only inside the folder, but Git's pull refuses on any staged file.**
- `git merge`, and so `git pull`, aborts when the index differs from HEAD and a merge is needed. Reproduced: a stray staged file with a new remote commit gave "Merge with strategy ort failed".
- So a file staged anywhere else in the checkout passes the folder-only check. Examples: A16b's own manifest rows in `research/data/manifests/groww-candles/`, the story's own shared-checkout case, or a quotes file.
- The run would then:
  - make its local commit;
  - fail the pull and run `merge --abort`;
  - print "NOT committed: pull failed";
  - repeat every mark, piling up local commits that never get pushed, with none of the one-alert-per-run rule.
- Expected fix: check the whole index (`git diff --cached --name-only`, no pathspec) and refuse when anything staged is not an owned path. The refusal line, the single alert and the criterion 2 checks stay as written. Add a criterion with a staged file outside the folder, for example a manifest row: refused, one alert, HEAD unchanged.

**Minor:** the response says the boundaries were "checked: `git add -n` in a scratch repository". I confirm that result. Keep the pathspec boundary test in criterion 1 as stated.

The story text otherwise matches the code it describes: `manifest_commit.py`'s add and commit steps, the `-X theirs` pull, and `abort_merge`.

## Addendum 12 (15 Oct 2026): A16e story text revised at 8af21de

**Verdict: PASS.** Both should-fix findings from addendum 11 are met. The diff from a59b8be is text only: the A16 story and response 108 part 6b.

- **Should-fix 1: MET.**
  - Only owned paths that exist on disk or are tracked are passed, and with none present the outcome is "nothing new to commit".
  - New criterion 2 covers a fixture without `rv/` and a separate empty folder.
  - Criterion 8 adds the broken-code proof (pass every owned path blindly, and criterion 2 fails).
  - A tracked owned file deleted on disk is still passed, which stages the deletion, so it is never silently skipped.
- **Should-fix 2: MET.**
  - The check reads the whole index (`git diff --cached --name-only`, no pathspec) before every pull and every commit. It refuses both when anything staged is outside the owned paths.
  - New criterion 4 covers a manifest row staged outside the folder; criterion 5 covers three marks with one alert and three lines.
  - Criterion 8 adds the proofs: a folder-only check fails criterion 4, and alerting on every refusal fails criterion 5.
  - The builder's message ("Your local changes … would be overwritten by merge") and mine ("Merge with strategy ort failed") are two outcomes of the same Git rule, depending on whether the merge touches the staged path. Both mean the same refusal.
- **Checked as consistent with the existing rules:**
  - Owned files left staged by a commit the record scan refused count as owned, so the next mark retries them and does not refuse.
  - A refused pull falls back to A16's existing "pull failed" settling.
  - The untracked-file limit is stated honestly and adds no rule.
  - Folding into the shared push-guard story (decision 64) later matches my addendum 11 ruling.
- **Code to come.** The judge checks the A16e code against criteria 1-9, including every broken-code proof, in its own lane 1 verdict.

## Addendum 13 (15 Oct 2026): A16e code at f8ba463

**Verdict: PASS.** No blocking or should-fix findings. One minor (a test gap) and one note.

**Gates, run by me.**
- On f8ba463: 4,624 passed with `FNO_SLACK_BOT_TOKEN` unset; ruff check, ruff format --check and check_imports clean.
- On a trial merge with `origin/main` (ce76e22): 4,624 passed; ruff and imports clean.
- New and changed files are 36-128 lines each.

| Criterion | Result | Evidence |
|---|---|---|
| 1. Only owned paths reach origin; `rv-candle/` and `heartbeat.json.tmp` stay untracked | MET | Test at the 15:30 mark checks what reaches origin and the untracked files left. My J10 (whole folder, base `_paths`) is caught. |
| 2. Fresh folder without `rv/`; empty folder | MET | The 09:15 row and heartbeat push; an empty folder says "nothing new to commit". My J1 (blind owned paths) and J8 (no `--others`) are caught. |
| 3. Staged inside the folder: pull and commit refused, one alert, HEAD unchanged, file still staged, row kept; after unstaging, the next commit carries it all | MET | J6 (commit skips the check) and J7 (pull skips it) are caught. |
| 4. Manifest row staged outside the folder: refused | MET | J2 (check limited to the folder) is caught. |
| 5. Three marks, one alert | MET | J3 (alert on every refusal) is caught. |
| 6. Untracked stray only: no refusal | MET | Covered by test. |
| 7. Manifest committer unchanged | MET | The base `_paths()` returns `[self.folder]`: the same `add -- <folder>` and `commit -- <folder>` arguments as before. The new empty-pathspec guard in `pending()` cannot trigger for the base class. The other users (`storage/wiring.py`'s manifest committer, `market_read_models/wiring.py`'s publication inputs) see no change, and their existing tests are green. |
| 8. Broken-code proofs | MET | The builder reports M1-M5 caught. My own plants J1, J2, J3, J5, J6, J7, J8 and J10 are each caught; J5 drops the "/" from a folder name, so `rv` would match `rv-candle`. |
| 9. Gates | MET | As above. |

**The orchestrator's questions.**
1. **Does `_paths()` change anything for other users?** No (row 7).
2. **An owned file deleted on disk.** Checked with the real class on a scratch repository. `ls-files --cached` still lists a tracked `heartbeat.json` deleted from disk, so it is passed, and `git add` staged `D f/heartbeat.json`. Correct.
3. **`--others --exclude-standard`.** Untracked owned files are listed: the fresh-folder test and J8 show this. An ignored file is not listed, as I checked with an ignored `ign.json` named as owned. That is right, because `git add` would refuse an ignored path outright.
   - Untested: dropping `--exclude-standard` (my J9) survives. No owned path is ignored today, so this is not a finding.

**Minor (test gap): the staged-file boundary for single files is untested.** My J4 makes a file name match by prefix in `_matches`, so `heartbeat.json` would count as owning `heartbeat.json.tmp`. It survives all 187 intraday tests.
- With it, a staged `heartbeat.json.tmp` would count as owned and not be refused, and the pull would fail. The current code is correct; only the test is missing.
- Criterion 1 tests this boundary only for untracked files.
- Expected fix, next time this code is touched: one test with `heartbeat.json.tmp` staged, expecting a refusal.

**Note (not a finding).** A staged deletion of an owned file made by another writer (`git rm --cached` on `heartbeat.json`) is neither committed nor refused: in my check `_paths` lists only `rv/` and `foreign_staged()` is empty. So such a pull would fail as "pull failed". It needs another writer to remove the recorder's own tracked file, and the recorder never deletes. The shared push guard (decision 64) can cover it.

**Claims vs reality.** Response 108 part 6c matches the diff. "Beside the unchanged manifest committer" is loose wording: the manifest committer gained the `_paths()` hook, but its Git arguments are unchanged, as the next bullet says.

**Rule 8 plan I accept.** No live run is possible before merge. After merge:
- A dry run on `main` (`intraday snapshot --dry-run`) shows nothing breaks. It uses NoSync, so it cannot exercise the committer.
- The first live routine fire after merge is recorded by the builder in `conversations/<date>.md`. It must show that fire's commit file list (`git show --stat`), containing only `slots/…` and `heartbeat.json` (plus `rv/…` at 15:30), and no refusal line.

I check that commit in the merge check. Until then, A16e counts as merged but not yet proven live.

## Addendum 14 (15 Oct 2026): owner rule "keep the design simple" applied to my open items

The owner rule is in `docs/DESK_DECISIONS.md`, 15 Oct: a scenario counts only if it happens in this system's normal running or has already happened in our data. I re-checked my open items against it.

- **Withdrawn: addendum 13 minor.** It asked for a test with a staged `heartbeat.json.tmp`. Nothing in our system writes that file; it came from my own planted mutation J4.
- **Withdrawn: addendum 13 note.** Another writer running `git rm --cached` on an owned file is a person hand-making odd commits.
- **Withdrawn: addendum 7 note 1.** The scanner hardening for `pip3`, `--requirement`, multi-line commands and scripts was for doc forms nobody uses.
- **Kept: addendum 7 note 2.** It stays a one-line note, not a request: an unpinned build setuptools could break the install one day.
- **Kept: addendum 11 should-fix 1, now met.** The missing `rv/` before the first 15:30 is a real case: the first live session hits it for certain.
- **Re-rated: addendum 11 should-fix 2, now met.** It assumed another writer stages files in the recorder's checkout. The story itself says each routine fire is a fresh clone, and A16b's backfill is a one-off command run elsewhere. Under the new rule that path is not shown to happen. It would have been at most a note, and the folder-only check the orchestrator first decided would have been enough.
  - What it added: the whole-index check is a few lines inside the same committer, with two tests.
  - The owner or orchestrator decides whether to keep it, per point 4 of the rule. I do not ask for its removal.

## Addendum 15 (15 Oct 2026): merge check, part 1, A16e merged to `main` as b035811

**Merge structure: complete and matching the PASS.**
- `b035811` has parents `c6c285a` (main) and `f8ba463`, the SHA I passed, and it is on `origin/main`.
- Leaving out judge files, the merge's change has the same stable patch-id (`bb9b3d00…`) as the branch's diff from its base `902f3b6`.
- On b035811 with `FNO_SLACK_BOT_TOKEN` unset: 4,624 passed; ruff and check_imports clean.

**Rule 8: open.** Under the plan accepted in addendum 13, I check the builder's dry run and the first live fire's commit file list when they arrive. Until then A16e is merged but not yet proven live.

The orchestrator keeps the whole-index check (addendum 14, point 4).

## Addendum 16 (15 Oct 2026): A16e merge check, part 2: rule 8, part 1

**Merge check complete, matching the PASS.** One item is open: the first live commit.

- **The builder's record.** `conversations/2026-10-15.md` has the dry run on main `b6910e8`: "14:15 good: 224 of 224 contracts", exit 0, clean tree.
- **My own run.** On main `ea18b1f`, which contains b035811, I ran `python -m fno intraday snapshot --dry-run <scratch>` with `FNO_SLACK_BOT_TOKEN` unset. It used read-only Groww with this session's credentials and wrote to a scratch folder, since deleted.
  - Output: `14:30 good: 220 of 220 contracts (220 two-sided), index answered 0.7 s after the mark`, then "dry run: nothing pulled, committed or pushed", exit 0, clean tree.
  - The run also printed a "2 bad snapshots in a row (09:15, 09:30 not_taken)" alert, marked "alert NOT sent: dry run". That is expected for an empty dry folder, which has no earlier rows that session. It is not a defect.
- **Open: part 2, the first live routine commit.** It waits for the owner to set up A16's routine. When it comes, its `git show --stat` must hold only `slots/…` and `heartbeat.json` (plus `rv/…` at 15:30), with no refusal line. I check it then.
