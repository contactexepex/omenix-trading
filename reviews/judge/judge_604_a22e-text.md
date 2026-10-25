# Judge 604: A22e story text (Amendment 3, index parts' last read at 09:10:45), story/a22e-last-read at 0846f0876 (judge J, round 1 of 2)

**PASS** (text), lane 1, 1 minor. Diff: only `docs/stories/A22-preopen-data.md` (+85). Doc-reading tests with
`FNO_SLACK_BOT_TOKEN` set: 864 passed, 14 xfailed.

## Criteria
| Item | Verdict | My evidence |
|---|---|---|
| Evidence | MET | Read 23 Oct's day row through the verified Drive cache (`data/preopen/day/2026/10/2026-10-23.csv`, SHA-256 290d6382..., equal to its committed receipt). Results: nifty `incomplete`, 3 reads, seen 09:10:59; banknifty `incomplete`, 3 reads, seen 09:11:01. Also gift `ok` (08:40:00) and fo_list `ok` at its first read (09:08:30) |
| Root cause | MET | `run.py:52`: ties go to the earliest `next_at` in list order (gift, fo_list, nifty, banknifty), read one after another. `run.py:76-83`: last read = close - `LAST_READ_BEFORE_CLOSE` (1 s), `ok` only when `seen_at < close`. `seen_at` is the candle answer's `received_at` (`parts.py:92`). The paced source spaces call starts by 0.5 s (`candle_source.py:18`) |
| The rule | MET | `next_at = min(now + 30 s, last_read)` with a 15 s margin gives 09:10:00, 09:10:30, 09:10:45. The default 1 s keeps GIFT at 08:44:59 and the F&O list at 09:10:59. The windows and `seen_at`'s meaning are unchanged |
| Alternatives | MET | Parallel reads would need threads around the paced source. Request-time judging would change `seen_at` for every part. Widening the window moves the 09:12 commit margin. Each is weighed with its reason |
| E1-E4 | MET | each testable on the injected clock; good, bad, boundary (09:10:59 vs 09:11:00) and empty (margin wider than window) cases; 5 plants |
| Out of scope | MET | the rehearsal's "late" is a replay artifact: only the last answer is archived, so REH1c can serve only 09:11:01 |

## Findings
**m1 (minor) The F&O list's last read now waits behind the index reads.**
- Before A22e, all three parts were due at 09:10:59 and the tie went to `fo_list` first.
- After it, the index reads at 09:10:45 run first. Each Groww candle call can take up to `CALL_TIMEOUT_SECONDS` = 30
  (`candle_source.py:21`).
- So if the F&O list were still incomplete after 09:10:30 and both index calls hung, its 09:10:59 read could start
  after 09:11:00.
- This is narrow: on 23 Oct the list was `ok` at 09:08:30.
- Fix: one sentence in the rule saying so, and an E1 or E2 boundary case with the F&O list incomplete and slow index
  calls, so the outcome is a test result, not an assumption.

## Plants
0 (text round). The builder's 5 plants are noted for the code round.

## Addendum 1: A22e code, round 1 of 2, story/a22e-last-read at 5f90b561a
**PASS**, lane 1, 2 minor. The code diff is `fno/preopen/parts.py` (+9), `run.py` (+6 -6) and
`rehearsal/recorded_preopen.py` (+1); tests and the story otherwise.
- **Gates** on a trial merge with main 74dfb9dba (b789f3d7a), `FNO_SLACK_BOT_TOKEN` set: 16,107 passed, 1 skipped, 14 xfailed.
  ruff, format, check_imports (2,695), check_records (9,174) and check_numbers are clean. No Slack post in the run's window
  (16:45:43-16:54:57 UTC).
- **E1-E4 and m1 MET.** The margin lives on the part (`PreopenPart.last_read_margin` = 1 s, `GrowwIndexPreopen` 15 s).
  `run.py:76` reads it, and `test_last_read.py` covers good, bad (old 1 s: late), boundary (14/15/16 s; seen 09:10:59
  ok, 09:11:00 late) and empty (margin past the window: one read at the opening). `test_m1_*` shows the F&O list late
  when two 30 s index calls start at 09:10:45.
- **Plants: 7 of mine, 7 caught.** Index margin 1 s; 14 s; 15 s for every part; `run.py` back to a fixed 1 s; the
  rehearsal copy removed; `ok` at the close (`<=`); last read one second later.
- **(1) Is 15 s enough?** The only real timings are 23 Oct's archived last answers: nifty received 09:10:59 for a read
  due 09:10:59, banknifty 09:11:01. So two paced calls took about 2 s, against 15 s (some evidence, n = 1; 24 Oct was a
  Saturday, and only each part's last answer is archived). A call slower than 15 s is still `late` and alerted with
  its value kept, which is honest. The index source's call timeout is 30 s (`candle_source.py:21`).
- **(1b) The F&O list when the index read runs long:** it is delayed past 09:10:59 and judged `late`, as m1 states and
  `test_m1_*` pins. On 23 Oct the list was `ok` at 09:08:30, so this needs a list still incomplete after 09:10:30.
- **(2) Can the rehearsal diverge?** No. `RecordedPreopenPart.__init__` copies `live.last_read_margin` from the
  wrapped live part (a class attribute; nothing sets it later), and my plant removing the copy was caught.
- **(3) Should CLAUDE.md's A22 section name the last read? Yes,** as a lane-2 wording fix after merge, not a merge
  gate. Step 3 says the Groww candle is read "(09:10:00-09:10:59)". After A22e the reads end at 09:10:45 and the window
  closes 09:11:00, so "09:10:00-09:10:45, window to 09:11:00" would keep the routine's operating text true for a
  session reading a late or incomplete line. It narrows no lane-1 rule and touches no hard line, so it is lane 2.
- **m1 (minor)** The Claims have no printed real-output sample (quality rule 6). The 23 Oct-shape test
  (`test_open_check_record.py::test_d1_*`, both indices "ok (1 read(s))") stands in. Add its lines.
- **m2 (minor)** The builder ran only part of the suite after two test renames; my full run above covers it.
