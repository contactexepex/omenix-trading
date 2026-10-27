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
