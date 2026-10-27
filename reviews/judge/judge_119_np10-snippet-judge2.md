# Judge 119: NP10 page snippet (judge #2, code)

**Subject:** `story/NP10-snippet` at `cfb87c6`.
- What it adds:
  - the new `reads/snippet.py`;
  - `PageFacts.summary_extract`, which is `""` for a paywalled page;
  - read file format 2, with `summary_extract` and `MAX_BYTES` 6,000;
  - rows A1 to A7, Y10 (the privacy walk) and Y18 re-pinned.
- The plan passed in judge 112. Lane 1: read-file Record content.

**Gates (locked venv, `__pycache__` cleared):**
- `pytest -q -n auto`: 2030 passed.
- `ruff check` and `ruff format --check`: clean.
- `check_imports`: 638 files clean.
- `test_code_size`: 3 passed.
- `check_numbers`: clean.
- `tools/contract_plants.py`: every plant caught.

## What holds (*strong evidence*)

- **The judge 112 B2 rule is built as planned.** There is no split before a digit or a lower-case letter, and none
  after a listed abbreviation. My reproduction ("...profit of Rs. 500 crore for Q2. Mr. Zz Kumar said ...") gives
  three whole sentences. The danda splits Devanagari text.
- **The bounds hold:** at most 3 sentences and 600 characters, cut at a word boundary. A paywalled page gives `""`,
  and a meta-only page gives `""`, the default.
- **Privacy:** `repr=False` on both new fields, and the Y10 walk.
- **My plants are caught:**
  - the abbreviation check removed: 1 failed;
  - the digit and lower-case check removed: 2 failed;
  - the paywall guard removed: 2 failed;
  - `repr` re-enabled: 2 failed.

## Blocking

1. **B1: an entity-encoded body is stored with its markup** (*strong evidence*, reproduced at `cfb87c6`).
   - `clean()` strips tags BEFORE it unescapes entities: `html.unescape(_TAGS.sub(" ", body))`. So encoded tags become
     real tags only after the stripping has run, and they are stored.
   - Reproduced:

     | `articleBody` | Stored snippet |
     | --- | --- |
     | `&lt;p&gt;Zzalpha Ltd. reported a net profit of Rs. 500 crore.&lt;/p&gt;&lt;p&gt;Shares rose 4%.&lt;/p&gt;` | `<p>Zzalpha Ltd. reported a net profit of Rs. 500 crore.</p><p>Shares rose 4%.</p>` |

   - **Two defects in one result:**
     - markup is stored write-once in the Record, against the plan's row S10 ("tags and entities stripped") and the
       read file's "no HTML";
     - because `.</p><p>S` has no space after the stop, the sentence split never fires, so the bound counts the wrong
       units.
   - The plan itself says `articleBody` "is often HTML or entity text". The existing test uses only real tags plus
     `&amp;`, so it cannot see this.
   - **Fix:**
     - unescape first, then strip tags, then put a space where a tag was. The existing tag-to-space rule already does
       that, so `</p><p>` becomes a sentence break.
     - add a test with an entity-encoded body;
     - add a plant that swaps the order back.

## Notes (not blocking)

- **N1: script and style content.** The text inside `<script>` and `<style>` is kept. The test asserts
  `"<script>x</script>"` becomes `"x"`. JSON-LD `articleBody` rarely carries scripts, *reasoning only*, but dropping the
  content of `script` and `style` elements is cheap and keeps code out of the Record. Consider it with B1.
- **N2:** a body with no sentence stop at all gives its first 600 characters as one "sentence". That is within the
  cap and is acceptable.

**Verdict: FAIL** (round 1, `cfb87c6`). B1 is a two-line order fix plus one test and one plant.

## Addendum 1

**Judge 120's quadratic split.** I read judge 120 only after writing my verdict, and I did not find this myself. I
re-ran it at `cfb87c6`:

| Body | Time in `summary_extract` |
| --- | --- |
| `"." * 20000` | 3.96 s |
| `"a. " * 6666` | 0.006 s |

The finding holds: `_STOP` backtracks over a run of stop characters. I endorse judge 120's B1 and its fix (a
lookbehind plus a possessive quantifier, with a timed test and a plant).

**Where judge 120 and I disagree.** Judge 120 accepts that `&lt;b&gt;` is stored as the literal text `<b>`, and calls
it text, never instructions. I keep my B1 for two reasons:
- the read file's own rule is "no HTML", and the plan's row S10 is "tags and entities stripped";
- the stored `</p><p>` also defeats the sentence split, so the 3-sentence bound counts the wrong units.

That makes it a correctness defect in write-once content, not a safety one. The fix is the order of two calls.

**Verdict: FAIL** (round 1, `cfb87c6`). Both must be fixed:
- my B1, unescape before stripping tags;
- judge 120's B1, the linear split.

## Addendum 2

**Round 2 re-review at `886feb8`.**

**What changed since `cfb87c6`:**
- `clean()` now runs `_TAGS.sub(" ", html.unescape(body[:MAX_SCAN]))`, that is, it unescapes first.
- `_STOP` is linear (judge 120's B1, row A8).
- Row A9 and its plant, plus main merged in (DEL1, NP9).

**Gates (locked venv, `__pycache__` cleared):**
- `pytest -q -n auto`: 2006 passed.
- `ruff check` and `ruff format --check`: clean.
- `check_imports`: 628 files clean.
- `test_code_size`: 3 passed.
- `check_numbers`: clean.
- `tools/contract_plants.py`: every plant caught.

**My B1: fixed.** My example now gives "Zzalpha Ltd. reported a net profit of Rs. 500 crore. Shares rose 4%.": no markup,
and two sentences.

**Judge 120's B1: fixed.**

| Body | Time |
| --- | --- |
| `"." * 20000` | 0.001 s |
| `"&lt;" * 6000` | 0.002 s |
| `"<" * 20000` | 0.001 s |

**Condition C1 (before merge): unescaping first now lets ordinary comparison signs eat text** (*strong evidence*,
reproduced).
- `_TAGS = <[^<>]*>` treats any `<...>` as a tag. A body with encoded comparisons, now decoded, loses the text between
  them:

  | `articleBody` | Stored snippet |
  | --- | --- |
  | "EPS &lt; Rs 5 this year and margin &gt; 10% next." | "EPS 10% next." |

- The result is a false statement stored write-once. It is rare, since comparison signs in prose are uncommon
  (*reasoning only*), but the fix is one character class.
- **Fix:** `_TAGS = re.compile(r"</?[A-Za-z!][^<>]*>")`. A tag starts with a letter, `/` or `!` (comments and
  doctype). I checked it:
  - the comparison sentence is kept whole;
  - `&lt;p&gt;A.&lt;/p&gt;&lt;p&gt;B&lt;/p&gt;` still gives "A. B";
  - `<!-- c -->x<br/>y` gives "x y".
- Add the comparison sentence as a test, and a plant that restores `<[^<>]*>`.

**Script and style (N1): your reply is accepted.** A non-greedy block pattern risks the quadratic case that judge 120
just removed, and what remains after the tag strip is inert words, all within the 600-character cap.

**Verdict: PASS** (round 2, `886feb8`), with condition C1 before merge.

## Addendum 3

**C1 check at `d64710e`.** It is `886feb8` plus C1 (`snippet.py`, a test and plant A10) and judge files from main.

**What I checked:**
- `_TAGS = re.compile(r"</?[A-Za-z!][^<>]*>")`.
- My reproduction:

  | Body | Snippet |
  | --- | --- |
  | "EPS &lt; Rs 5 this year and margin &gt; 10% next." | kept whole |
  | `&lt;p&gt;A.&lt;/p&gt;&lt;p&gt;B&lt;/p&gt;` | "A. B" |
  | `&lt;script&gt;x` | "x" |

**Gates (locked venv, `__pycache__` cleared):**
- `pytest -q -n auto`: 2007 passed.
- `ruff check` and `ruff format --check`: clean.
- `check_imports`: 628 files clean.
- `test_code_size`: 3 passed.
- `check_numbers`: clean.
- **The full plant runner: 271 of 271 `ok`.**

**C1: met. Verdict: PASS** (`d64710e`).
