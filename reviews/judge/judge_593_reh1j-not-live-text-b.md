# Judge 593: REH1j story text, not-live steps never a problem of the day (story/reh1j-not-live @ 37eec0600), judge B

**FAIL (round 1 of 2; 1 should-fix, 2 minor). Lane 1, rule 1 (text first).** One file, the REH1j section of
`docs/stories/REH1-rehearsal-mode.md` (+95 lines from main e891f3bcb): judged by reading. Doc-reading tests at
37eec0600, with the Slack token kept (DESK_DECISIONS rows 329-330): 853 passed, 15 xfailed.

## Criteria

| # | Check | Result | My evidence |
|---|---|---|---|
| Finding | the three false problems | MET | `margin_check: null`, `card: null` in `config.yaml` `daily.live_from`; `stress-broker-check` is not in `nse_margins/cli.py` (only `nse-span`, `stress-factor`); `NotLiveInRealRuns.run` returns the step's outcome unchanged (`live_wiring.py`) |
| Root cause | REH1c's rule, not the steps | MET | `problem_steps` counts any `failed`/`refused` status (`run_log.py:64-67`, `_problem`); a real run's `not_live` never counts |
| Reversal? | owner or judge decision | MET: none reversed | "an honest result, not hidden" is REH1c's builder text (`REH1-rehearsal-mode.md:449-450`); judges 563 and 564 ruled on the wrapper and the labels, not on counting. The owner's ask (every report runs, labelled, posted) is kept |
| `build_parser()` | a pure extraction | MET | `main()` lines 179-270 only build the parser; my AST scan of every `add_*_parser` finds no I/O (config, files, env, clock, network, subprocess) |
| Readers claim | no step reads a not-live step's result | MET, list incomplete | also `reviews.py:60` (snapshot), `feed_gate.py:48` (candles), the scoreboard (decisions, exits), `NEEDS` (fills: snapshot, decisions); none of these steps has a `daily.live_from` key, so none is ever wrapped |
| Public log | `exercised` in `journal/runs/` | PARTLY | `PublicResult.public` codes leaves at any depth, so a nested result stays status-only; the new texts have no code (minor 1) |
| J1-J6 | testable, cases | MET | each has good, bad and boundary cases and a plant; J6 pins real runs |
| Gap list | complete | NOT MET | finding 1 |

## Findings

1. **Should fix: the text never says where the owner sees an exercised failure, and two owner rows of 24 Oct are
   missing from the gap list.** Row 322: "I want warning so that we could understand and know that there was some
   issue instead of hiding". Row 329: "Publish to slack ... Run everything including full dry run stages". Design 4
   prints the "not live in real runs (exercised)" line only on `rehearse`'s own output. Design 5 says "the rehearsal's
   summary in its report is the line in 4" without naming that report. After REH1j, a replay's card no longer warns
   for these steps. A not-built step posts nothing, and the line is the only trace of 23 Oct's `margin_check` and the
   card's T1f failure [strong: text read]. That is visible to the orchestrator but not in Slack, where the owner
   reviews the dry run. Fix: add both rows to the gap list. Post the exercised line once, labelled, to #fno-desk, or
   have the rehearsal's card name the exercised steps on their own line without the real-day warning. Add a J5 test
   for the post.

## Minor

1. Name the reason codes. The public run log keeps a reason only as a closed code (`public_log.py`; `reason_codes.COMMON`).
   Neither REH1c's notes (`NOT_LIVE_UNSET`, `NOT_LIVE_UNTIL`) nor the new "no command '...' in fno" is registered, so
   both would log as `unlisted`. Add them to J1 and J3.
2. J3's check walks argparse's subparsers (a private `_SubParsersAction.choices`). Add a boundary for a path whose parent
   exists and whose child does not (`margins stress-broker-check` beside `margins stress-factor`). Also add one for a
   path that is a prefix of a real command.

## Plants

None (text). The planned plants are sound; add "the not-built check fooled by a parent that exists" (minor 2).

## Notes

- `quotes_done`: on main a part whose key is not live is left out of the day (`quote_parts.py:209-215`). It joins only
  because `rehearsed_live` makes its key live, so moving it to `exercised_parts` in the rehearsal's root restores the
  real day's rule.
- My earlier gate runs today used `env -u FNO_SLACK_BOT_TOKEN`, as my brief asked, before I read rows 329-330. From
  this verdict on I keep the token.

## Addendum 1

**REH1j story text, round 2 (story/reh1j-not-live @ 73d3c1b71), judge B: PASS (1 minor). Lane 1, rule 1.** Only
`docs/stories/REH1-rehearsal-mode.md` differs from main (my `git diff --name-only` from the merge base), so I judged by
reading. Doc tests at 73d3c1b71, with the token kept: 853 passed, 15 xfailed.

| Round-1 item | Outcome | My evidence |
|---|---|---|
| SF: where the owner sees it; rows 322 and 329 | **Accepted** | Design 4 posts the exercised line once per daily-run rehearsal to #fno-desk through `build_alert_sender()`, only when something was exercised, with "alert NOT sent" on failure. The parent runs inside `in_this_process(mode)` (`rehearse.py:41`), so the post carries REH1's label. Design 5's reason for not using the card holds (T1's, and itself exercised on 23 Oct). Both rows are in the gap list; J5 tests one post, with three plants |
| m1 reason codes | **Accepted** | Design 6 registers `rehearsal:NOT_LIVE_UNSET`, `NOT_LIVE_UNTIL` and `NOT_BUILT` in `reason_codes.COMMON`; J1 and J3 assert the codes, never `unlisted` |
| m2 parser walk | **Accepted** | Design 2 spells out the walk; J3 adds a missing child under a real parent and a prefix of a real command, with plants |
| Readers list | **Accepted** | the list now matches my round-1 grep |

## Minor (round 2)

1. Design 2 says "each word must be a subcommand", but the daily run's command steps carry options and values
   (`pricedist record --day <d> --live`, `wiring.py:104`). Read literally, a not-live command with options would be
   "not built" and never exercised. Say that the walk stops at the first word that is not a subcommand (an option, or
   any word once the parser reached has no subcommands), and that the parser reached must have a handler. Add a J3
   boundary: `pricedist record --day D --live` is built.
