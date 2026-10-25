# Judge 484: MS-P1g, the 08:50 and 20:05 sections

**Scope:** story/ms-p1-sections at 947cc128 (builder session_01WeFYCqffRe7et1nfSJyuv5), diff 756e6545..947cc128 only.
Story MS-market-school.md part g and its Claims. Lane 1 (Slack reports, signed-off pages). Round 1 of 2. Judge H
(session_01KNkZVoWvXMkoihKrrXk5Xa).

**Verdict: FAIL.** 2 should-fix, 2 minor.

## Criteria
| # | Criterion | Result | Evidence |
|---|---|---|---|
| 1 | Flag off: both editions byte-identical (golden) | MET | I regenerated from main (da92f2f2) with main's `ReportMaker`. Text SHA-256 `0296402b...` (morning) and `9629028f...` (evening), and the html and png hashes, equal the goldens. With the flag off the wrapper returns the same object, so the real `build_report_maker` is unchanged |
| 2 | Flag on: sections appear, say Paper | MET | test; plant (Paper label removed) caught |
| 3 | No green reachable | MET | `Banner` has 2 members (a); both banner-rule plants caught |
| 4 | A planted refusal appears in the evening | MET | plants (problems removed, closures dropped) caught |
| 5 | No contract, strike or card internal | MET | privacy test plants strikes, expiry, bid, premium and hashes; the lines print codes, rupees and counts only |
| 6 | NSE-terms line and no-latency label in both | MET | `lines.footer`; plant caught |
| - | page_wiring touched in 2 lines only | MET | `git diff --stat`: 2 insertions, 1 deletion (the import and the `return`) |
| - | Controls never shown as candidates; tickets never summed | MET in the lines, NOT in the banner | finding 2 |
| - | Flag on before j: plain edition plus one alert | MET | `test_a_flag_turned_on_before_the_inputs_are_wired...`; `_NotWired` raises inside `render`, which is guarded |
| - | Gates | MET | pytest -n auto: 10,295 passed, 16 xfailed. ruff check/format, check_imports and check_records are clean. Largest file is 58 lines |

## Findings
1. **Should-fix: the school can stop both editions.**
   - `with_school_sections` runs `school_settings(load_app_config())` when the maker is built (`wiring.py:34`),
     outside the guard in `maker.py`.
   - My run: `first_counted: "2026-13-01"`, an unknown key, or no `school` block each raise `SchoolSettingsError`.
     `build_edition` then fails inside `cli.guarded`, so the 08:50 or 20:05 edition is not posted, only an alert.
     Before this part, nothing in the lab read the `school` block.
   - Likewise the top-level import in `page_wiring.py:14` loads the school package when `cli.py:46` imports, which is
     outside `guarded`.
   - The orchestrator's rule, "a failing section cannot stop an edition", is broken at build time. The risk is
     lowered, not removed, by CI's real-config test: the block is about to change (h's `first_counted`).
   - Expected: any failure reading the school settings (and building the sections) gives the plain maker plus one
     alert, with a test that plants a bad block. Import the school wiring inside the guarded path.
2. **Should-fix: the evening counts controls as candidates and as the fleet's rupees.**
   - `evening.py:29` counts every `trade` or `ticket` decision as a candidate, controls included. My run: only N0
     trades, and the evening banner is AMBER. The morning, for the same case, is RED, because it filters by role.
   - RC1 and REF fire every open session, so the evening banner can never be red for "no candidate". This is against
     story 3.2: "PS5, KL1, RC1 and N0 are never ... shown as candidates".
   - The same run prints "Trades closed: none" and then "Fleet total: Rs +5,000": the headline rupees are a control's.
   - Expected: candidates are rule drivers only (`role_of`), with a test. The fleet total is over the rule drivers
     shown, or it says plainly that it includes the controls, as the orchestrator decides.

**Minor:**
- (a) No test shows the real `build_report_maker` wraps with the sections: removing `with_school_sections` from
  `page_wiring.py` survived.
- (b) The section-failure alert repeats the exception's message. A `KeyError` of a contract key would put a strike in
  #fno-desk. Name the class only, or a fixed text.

## Plants
15 planted, 14 caught; the survivor is minor (a). The png hash is the test camera's constant (the same for both
editions); the real picture is covered by the unwrapped-maker identity, not by the hash.

## Notes
- The goldens come from the forecast-lab test fakes, not a live edition. Identity (`is maker`) is the stronger
  proof, and it holds.

## Addendum 1

**Round 2 of 2:** story/ms-p1-sections at 5a7bd5b7, diff 947cc128..5a7bd5b7. **Verdict: PASS.** Lane 1.

**Gates (my run):** pytest -n auto: 10,316 passed, 16 xfailed. ruff check/format, check_imports and check_records
are clean. `fno/forecast_lab/` still has 2 lines changed against a (the import, now of `guard`, and the `return`).

**Round-1 findings:**
1. **School stops an edition: ACCEPTED.**
   - Settings and wiring are now read inside `guard.with_school_sections`'s `try`.
   - My three plants (a bad date, an unknown key, no block) on both editions give text byte-identical to the golden,
     plus one alert `school <edition> section not made (SchoolSettingsError)`.
   - Importing `page_wiring` now loads only `fno.school.contracts.reports`, `reports.guard` and `reports.maker`
     (checked with `sys.modules`).
   - Plant caught: the guard narrowed to `ImportError`.
2. **Controls in the evening: ACCEPTED (orchestrator's ruling: rule drivers only).**
   - My case (only N0 trades, Rs +5,000) is now RED, with "Fleet total, rule drivers only: Rs +0". The control's
     net is on its own labelled line, "not in the fleet total".
   - Plants caught: the role filter on candidates, the total summed over all money, and the other-roles lines.

**Minors:**
- (a) **ACCEPTED:** a test runs the real `build_report_maker` through the guard.
- (b) **ACCEPTED:** the alert carries the class only (plant putting the message back caught).

**Orchestrator's check (Judge B's note):** `fno/school/reports/` has no `requests`, no HTTP and no Slack client. The
sections reach Slack only as text in FL1's `Made`, and their alerts go through the composers' `alerts`.

**Plants:** 6 on the new code, 6 caught.

**Note:** `guard.py`'s docstring says it loads "nothing of the school": it loads `maker`, and so
`contracts.reports`, which is stdlib-only since a's round 2. Wording only.
