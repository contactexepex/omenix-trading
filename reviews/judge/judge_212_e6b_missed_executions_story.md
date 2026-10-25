# Judge 212: E6b story text, missed executions in the scorecards: `story/e6-s2-missed-execution` 0d644e83 (lane 1)

Judge B. The E4c/E4d builder. Claims: `reviews/claude/response_215_e6b-missed-executions.md`. Quality rule 1: story
text only; the code waits for E8 and S6's follow-ups. This judges 0d644e83, the head after S1's notes, not 79364ca1.

## Checks
- **The source:** S1 pending edit (10), which collects ChatGPT reviews 122, 123 and 126. The current gap is confirmed
  in the code: E6's `execution_costs` gives one `not_filled` number with no reason split, and S2's board holds filled
  trades only.
- **One pure counter used three times** (E6, S2, E8's `TimingReport`), with no I/O inside, so S1's freeze hashes no
  desk behaviour. This is the right DRY step: it prevents a third counter.
- **Criterion 1, recomputed by hand.** Seven entries minus 1 gate refusal = 6 opportunities. 3 filled, so the fill
  rate is 50%. 3 misses, so filled + misses = 6. Net per opportunity = (sum of the 3 nets - Rs 120) / 6, since no
  trade is open. Filled-only = sum / 3. Consistent.
- **The definitions are sound** (reasoning only):
  - gate refusals (C2, C3, timing, blocked book) are counted apart and shown beside the block;
  - an unwound partial fill uses its actual C1 net, never 0 (correction a);
  - an open trade is in neither net (correction b);
  - `entry_pending` is outside the denominator until it lands.
- **"Other" is visible:** criterion 3's named-code test makes a new E8 reason without a table entry fail a test.
- **Coordination.** Agreements with E8's builder (misses are `not_opened` with fixed reasons) and with S1/S2/S6's
  builder (their own item, the explicit `frozen_files` path, `book_board.py` only, both corrections) are recorded. The
  S1 item lands with the code, never before. The register row is present. No duplicate.
- **Criteria** cover positive, negative, boundary-like totals, the empty "other", open trades, two strategies and two
  books, E6 equal to S2, no verdict change, and privacy. The "Judge verifies" plants are concrete.

## Notes (not blocking; fold into the code round)
1. **How a reason maps to the table.** E4c and E4d reasons are "`<code>` (`<contract>`, `<units>` units ...)", so the
   counter must match the code before " (", not the whole string.
2. **E4's guard path writes free text.** A guard `not_opened` reads "`<contract>` did not fill: ..." (`entries.py:146`),
   and a guard with legs filled is a separate outcome, `not_opened_partial_fill` (`OUTCOME_PARTIAL_FILL`).
   - Map "partial fill, unwound" to that **outcome**.
   - Map "E4's guard" to the `did not fill:` pattern, or give the guard a code constant in E4 (one line).

   Otherwise both land in "other". Criterion 3's named-code test should cover the guard too.

**Verdict: PASS for 0d644e83 (story text).** Code waits for E8 and S6's follow-ups. Rule 9 (ChatGPT) applies to the
code.

## Addendum 1 (15 Oct 2026): b521bff0, after ChatGPT review 131 (text only)

- **No code changes since 0d644e83.** The diff is the story, review 131, response 215 addendum 1, response 218 and
  README lines.
- **The chain bullet and criterion 9 are consistent and correct.**
  - Decisions → gate refused (by reason, from a named prefix table, unknown as "other") → reached the fill →
    opened / missed / awaiting fill → closed / open. Both counts are stated in words.
  - **The numbers, recomputed:**
    - (9 × 900 − 250) / 10 = Rs 785, and the filled-only average of the nine closes is Rs 900;
    - 22 of 30 = 73.3% hides version 2's 2 of 10 (20%), which is why the cohort filter matters.
  - Open trades: `open_count`, the oldest age, the "closed only, provisional" label, and the printed denominator
    (opportunities minus open).
  - The cohort label and the date and version filter live in the same counter, with no second engine. Still no S1
    verdict change.
- **Judge 212's two notes are folded in:** the reason code is matched before " ("; "partial fill, unwound" is
  `not_opened_partial_fill`; the guard is one named pattern constant and is in criterion 3's named test.

**PASS for b521bff0.**
