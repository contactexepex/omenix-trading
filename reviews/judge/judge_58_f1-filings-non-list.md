# Judge 58: F1 (a filings list answered with a non-list), judge #1, single judge

**SHA:** `39f38e523eac08b89068366323a81efe909a27ce` (`story/F1-filings-non-list`, base 8417a8b). Lane 1 (NSE reads).
**Verdict: FAIL, round 1 of 2, on one parallel case the fix leaves open.**

## Gates

- Suite: 923 passed, 2 runs out of 2.
- ruff and imports (481 files): clean.

## What holds (strong evidence: code read, plants)

**`listed(body, what)`:**
- an empty answer gives no rows;
- a list is returned as it is;
- anything else raises a `ValueError` naming the list and the shape: up to 5 sorted key names for an object, or the
  type name. It never names a value.

The legacy/insurance and shareholding lists use it. The integrated list checks that its answer is an object.

**The design choice is right:** an unknown non-empty body is a failure to read, not "no filings". Reading it as empty
would silently lose a company's filings for the run. As a failure, it is red, alerted, and retried next run.

`LIST_ERRORS` includes `ValueError` (`librarian.py:38`), so the company fails alone and the run goes on
(`test_one_odd_company_fails_its_own_read_and_the_run_goes_on_to_the_next`).

| Plant | Result |
|---|---|
| A non-list read as empty | caught (3) |
| The legacy list skips `listed` | caught |
| The value put into the message | caught |
| The integrated check removed | caught |

## Required to PASS

### N1. The integrated list's `data` field is still unchecked, and its failure stops the whole run

Reproduced. With `get_json` returning `{"data": {"x": 1, "y": 2}, "totalCount": 5}`,
`NseIntegratedResultsIndex.filings` raises **`AttributeError: 'str' object has no attribute 'get'`**: iterating the
dict yields its keys, which are later used as rows.

`AttributeError` is **not** in `LIST_ERRORS` (`RequestException, RuntimeError, ValueError, KeyError, TypeError`), so it is
not caught per company at `librarian.py:98`. It escapes the company loop and ends the run, so every later company goes
unchecked. That is worse than the bug F1 fixes: the reported TypeError was at least caught per company.

This is the same shape of answer F1 is about, one level down.

Fix: `new = [r for r in listed(answer.get("data"), self.name) if r not in rows]`, plus a test with an object-valued
`data` that asserts a named `ValueError` and that the run goes on.

## Nit, not blocking

The key names in the message are whatever NSE sent. They are public structure, but uncapped in length. Truncating each
name (to about 40 characters) keeps one odd answer from writing a long line into the public log.

## Hard lines

No orders and no secrets. No live NSE call: the tests and my reproduction are offline.

## Addendum 1: round 2 at fbca4e2: PASS

Reviewed `git diff 39f38e5 fbca4e2`. The content commit is 0fd9e2c. The merge commit fbca4e2 only brings in main's judge-58 files (lane 3; checked with `git diff --stat 0fd9e2c fbca4e2`).

**N1 is fixed (strong evidence).**
- The integrated loop now reads `listed(answer.get("data"), self.name)` (`fno/ingestion/filings/index.py:153`).
- `listed` now also requires every row to be an object. This is wider than I asked, and correct: a list of text rows was the same AttributeError path.
- My round-1 reproduction (`{"data": {"x": 1, "y": 2}, "totalCount": 5}`) now gives a named `ValueError` ("not a list of rows").
- The new librarian test shows a bad integrated company recorded as failed while the next one is still checked (`failed == {"BAD"}`).

**Gates at fbca4e2 (strong evidence).**
- ruff, format and check_imports are clean.
- Full suite: 930 passed on the second run.
- On the first run, `tests/ingestion/test_nse_pacer.py::test_after_the_pause_one_probe_goes_alone...` failed once under `-n auto`. The diff does not touch the pacer, and the pacer file then passed 5 times alone plus one full re-run. This is a timing test under parallel load. It is not this change and not a root cause. I note it for whoever owns the pacer tests.
- File sizes: 187, 107 and 31 lines.

**Plants** (PYTHONDONTWRITEBYTECODE=1, each one undone). Every plant is caught:

| Plant | Result |
|---|---|
| integrated `data` unchecked (`answer.get("data") or []`) | 5 failed |
| rows not checked to be objects | 2 failed |
| key names not cut | 1 failed |
| failure line leaks the body | 2 failed |
| any non-list read as empty | 16 failed |

**Nit done.** Key names are cut to `KEY_NAME_LIMIT = 40`, and that is pinned.

**Hard lines.** No order path, no secret, no Groww, and no change to a recorded file or receipt. NSE is never called by the tests.

### N2: needed follow-up, not part of F1 (strong evidence; this predates F1 and is on main)

The same kind of failure is still there one level down, inside a row that is an object.

- The parsers `nse_day`, `nse_time` and `xbrl_link` call `.strip()` or `.startswith()` on whatever NSE puts in a field.
- A non-text value (null, a number, an object, a list or a bool) raises an AttributeError. AttributeError is not in `LIST_ERRORS` (`librarian.py:38`), so it escapes `librarian.py:98` and **ends the whole run**.
- I reproduced this on all four lists with full valid rows, changing one field at a time. 84 cases escape. The fields are:
  - `toDate`, `periodEnd`, `qe_Date` and `date` (null included);
  - `broadCastDate`, `exchdisstime`, `systemDate`, `broadcastDate`, `creation_Date` and `broadcast_Date` (any non-text that is not null);
  - `xbrl` (any non-text that is not null).
- The same probe on `origin/main` gives `"toDate": null` → AttributeError that escapes.
- A `null` period end is a realistic NSE answer.
- Root-cause fix to consider: make the three parsers raise `ValueError` for anything that is not text. Do not just add AttributeError to `LIST_ERRORS`: that would also hide real programming errors.
- I missed this in round 1, because I checked only the list shape. It is outside F1's stated scope, which is the list. F1 makes it no worse.
- I do not FAIL F1 for it in the last round. The orchestrator decides whether it becomes F2 (my recommendation) or is folded in.

**Minor (reasoning only).** `{"data": 0}` or `{"data": false}` reads as "no filings", which is the same as before for empty values. It is not worth any code.

**Verdict: PASS round 2 at fbca4e2. N2 is a needed follow-up story (lane 1).**
