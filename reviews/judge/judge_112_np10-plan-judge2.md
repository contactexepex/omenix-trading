# Judge 112: NP10 page snippet plan (judge #2, plan only)

**Subject:** `story/NP10-plan` at `cb7cae9`, `docs/stories/NP10-page-snippet.md` (48 lines, the only file changed
against main).
- A plan for lane-1 code: it changes read-file Record content and keeps more publisher text. One judge.
- **Scope: in bounds.** The snippet is derived from the fetched page and archived write-once, which is "derive"
  under CLAUDE.md's scope rule. The consumer only reads it downstream; no read contract is defined here.

## The five points asked

- **(a) The privacy walk: sound.**
  - The snippet lives in the private read file only.
  - The planned S9 test walks every report and log string with a planted snippet.
  - The receipt holds the SHA of the file's bytes, and the manifest row holds an id and that SHA. Neither carries the
    text.
- **(b) JSON-LD `articleBody` only, no new dependency: acceptable** (*strong evidence*: `extract.py:98` already reads
  `articleBody`).
  - The unmeasured share of pages that carry it is said plainly and left to the owner. That is right: the first real
    pass will show it.
- **(c) The numbers and the split rule: the split rule fails its own row S3.** See B2.
- **(d) Format 1 to 2 with no compatibility: acceptable** (*strong evidence*). There is no `manifests/news` or
  `receipts/raw/news` on `origin/main`, so no read file exists.
  - The plan's own fallback ("if real reads exist by merge time, read 1 and 2") is the right guard.
  - Make that check part of the code story's merge procedure, not a memory.
- **(e) Rows S1 to S10: complete for the behaviour,** once S3 is restated as in B2.
  - Add one row: a `partial` page (`access == partial`) gives the snippet, or `""`. The plan says what happens to a
    paywalled page, but not to a partial one.

## Blocking

1. **B1: the owner's words are not on record.**
   - The plan quotes the owner (28 Oct 2026, relayed by the orchestrator): "enriched, segregated summary", "never the
     whole news, just a small summary".
   - The conversations folder has no `2026-10-28.md`, and no log on main holds those words. I searched.
   - This flips a standing owner default (E1: no key sentences) and stores more publisher text. It is the same
     provenance rule I applied in judge 104.
   - **Fix:** record the owner's message verbatim, with the decision, in the IST-dated log, and cite it in the plan.
2. **B2: the sentence rule cuts "Rs." and so contradicts S3** (*strong evidence*, reproduced).
   - The rule "split after `.` and space; a piece under 25 characters is joined to the next" protects only a SHORT
     piece.
   - Example: "Zzalpha Ltd reported a net profit of Rs. 500 crore for the quarter. Mr. Zz Kumar said ..." gives three
     "sentences":
     - "...net profit of Rs."
     - "500 crore for the quarter."
     - "Mr. Zz Kumar said ..."
   - So two of the three sentences are spent on one broken sentence. "Rs." is everywhere in Indian business news, and
     the snippet is written once and kept for good.
   - **Fix:** never split when the next non-space character is a digit or a lower-case letter. Also keep a small fixed
     list of abbreviations that do not end a sentence (`Rs.`, `Mr.`, `Mrs.`, `Ms.`, `Dr.`, `Ltd.`, `Co.`, `No.`, `vs.`,
     `Inc.`, `Sr.`, `Jr.`, `St.`).
   - **S3's test:** a long piece ending in "Rs." followed by a number stays one sentence.

## Notes (not blocking)

- **N1:** `MAX_BYTES` of 6,000 is enough. `ensure_ascii=False` writes UTF-8 (`read_file.py:52`), so 600 characters of
  a three-byte script are 1,800 bytes, as the plan says.
- **N2: copyright.** The plan states plainly that storing publisher text is the owner's decision. That is correct, and
  it should stay in the plan's "Open" list until the owner says it in their own words, with B1.

**Verdict: FAIL** (round 1, `cb7cae9`). Both blockers are plan edits:
- B1 is the log entry;
- B2 is two sentences of rule and a restated S3.
