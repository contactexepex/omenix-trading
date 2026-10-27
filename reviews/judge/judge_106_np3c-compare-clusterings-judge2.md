# Judge 106: NP3c compare clusterings (judge #2, code)

**Subject:** `story/NP3c-compare-clusterings` at `d001816`.
- New: `fno/ingestion/news/compare/` (`metrics.py`, `run.py`, `wiring.py`), the CLI `news compare-clusterings`, and
  the dispatch-only workflow `news-compare-clusterings.yml` (`contents: read`).
- Rows J1 to J7.
- Lane 1: a workflow that reads Drive, and output in a public Actions log.

**Gates (locked venv, `__pycache__` cleared):**
- `pytest -q -n auto`: 1981 passed.
- `ruff check` and `ruff format --check`: clean.
- `check_imports`: 628 files clean.
- `test_code_size`: 3 passed.
- `check_numbers`: clean.
- `tools/contract_plants.py`: every plant caught.

**Scope:** in bounds. It measures the pipeline's own clustering (version 1 against version 2) before any cutover,
which judge 96 required. It writes nothing and serves no consumer.

## The question asked: can anything write, or leak a title, key, URL or symbol?

**Write: no** (*strong evidence*).
- `wiring.py` builds only `AreaStore` readers and an `ArticleSource`. There is no `ClusterWriter`, `DataStore`,
  receipt writer or alert sender.
- `run.py` calls only `candidates`, `inputs` and `cluster_articles`.
- The workflow has `contents: read`, no schedule, no commit step and no Slack token.
- A test checks that the Drive and the manifests are unchanged.
- One limit, said plainly: the Drive token is the shared full-scope token, so "read only" is enforced by the code, not
  by the credential. This is the posture `docs/PIPELINE_DESIGN.md` already records, not a new risk.

**Leak, as the code stands: no** (*strong evidence*, every output line read). The five lines are fixed labels and
integers. The error path prints only a fixed code and the exception's class name. `metrics.py` returns counts only.

**Leak, as the tests pin it: not pinned.** The only check on the output is
`"Nifty" not in text and "https://" not in text and "pub.example" not in text` (`test_run_cli_workflow.py:55`). My
plants:

| Plant | Mutation | Result |
| --- | --- | --- |
| L1 | every anchor KEY appended to the v1/v2 line | **survives** (1981 passed) |
| L4 | `coverage` prints its symbol counter (every tagged SYMBOL) to stdout | **survives** (1981 passed) |
| L3 | the error path prints the exception message | caught |

## Blocking

1. **B1: the "counts only" guarantee of a public log is unpinned for keys and symbols.**
   - The story's point is a public Actions log, and the owner's company selection is private. Under L4, every tagged
     company symbol would reach that log with every test green. Under L1, every article key would.
   - **Fix:** one test that runs the comparison and captures all output, the CLI's stdout included, so L4 is covered.
     Assert that every line matches a whitelist of the fixed label words, digits and `:` `,` `-` `>=`. Add a contract
     row with the L1 and L4 plants.

## Notes (not blocking)

- **N1:** the coverage line tags title plus summary, while version 2's bar uses the title only. The docstring says so.
  Read `tagged` as coverage, not as what moves the bar.
- **N2:** the comparison skips the NP7b company-list pin. That is correct, since it writes nothing, and the docstring
  says so.
- **N3:** the run time is unmeasured. It makes one Drive `get` per Google News article in the window, as judge 100 N3
  noted. The first dispatch will show it, and the 30-minute timeout bounds it.

**Verdict: FAIL** (round 1, `d001816`). B1 is one test and one row.

## Addendum 1

**Re-check at `eb0ac05`.** This head was pushed before my round-1 verdict reached the implementer, so I count it as
round 1, not as a second round.

**What it adds:**
- `assert "ZZ" not in text and "Zz" not in text` on `report.line()`;
- plants J8 (a title in the report) and J9 (the dictionary's symbols in the report).

**My B1 plants, re-run at this head:**

| Plant | Mutation | Result |
| --- | --- | --- |
| L1 | every anchor KEY appended to the v1/v2 line | **survives** (1981 passed). A hex key holds no "ZZ" |
| L4 | `coverage` prints its symbol counter to stdout | **survives** (1981 passed). The test reads `report.line()`, never stdout |

The new check is a blacklist of the test's invented names. The whitelist over ALL output that B1 asks for would catch
both plants, and any other name.

**Verdict: FAIL** (round 1 still, `eb0ac05`). B1 is unchanged.
