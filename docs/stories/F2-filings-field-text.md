# F2: a filings row field that is not text

**Lane 1, one judge (outside service; the filings archive).** Orchestrator call, 27 Oct 2026, from judge 58 N2 (strong evidence,
reproduced on main).

## What could happen
F1 made a list that is not a list of objects a named failure. A row that IS an object can still carry a field that is not text
(`"toDate": null`, `xbrl: 5`, `broadCastDate: {}`). `nse_day`, `nse_time` and `xbrl_link` call `.strip()` or `.startswith()` on it, which
is an AttributeError. The librarian catches only `LIST_ERRORS` (no AttributeError), so one such row would end the whole run and leave
every later company unchecked (84 field and value cases over the four lists, reproduced by the judge). Not seen live yet.

## Rule (`text_field` and `required_text` in `fno/ingestion/filings/index.py`)
Every field of a row is read through one of two functions:
- `text_field(row, name)`: the text, or `None` when the field is absent or null (as before: a missing XBRL link or time is how NSE
  says "none"). A number, boolean, object or list is a `ValueError` "field NAME: NSE sent TYPE, not text": the field name and the
  type, never the value.
- `required_text(row, name)`: the same, and `None` is also a `ValueError` ("NSE sent none"). Used for the period date of each list
  (`toDate`/`periodEnd`, `qe_Date`, `date`), which a filing cannot do without (a missing key used to be a KeyError).
A field we cannot read is a failure of that company's read, surfaced and retried by the next run, never dropped and never a crash.
`ValueError` is already in the librarian's `LIST_ERRORS`; widening that to AttributeError would hide real bugs, so it is not widened.

## Follow-up (T1, judge 58 minor)
A field that is text but not a date or time NSE writes (`time_field`, `day_field`) is a ValueError "field NAME: not a date in NSE's format": Python's own message quoted the text, which broke this story's "field and type, never the value" rule.

## Pinned by
`tests/ingestion/filings/test_non_text_fields.py` (offline): for each of five list shapes (classic, insurance, classic without times,
integrated, shareholding) and every field, each of six non-text values gives the named ValueError; a null or missing period date is
named; a null link is still a filing without a file; the old rows judged by their link alone; the message holds no value; and a run
with one null-date row still checks the next company. Nine plants (non-text read as absent, no type check, null date read as empty,
`xbrl` unchecked at each of the two sites that matter, `consolidated` unchecked, the message leaking the value) each fail tests.
