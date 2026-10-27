# F1: a filings list that NSE does not answer with a list

**Lane 1, one judge (outside service; the filings archive).** Owner/orchestrator call, 27 Oct 2026.

## What happened
The first full filings-archive run after the R1b1 merge (run 4, 05:14 to 05:56 UTC, 27 Oct 2026) checked all 501 companies and failed
two of them: `FLUOROCHEM` and `JUBLFOOD`, "NSE insurance results list not read: string indices must be integers, not 'str'".
Cause (some evidence: the code, not the body, which was not fetched): `NseLegacyResultsIndex.filings` assumed the answer is a
list. A non-empty object or text gets iterated, a text or key comes back as "row", and `row["periodEnd"]` is a TypeError. An empty
answer already meant "no filings". The parsing is unchanged since the stage-2 split; the resilience work only changed retries.

## Rule (one place: `listed` in `fno/ingestion/filings/index.py`)
- Empty answer (`None`, `[]`, `{}`, `""`): no filings (as before).
- A list: its rows.
- Anything else (an object, text, a number, or a list whose rows are not objects): a `ValueError` that names the list, the shape
  (an object with its first five key names, each cut to 40 characters, or the type name) and never a value. The librarian already records that as the company's failure and goes on to the next company.
- The integrated list is an object with a `data` list: a list instead of the object, or a `data` that is not a list of objects, is
  the same named failure (judge 58 N1: an object in `data` raised an AttributeError that `LIST_ERRORS` does not catch and ended
  the whole run).

An unknown answer is a failure to read, not "no filings": reading it as empty would hide missing data from the archive.

## Pinned by
`tests/ingestion/filings/test_non_list_answers.py` (offline; NSE is never called): object, text and number bodies for the three
lists, empty bodies, a normal list, the integrated list given a list, the failure line holds no value, and a run with one odd
company still checks the next. Nine plants (non-list handed on, non-list read as empty, integrated check removed, the integrated `data` unchecked, rows not
checked to be objects, key names not cut, each of the three lists skipping the check, the line leaking a value) each fail a test.

## Not done
The real body NSE sent for the two companies is unknown; it is not fetched (politeness). The next full run will name its shape in
the failure line.
