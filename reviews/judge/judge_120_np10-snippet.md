# Judge 120: NP10 page snippet (code), round 1 at cfb87c6: FAIL (one bound)

**Lane 1, two judges; this is judge #1.** Branch `story/NP10-snippet`, frozen SHA cfb87c6. I reviewed `git diff origin/main...cfb87c6`, which touches:
- `reads/snippet.py` (new);
- `reads/extract.py` and `reads/read_file.py`;
- the tests, rows A1 to A7, and Y10.

## Gates (strong evidence)
In a venv installed from `requirements.lock`:
- 2030 passed;
- ruff check is clean, and check_imports is clean;
- **plant runner: 284 of 284 `ok`.**

## B1 (required; strong evidence, timed): the sentence split is quadratic, not "linear" as the docstring says
- `_STOP = re.compile(r"[.!?।]+(?=\s+\S)")`. On a run of stop characters with no space after them, every starting position inside the run grabs the rest of the run and then backtracks through it. That is O(n²) in the run's length.
- **Measured on `summary_extract`, with the body capped at `MAX_SCAN = 20,000`:**

| Body | Time |
|---|---|
| `"." * 20000` | **4.3 s** |
| `"?!" * 10000` | **4.9 s** |
| `"x" + "."*19998 + "x"` | **4.5 s** |
| `"a. " * 6666` (the abbreviation path) | 0.007 s |

- The cap bounds it at about 5 s of CPU per page. But that runs inside the read pass's 900 s budget, outside any per-fetch deadline, and 80 such pages would spend about 400 s. The listed outlets are not hostile, so this is a robustness bound, not an attack; but the story and the docstring claim linear, and the repository has held page-text parsing to hard bounds since judges 78 and 79.
- **Fix, measured:** `re.compile(r"(?<![.!?।])[.!?।]++(?=\s+\S)")`, which only starts at the first stop character of a run and is possessive.
  - All three bodies above drop to **0.0006 s**.
  - The output is unchanged on the A-row sample (`"Profit of Rs. 500 crore. Next sentence here. Third one."`).
  - Possessive alone is not enough: it still took 0.57 s.
- Add a test that times the dots body (or counts steps), and a plant that drops the lookbehind.

## What holds
- **Privacy:**
  - `summary_extract` is `repr=False` on both `PageFacts` and `ReadFile`, so it is never printed, even in a traceback.
  - Y10 walks a planted phrase and finds it only in the read file, never in a report, manifest row, receipt or log.
  - The snippet sits only in the private Drive read file.
- **Bounds:**
  - at most 3 sentences and 600 characters, cut at a word boundary;
  - `MAX_BYTES` is 6,000, and a file over it is refused;
  - a paywalled page and a meta-only page give `""`.
- **Judge 112's B2.** "Rs. 500" stays one sentence: there is no split before a digit or a lower-case letter, nor after a listed abbreviation.
- **Format 2 only, and the Record is empty.** No `reads` manifest or receipt is on `main`, and the merge-procedure check (d) holds the merge if one appears.
- **Text, never instructions.** `html.unescape` runs after tag removal, so `&lt;b&gt;` is stored as the literal text `<b>`. This repository never renders it, and the snippet sets no host, tag or symbol.
- **Scope.** This is what the Record stores; it touches no consumer.

## Hard lines
No orders, no Groww, no secret. No new request, and page text never reaches git or a log.

## Verdict: FAIL round 1 at cfb87c6. B1 required: a linear sentence split (lookbehind plus possessive), with a test and a plant.

## Addendum 1: round 2 at 3793258: PASS

3793258 is cfb87c6 plus the B1 fix, plus `main` merged in (DEL1 and NP9). I reviewed `git diff cfb87c6 3793258 -- reads/snippet.py`. The only code change is that `_STOP` becomes `(?<![.!?।])[.!?।]++(?=\s+\S)`, my measured fix; the docstring now says "linear (a run of stops is matched once)".

**Gates (locked venv, strong evidence).**
- 2005 passed. The count fell from 2030 because the merged DEL1 removed tests.
- ruff check is clean; check_imports is clean.
- **Plant runner: 269 of 269 `ok`.**

**B1 fixed (strong evidence, timed at 3793258).**

| Body | Time |
|---|---|
| `"." * 20000` | 0.0006 s |
| `"?!" * 10000` | 0.0007 s |
| `"x" + dots + "x"` | 0.0006 s |
| `"a. " * 6666` | 0.0073 s |

Row A8 and its plant (every start position tried again) are caught by the runner. The test bound is 0.5 s.

**Verdict: PASS round 2 at 3793258.**
