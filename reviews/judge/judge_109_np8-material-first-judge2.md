# Judge 109: NP8 material-first reads (judge #2, code)

**Subject:** `story/NP8-material-first-reads`, asked at `e6aac2a` and re-checked at the current head `18f9111`.
- Since `e6aac2a`, the head adds judge 108's M18 and M19 and a constructor change for `sha256`; the rest is main merged
  in.
- What the story adds:
  - `reads/order.py`, `queue.py`, `plan.py`, `pass_note.py` and `links.py`;
  - the shared `news/pin.py`;
  - the wiring;
  - the `news-read-pages.yml` manifest and receipt paths;
  - rows M1 to M19.
- Lane 1: private files, a new write-once Record file and a workflow.

## Gates (locked venv, `__pycache__` cleared)

- `pytest -q -n auto`: 2001 passed at `e6aac2a`, 2018 at `18f9111`.
- `ruff check`, `ruff format --check`, `check_imports`, `test_code_size` and `check_numbers`: clean.
- **`tools/contract_plants.py` is RED at both SHAs:** `Y4: the plant went unnoticed: the claim is no longer pinned`.
  CLAUDE.md lists the contract plants among the gates that must pass before `main`.

## The three points asked

1. **No title, symbol or term in the note or the line: holds** (*strong evidence*).
   - `PassNote` is three counts, two versions and two SHA-256s. `parse_note` refuses any other key.
   - `ReadReport.line()` prints only fixed count names and the order name.
   - `Scored` holds titles in memory only.
   - The `read-passes.csv` row holds the SHA of the note's bytes, not of the private files.
2. **The degrade paths never move the pin: holds** (*strong evidence*, `plan.py:65-97` and `run.py:611`).
   - Every one of these returns `NewestFirst` with no note, so nothing is written:
     - a store error;
     - a refusal;
     - a used-then-missing file;
     - an unreadable last note.
   - A probe writes no note either.
   - My plants P1 (a refused file still used), P2 (missing-after-use accepted), P3 (unavailable silent), P10 (the
     OLDEST note compared), P11 (an unreadable note ignored) and P13 (a note on a probe) are all caught.
3. **The shared `pin.py`: correct.**
   - It is the NP7b rule exactly, with `last_version == 0` meaning nothing to compare.
   - The cluster run's behaviour is unchanged: `_refuse_going_behind` delegates to it, and NP7b's Z17 and Z18 plants
     are re-pointed and caught.

## Blocking

1. **B1: the contract gate is red (Y4), and the 80-page cap is not pinned on the new path** (*strong evidence*).
   - `min(pages, PAGES)` now appears twice in `reads/run.py`: line 72, the material-first path, and line 74, the old
     path.
   - The plant runner replaces the FIRST occurrence (`tools/contract_plants.py:52`). Y4 therefore mutates the
     material-first path, which Y4's test never takes.
   - I confirmed it directly at both SHAs: removing the cap on the material-first path (`queue.candidates(today, pages,
     report)`) passes the full suite, 2001 and 2018 passed.
   - So "at most 80 pages per run" is unpinned on the path the owner's materiality file switches on.
   - **Fix:**
     - a material-first test that asks for more than 80 pages and gets 80;
     - Y4 pointed at both occurrences: either a second row for the material path, or one `min(pages, PAGES)` computed
       once before the branch, which also removes the duplicate.
2. **B2: nothing pins that production wires the planner** (*strong evidence*).
   - My plant P12 passes `None` for the planner in `reads/wiring.py`. With it, every production pass reads newest first
     forever, the materiality file has no effect again (the gap NP8 exists to close), and no note is written. The full
     suite passes at both SHAs.
   - **Fix:** a wiring test asserting that `build_read_pass` gives a `ReadPass` whose `planner` is a `ReadPlanner` and
     whose `notes` is a `PassNotes`. Add a contract row with the P12 plant.

## Notes (not blocking)

- **N1 (P14 survives):** `MaterialFirst.material` passes `article.source` to the tagger, and no test pins it. Without
  the source, an outlet suffix (judge 92 F2) could make a story material and push it up the read order.
  - The effect is ordering only, not the Record, so this is not blocking.
  - Add a test in the next push that touches these files.
- **N2: the company-list degrade.** The plan proposed degrade-and-alert for the company list too, and judge 108 accepted
  it. I agree, with *reasoning only*: here the list orders reads and archives nothing. The hard stop stays in the
  version 2 cluster run.
- **N3: judge 108's PASS at `18f9111`.** It was given with the contract gate red (Y4). I raise this so the orchestrator
  does not merge on two PASSes while a CLAUDE.md gate fails.

**Verdict: FAIL** (round 1; at `e6aac2a`, and the same at `18f9111`). B1 and B2 are each one test and one row, and B1
can also remove a duplicate expression.
