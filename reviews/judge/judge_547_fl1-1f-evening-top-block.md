# Judge 547: FL1-1f, the evening's top block, story/fl1-1f-evening-top-block

- **Judge:** E (session_01HkXMVPDEqVsmJZtghFrGzM), lane 1, round 1 of 2
- **Head judged:** 5460bfcc (it replaces 352a2776 and 4a1cddb4), merged with main for testing; FL1-1e is
  already on main
- **Claims:** docs/stories/FL1-1f-evening-top-block.md
- **Verdict: FAIL.** Two small wording faults in the record line, the part the owner reads for "how good is
  it live". Everything else holds; round 2 needs only a delta check.

## Gates (merged tree 784d2cfd)
- pytest -n auto: 14673 passed, 0 failed.
- ruff check, ruff format --check, check_imports, check_records: clean.

## Findings
1. **F1 (blocking): "Back-test (last 30 days)" does not count what it says.**
   - `today_view.track_record` takes `[p for p in points if not p.live][-30:]`: the last 30 back-tested
     sessions, wherever they fall.
   - The story and model.py's docstring both say "the back-tested sessions among the last 30".
   - Probe: 30 back-filled sessions followed by 10 live ones gives "Back-test (last 30 days): 30 of 30",
     but those sessions are 11 to 40 sessions old. From Monday this drifts by one session every day.
   - Fix one or the other: count the back-tested sessions among the last 30 points, or keep the code and
     word it "Back-test (30 sessions before live)". Pin it with the probe's case.
2. **F2 (blocking, the orchestrator's "live and back-test apart"): the light's colour is mixed.**
   - In "🟢 Live so far: 1 day … | Back-test (last 30 days): 25 of 30", the 🟢 comes from
     `plain.light(index)`, which reads `index.right` of the last 30 points, live and back-tested together.
   - With 1 live day, a green light in front of "Live so far" is almost entirely back-test.
   - Fix: put the light with the part it measures (the 30-day mixed record) or label it there, never in
     front of the live count; pin it.

## Checked and right (code read plus plants)
- **Verdict on the forecast's own edges:**
  - `edge_words` reads q25/q75 and q05/q95 unrounded; VERDICTS is keyed on `inside_90`.
  - Q1 (edges widened by 10, as the rounded words would be) is caught.
  - BANKNIFTY 23 Oct: 221.43 points below 54,509.4, not 212.65 against the rounded 54,500.
- **"Why" lines labelled:** each line is "Day (measured)", "Size (measured)" (the narrow threshold is
  marked reasoning; Q9 caught), "Missed because (measured)" or "Missed (reasoning): no measured cause".
- **No invented cause:** only FL1-1c's measured reasons are shown (Q2 caught). Context is "measured, not
  a cause" (Q4 caught).
- **Context never a placeholder:**
  - With nothing to show it prints either "not available (<reason>)" or "no notable moves in our data"
    (Q3 caught).
  - The evening's GIFT is `not_available`, so morning-only sources are never listed.
- **Live and back-test apart in the counts:** Q5 (back-test counted live) and Q6 (window cut) are caught.
- **Day path:** only levels that were recorded are shown, the evening only, and only from A4h's stamped
  official record (Q10 and Q11 caught).
- **Preview:**
  - It writes nothing: `build_composer` is shared, the composers only read, and no `EditionRun` is built.
  - The morning preview is refused without a sealed record (Q12 caught) or with changed ranges (Q7
    caught).
  - The first line is always the bold DRY RUN label (Q8 caught).
  - It posts only to #fno-forecast through the edition's own poster; would-be alerts are printed, not
    sent.

## Plants: 12 planted, 12 caught. F1 was found by a probe, F2 by reading the code.

## Note
After this merges, the designer's red line should use `no_verdict_words`, so the page gives the reader's
own reason too (judge 538.2).

## Addendum 1

- **Head checked:** b801bc28, round 2 of 2, a delta check of b3586bb4. Merged with main for testing as a1b0f736.
- **Verdict: PASS. Merge go.**
- **Gates:**
  - tests/forecast_lab, tests/school and tests/e2e_acceptance: 3887 passed;
  - ruff check, ruff format --check, check_imports: clean;
  - the builder's full suite: 14,742 passed. The orchestrator's merge run is the one full run.
- **F1 fixed:** the back-test counts the back-tested sessions among the last 30, and its label says so.
  - The round-1 probe (30 back-filled, then 10 live) now reads "Back-test (20 of the last 30 days): 20 of 20".
  - S1 (back to the last 30 back-tested) is caught, 2 failed; S4 (the label always "last 30") is caught.
- **F2 fixed, and more than asked:** the light is rated on live checks only, "⚪ too few live days to rate"
  below 30 live.
  - S2 (rated over the mixed days) is caught, 5 failed.
  - No alert or decision reads the light; `light` and `light_word` are display only (grep).
  - The design page's chip now shows the "Too few live days to rate" pill until 30 live days, which hides
    its mixed counts. That is consistent with the rule; the method line still gives the back-tested count.
- **Minor, not blocking:** S3 (the light over all live checks instead of the newest 30) survived, 3887 passed.
  - It cannot matter before an index has more than 30 live checks, about early December.
  - Pin `live_recent_right` over the newest 30 before then.
