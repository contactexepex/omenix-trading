# Judge 60: T1 test reliability and the filings field messages, code (one judge, judge #2)

Branch `story/T1-test-reliability`, SHA `147d15c`, compared with base `324d9fd`. I judged it at the lane-1 bar,
because it touches the filings parsers and the pacer's tests. **PASS**, with one note.

## Gates (`__pycache__` cleared)

1116 passed; ruff and imports clean. `tests/ingestion/test_nse_pacer.py` run 5 more times under `-n 8`: 14 passed every
time.

## (1) The pacer tests

**Deterministic, and no weaker.** The probe test now sets the probe's waiting limit at 100 times the join bound, so a
thread that the probe's answer does not release fails as still blocked; it does not pass on a timing threshold. The
spacing is read from a recording `sleep` on the frozen clock (`[0.05, 0.10]`). The "waiter gives up" test keeps its
0.15 s lower bound, and `run_bounded` is the upper limit. The "probe raises" test is released only by the failed
probe.

| Plant in `nse_pacer.py` | Pacer tests failed |
|---|---|
| `rate.acquire()` removed | 1 |
| `notify_all()` removed (a waiter never released) | 2 (after 57 s: they wait out their bound) |
| no limit on waiting for the probe | 1 |
| no waiting for the probe at all | 4 |

## (2) The filings field messages

`time_field` and `day_field` read the field, then parse it inside a `try` that re-raises "field NAME: not a time/date
in NSE's format" `from None`, so neither the text nor its cause chain is shown. Behaviour is otherwise unchanged:
- empty text still gives `None`, through `text_field`, and a missing required field still raises through
  `required_text`;
- the exception type is still `ValueError`, so every caller's handling is the same;
- `public_time` keeps its "latest time" rule on datetimes;
- every `nse_time`/`nse_day` call site in `index.py` is switched (grep).

| Plant | Failed |
|---|---|
| The time message quotes the text | 11 |
| The date re-raises Python's own error (text in the message) | 5 |
| A malformed time read as no time | 11 |

## Note (not blocking)

`fno/ingestion/filings/listing_dates.py:21` still calls `strptime` directly on NSE's listing-date text, so a malformed
listing date would raise Python's message quoting that text. It is outside this change (a different file, and not one
of the five list shapes). If its error reaches a public log line, the same `field NAME` treatment applies there; a
small follow-up.

**Verdict: PASS** (judge #2).
