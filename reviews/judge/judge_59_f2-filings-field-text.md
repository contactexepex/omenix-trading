# Judge 59: F2 filings non-text row fields (code), round 1 at 5f00329: PASS

**Lane 1, one judge (judge #1).** Branch `story/F2-filings-field-text`, frozen SHA 5f00329, base main 75532c0 (F1 merged).
Reviewed `git diff 75532c0 5f00329`: `fno/ingestion/filings/index.py` (+47/-15), the new test file `tests/ingestion/filings/test_non_text_fields.py` (128 lines) and `docs/stories/F2-filings-field-text.md` (27 lines). The story comes from judge 58 N2.

## Design (strong evidence: read and probed)
- Two small functions, `text_field` and `required_text`, sit next to the parsers. Every row field of the four lists and of `_timed`/`_placeable` is read through them.
- `grep` finds one raw read left: `row.get("type") == INTEGRATED_FINANCIALS` (index.py:161). A comparison cannot raise.
- The other raw `r[...]` reads in `fno/ingestion/filings/` (manifest, gaps, progress, listing_dates, wiring) read our own CSVs and state, not NSE rows. They are out of scope.
- `LIST_ERRORS` is not widened. A null or missing period date is now a named `ValueError`; before, it was a KeyError (caught) or an AttributeError (which ended the run).
- `consolidated` is checked too: an object there was an unhashable-key TypeError.
- `index.py` is 204 lines; no file is over 350. There are no new constants for the shared constants file; the messages sit at their single use.
- Trade-off, stated plainly (reasoning only):
  - One unreadable row now fails that company's read for that list for this run. Its other rows are not archived until the next run retries.
  - That is the existing rule ("unknown is a failure, never dropped"), and it is far better than ending the run.

## Gates at 5f00329 (strong evidence)
- ruff, format and check_imports are clean.
- Full suite under `-n auto`: 1100 passed, with `__pycache__` cleared and PYTHONDONTWRITEBYTECODE=1.

## My judge-58 reproduction, widened (strong evidence)
- Method: all four lists × every field of a full valid row × 9 odd values. The values were object, list, number, the text `"zz"`, null, bool, float, the empty string, and the field missing.
- Result: **0 escape**, 119 named failures, 385 normal reads. On main, 84 of these escaped and ended the run.
- In 12 cases the failure line holds the field's text: `"zz"` in `time data 'zz' does not match format ...`.
  - This is Python's own `strptime` message for malformed date text, and it was already on main before F2.
  - F2's "never the value" claim covers its own type message only, and that holds.
  - The leaked text is a public NSE date field, not a secret.
  - Minor follow-up only (reasoning only): wrap the date-parse message if the failure lines must never echo NSE text, for example to keep a huge string out of the log.

## Plants (PYTHONDONTWRITEBYTECODE=1, each one undone; mine, several differ from the implementer's)
| Plant | Result |
|---|---|
| no type check in `text_field` | 157 failed |
| non-text read as absent | 157 failed |
| null period date read as `""` | 5 failed |
| `_timed` reads `exchdisstime` raw | 6 failed |
| shareholding `xbrl` raw | 6 failed |
| `consolidated` raw, classic | 18 failed |
| `consolidated` raw, integrated | 6 failed |
| shareholding `broadcastDate` raw | 6 failed |
| type message leaks the value | 1 failed |
| classic untimed-branch `public_time(row.get("filingDate"))` raw | **0 failed: a plant that cannot change behaviour** |

The last plant survives for a good reason. That branch runs only when `_timed` is False, and in that case `_placeable` has already read `filingDate` through `text_field`, because the `or` goes on past `_timed`. So the raw read there can never see a non-text value. No test is owed.

## Hard lines
No order path, no secret, no Groww call and no network call in the tests. No change to a recorded file, a receipt or a workflow.

## Verdict: PASS round 1 at 5f00329
One minor, optional follow-up: the strptime message echoes malformed date text. It was already on main before F2.
