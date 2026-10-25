# Judge F: pending work at handover (24 Oct 2026, 06:46 UTC)

Every Judge F verdict is on `main`. This file has no claimed number: it is a handover note, not a verdict.

## Waiting for a request

- **A4c-2 code** (`story/a4c-alert-outcome`; the A4h/A4c builder, session_01MKtUHByHsR9cNwaP5KhFYH).
  - The text passed in judge 568 addendum 1. Draft code commits 2425cc96 and 8ca0ba05 are on the branch; I have not
    judged them.
  - The claims must show: DRY2's 14:38 lines replayed; a planted bug per criterion; O1's pinned 14:38 and 14:44
    unchanged.
- **A20c** (829d025e): paused by the owner's scope freeze, not for judging (O9 builder). It needs a fresh request.

## Checks after merges (quality rule 8), still open

| What | Source |
|---|---|
| A4h's first 5 sessions: read, recheck and confirm lines, no level in any | judge 440 add. 2, judge 447 |
| A17e: the first world-cues run (TWSE resets, criterion 9's counts and overlaps) | judge 439 minors 4 and 5 |
| A4f: the first live weekly line (expiries, rows, end time against 15:13) | judge 441 minor 3 |
| O9b step 2: the first `nse-margins` and `stress-factor` runs on Drive, and the first C2 and C4 reads | judge 534 and add. 1 |
| DR1: `record_store` switched to `build_stored_index_close_files()` | judge 558 add. 1 |
| Also: A9c's live hosts day, the VIX pilot, the health-run duration after the bisect, and the DR1-0 `--apply` (the orchestrator's go) | earlier verdicts |

## How Judge F worked (for the next judge)

- Check out the exact head in a worktree under the scratchpad. Run the full suite with `env -u FNO_SLACK_BOT_TOKEN`.
  Never run a plant beside a full run.
- Read a merge's own changes with `git show --remerge-diff`.
- Never use `pkill -f` on a pattern your own shell matches: it kills that shell.
