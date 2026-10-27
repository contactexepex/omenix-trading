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
