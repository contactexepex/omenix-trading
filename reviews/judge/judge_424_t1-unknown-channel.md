# Judge 424: T1's may-have-posted text names the poster's own channel (story/t1-unknown-channel at 28e42825)

**Verdict: PASS (lane 1: Slack text), with one merge condition about FL1-1.**

`fno/cards/posting.py`'s `UNKNOWN` changes from "(check #fno-desk)" to "(check channel {channel})". The channel is
`SlackCardPoster`'s own, so a lost post to #fno-forecast (FL1-1) no longer sends the owner to #fno-desk. The phrase
"Slack may still have posted it" is unchanged. FL1's guard against a double post matches on that phrase, and I checked
it is still in the text.

## Checked myself (strong evidence)
- **Gates:** on 28e42825 merged with today's `main` (no conflicts):
  - 8,832 passed, 16 xfailed;
  - `ruff check` clean; 1,627 files formatted;
  - imports clean; record scan clean (7,265 files).
- **Mutation:** putting "(check #fno-desk)" back fails 3 tests in `tests/cards`.
- **Other users of `UNKNOWN`:** none in `fno/`. The only other one is a test on FL1's branch (below).

## Merge condition: FL1-1's test formats `UNKNOWN` without `channel` (strong evidence)
`tests/forecast_lab/test_lab_close.py:78` on `story/fl1-forecast-lab` (a6396ac3) calls
`UNKNOWN.format(failure="ReadTimeout")`. With this change that raises `KeyError: 'channel'`; I ran the call against
28e42825. Neither branch fails alone, but whichever merges second breaks `main`.

Fix:
- the second to merge passes `channel=...` in that one test line;
- or FL1's builder does it now, which is harmless with the old text, because `str.format` ignores extra names.

The merge procedure's full suite on the merged tree would catch it. It is named here so nobody is surprised.
