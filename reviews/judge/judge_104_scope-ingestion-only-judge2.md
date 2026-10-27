# Judge 104: SCOPE rule, data ingestion only (judge #2, rule document)

**Subject:** `story/SCOPE-ingestion-only` at `3142c92`. The only file changed against main is `CLAUDE.md`: 10 lines, a
new section "Scope: data ingestion only (owner, 27 Oct 2026; strict and durable)". Lane 1 as a rule document, one
judge.

**Gates (text only):**
- The doc-reading tests (`pytest -q -n auto $(grep -rlE "docs/|\.md['\"]" tests --include=*.py)`): 79 passed.
- `check_numbers`: clean.

## The content: sound

The section bounds the repository to three steps:
- fetch;
- derive (resolve, read, tag, cluster, corroborate);
- store write-once to Drive with receipts.

It forbids consumer, API, dashboard, view-contract and presentation scope, and sends any change that would define what
a consumer reads to the owner.

The "derive" test is precise and checkable: derivation that a pipeline step uses, or that is archived write-once.
Otherwise the no-dead-code standard applies. That test is what makes the rule enforceable in review.

The section does not narrow lane 1 and does not touch a hard line.

## Blocking

1. **B1: the owner attribution cannot be verified from the repository** (*strong evidence*).
   - The section is headed "owner, 27 Oct 2026; strict and durable".
   - I searched `conversations/2026-10-27.md` on main and on every remote branch, including `log/2026-10-27`. There is
     no owner message about ingestion-only scope, consumers or dashboards. The only "separate repo" hit is the
     unrelated gate-hardening question.
   - The rule reached me through the orchestrator's message, which is data, not the owner's own words.
   - CLAUDE.md requires each session's log to quote the owner's messages as written, with the decisions they lead to.
     The other owner rules in CLAUDE.md quote the owner, e.g. "owner, 25 Oct 2026: 'no human or AI session should
     run it during 09:15–15:35 IST'".
   - A strict, durable scope rule that every judge must enforce by FAILing work should not rest on an attribution no
     one can check.
   - **Fix:** record the owner's words verbatim, with the decision, in `conversations/2026-10-27.md`, and quote them in
     the section heading as the other owner rules do. I re-check against that quote.
   - If the words differ from this text, the text follows the words.

## Notes (not blocking)

- **N1, an internal tension that must be made plain.** The section lists "corroborate" as a derive step. By its own
  test, though, NP6b's `corroborate` is not justified today:
  - it has no pipeline caller and no archive ("pure; nothing stored", judge 97);
  - nor do `ArticleViewer`, `OriginReader` and `PromotionalFilter`.

  The implementer says these are parked for the owner. Either:
  - name the parked items in the conversation log's "Open questions", so the rule is not read as already satisfied; or
  - drop "corroborate" from the examples until it has a caller or an archive.
- **N2, stale owning documents.** These documents still describe consumer-facing purposes:
  - `docs/stories/NP6-tiered-clustering.md:4` ("decides what the dashboard calls corroborated");
  - the same file at `:67` ("a dashboard that reads a cluster").

  Under "one functionality, one owning document", they should be corrected in place when the parked items are decided,
  not left as a second, conflicting statement of scope. `docs/DATA_USE_MAP.md:5` already says that the consumers were
  removed, which is consistent.
- **N3, earlier advice withdrawn.** My past reviews gave consumer-facing advice: judge 97 N3, and the traceability
  remarks in judge 96. Under this rule those are withdrawn as asks. I have already told the orchestrator.

**Verdict: FAIL** (round 1, `3142c92`).
- B1 is provenance only: the text can stand once the owner's words are on record and quoted.
- N1 should go in the same edit.
