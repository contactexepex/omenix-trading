# Judge 682: O14 story text, one retry policy for failed commands (story/o14-retry-policy @ 912cb521f), judge E

**FAIL (round 1 of 2; 2 should-fix, 3 minor). Lane 1** (it decides whether a record-writing step runs again, and
it calls outside services; judge 1 of 2). Judge E, own session; judge F's verdict not read. Text only (208 lines).

## Checked and met

- **The owner's words** (section 1) are quoted exactly from DESK_DECISIONS e3bbbdfeb. The gap list maps each part.
- **Section 2's facts, read in code:**
  - `COMMAND_LIMIT_SECONDS` is 600 (`fno/daily/steps.py:24`);
  - GW1a's worst case is "38 x 3 = 114 tries, under Groww's 150 per 24 hours" (`groww_sign_in.py:11`);
  - A16's slot is the mark plus 120 s (A16 story line 148), and A16 runs as its own Claude routine, so it is rightly
    in scope.
- **The design pattern:** one `RetryPolicy` interface with one strategy, wired in the composition roots. The numbers
  are 30 s doubling to an 8-minute cap, 5 retries, ±20% seeded jitter, and the short policy for A16 and A22.
- **No double capture:** the quote parts, the pack and the snapshot are left to their own loops.
- **Classification:** the step's own error classes, and decision 44's run stops stay final.
- **One escalation alert** carrying class names only.
- **The owner questions are fair and honest:** fills kept final, the school kept, exits and marks put to the owner
  with evidence.
- **The quiet-hours rule** (CLAUDE.md "How to work", judge 680.3): O14's retries are the scheduled routine's own, and a
  hand rerun stays only after an escalation. Consistent.
- **Gates:** record scan clean (9,544 files); doc-reading tests 963 passed, 13 xfailed, 0 failed.

## Findings

**Should-fix 1. The deadline rule looks only at the retried step's own deadline. The daily run is one thread, so a
retry can push a later timed step past its deadline.**
- `DAILY_RUN_STEPS` runs `book1` after the 14:58 pack and before `snapshot` and `fills` (15:15, `fills_by` 15:20).
  It also runs `reviews` and `card` before `premium_ranges` (sealed by 15:30) and the school (never after 15:25).
- Section 4 gives `book1` and these steps "the end of the run" as their deadline. Up to 15.5 minutes of waits, plus
  each attempt's run time (up to 600 s), would then cost the day its fills, the school slot or G13d's issue.
- **That is a money step lost to a retry of a step before it.** And "the step's expected run time" in the rule is
  never defined.
- Fix:
  - a step's retry deadline is the earliest of its own deadline and the latest start of every later timed step
    (`fills_by`, `SLOT_LAST_START`, 15:30, the 15:12 v4 check);
  - `book1`'s own deadline is the desk's decision deadline;
  - define the expected run time (for example the step's last measured time, else `COMMAND_LIMIT_SECONDS`);
  - add a criterion with a plant: `book1` failing at 15:05 must not delay `fills` past `fills_by`.

**Should-fix 2. The Groww sign-in budget leaves no margin, and the circuit cannot see a child's failure.**
- Groww's limit is "150 requests per 24 hours" (the 22 Oct probe file, line 111): a rolling window. 114 plus 12 x 3 =
  150 exactly, and a bad afternoon's sign-ins still count at the next morning's 08:36 pre-open.
- The circuit is "shared by every caller in the process", but the daily run's Groww retries are child processes. The
  parent learns a child's failure only from its exit and output.
- So it is not said how a child's sign-in failure or 429 opens the parent's Groww circuit, which section 5 needs for
  "no retry may start a new sign-in".
- Fix:
  - classify a child's Groww error class from its own last line (class names are already public) into the parent's
    circuit;
  - set the budget below the limit, for example 8 processes with a stated margin, or count sign-ins rather than
    processes;
  - add a criterion with a plant: a child's sign-in failure, then no further Groww child that day.

**Minor 1.** Criterion 8 removes step 2b. It should also update the quiet-hours clause in CLAUDE.md "How to work" and
AGENTS.md ("step 2b's once-only rerun holds until O14 replaces it") in the same change, so neither names a removed step.

**Minor 2.** "The end of the run otherwise" is not a deadline the policy can read. Name each step's real one, or
"16:00, `close_recheck`'s start", per should-fix 1.

**Minor 3.** Section 6 makes `card` not safe until a test shows one post. Say the same for every step that posts to
Slack (`recommend`, the editions): a Slack post is the one write that is not write-once.

## Addendum 1

Round 2 of 2, at `ab97493c5` (289 lines). **FAIL: 1 should-fix left (a residual of SF1); everything else is fixed.**
Judge F not read. After this round the owner decides.

**Fixed, checked against the code:**
- **3.1's hard times** match the code: `pack_wait_until` 15:10, `decision_deadline` 15:12 and `fills_by` 15:20
  (`config.yaml` lines 164-167); `SLOT_LAST_START` 15:25 (`school/constants.py:20`); premium_ranges' `DEADLINE`
  15:30. `RETRIED_ON_RERUN` is `exits` and `trade_marks` (`desk/daily_run.py:84`).
- **The expected run time** is defined: 1.5 times the previous session's duration, else 600 s or 60 s.
- **Every caller has a named deadline**, and `book1`'s is 15:12.
- **SF2:**
  - sign-ins are counted, at most 12 a day by O14 (129 of 150 with the next morning's pre-open);
  - the parent reads a child's class from a closed list, and an unreadable class counts as a sign-in failure;
  - a sign-in failure is never retried;
  - the plant is named.
- **A16 and A22:** A22 is not wrapped, and its windows are exact. A16 gets at most 2 retries, none at the 14:30, 14:45,
  15:00 and 15:15 marks.
- **Safety:** the safe-steps table is not-safe by default, and every Slack-posting step is not safe. A command stopped
  at 600 s is never retried (it may have uploaded already).
- **Minors:** m1 (2b's clauses in CLAUDE.md and AGENTS.md updated in the same change), m2 and m3.

**Should-fix 1 (residual). The deadline rule counts only the retried step's own expected time, not the steps run
between it and the timed step.**
- The check is `now + wait + expected <= retry deadline`, where `expected` is the retried step's.
- `exits` and `trade_marks` have retry deadline 15:25 (the school). But `DAILY_RUN_STEPS` still runs `reviews`,
  `quotes_done`, `card`, `price_distribution` and `premium_ranges` between them and the school.
- So an `exits` retry the rule allows up to about 15:24 still pushes the school's start past 15:25. It can also push
  `premium_ranges` toward its 15:30 refusal.
- The `book1` plant passes only because `decisions` comes right after `book1`, with nothing between.
- Fix: a later step's limit, minus the expected time of every step that runs before it (the same 1.5 times
  previous-session rule), is what the retry must meet. Add a plant: `exits` failing at 15:20 must not move the
  school's start past 15:25.

**Gates at ab97493c5:** record scan clean (9,547 files); doc-reading tests 963 passed, 13 xfailed, 0 failed.

## Addendum 2

Round 3 (granted by the owner on 25 Oct), a narrow check of the story's diff ab97493c5..3f15306ae. **PASS, 1 minor.**

- **The residual of should-fix 1 is fixed.**
  - Section 3.1 now meets every limit with the steps between counted:
    `now + wait + expected(retried) + Σ expected(each step after it and before S) <= L`. Each term uses the same
    1.5-times-previous-session rule, and a step that will not run today counts 0.
  - The example names `trade_marks`, `reviews`, `quotes_done`, `card`, `price_distribution` and `premium_ranges`
    before the 15:25 school. Section 4's rows say "less the expected times of the steps between".
  - Criterion 10.2 adds the plant "an `exits` retry pushes the school past 15:25", and the same check for
    `trade_marks`, `reviews`, `card` and `price_distribution`, each with one test.
- **Verified in code:** `exits` alerts only when its event is new (`fno/desk/exits.py:196`, `if new and outcome in
  ...`), so the safe row's "a retry alerts nothing twice" holds. `forecasts_v4_pack` is now not safe.
- **Minor:** the header still reads "pending the owner's word on a third round". Update it to the owner's grant.
- **Disclosure:** the commit range also carries main's merged judge files, so its diff showed me judge F's 683.1. My
  finding (682.1) was written and pushed before that, and this check rests only on the story's diff and the code.
- **Gates at 3f15306ae:** record scan clean (9,549 files); doc-reading tests 963 passed, 13 xfailed, 0 failed.
  The story is 303 lines, under 500.

No blocking or should-fix finding is left.
