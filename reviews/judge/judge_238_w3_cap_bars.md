# Judge 238: the W3 integration and the 2.11.0 follow-up (card cap bar, budget shares and tick)

Dashboard `story/w3-cap-bars` at 0971581 (W3 builder 0134MoC6f7aAJVcHRBiyATo6; claims: response_43). It is one commit on
`story/w3-merge-gh` 9e99b89, which is main e425aea (2.11.0, W3e) plus W3f, W3g and W3h. It contains 87af294, d777a54,
2d2a723 and 59ef046, each passed (judges 232, 234-236). Lane 1. Judge D, 16 Oct 2026.

**PASS.** This also covers the `fno-screen.css` re-check I owed once the screens were merged.

| Item | Result | Evidence |
|---|---|---|
| Merged `fno-screen.css` | MET | One file holds `.cards3` (W3e), `.facts2` (W3g), and W3f's `.facts3`, `.chance`, code chips and `.muted`. The 1099 px rule is one rule for `.cols` and `.cards3`. Main's `.strip` (W3a) and W3d's verdict rules are untouched. The new shared tick rule `.chance .base, .cap .bar .tick` replaces weather's own copy, with the same declarations and the same specificity under `:where`. |
| Card cap bar | MET | `maxLossOf` gives `share = min(1, max_loss / max_loss_cap)`. The words, aria label and note use `rs(t.max_loss_cap)` and match mockup 39's wording. A test with a ₹5,000 cap gives bar 79.7 and "80% of the ₹5,000 cap". |
| Budget shares and tick | MET | The tick is `min(100, alert_pct)`, and the cap note, aria label, words and how-to use `share_pct`, `alert_pct` and `stop_pct`. A test with 40, 70 and 90 moves everything, and alert 120 is drawn at the end. **My mutation** `tick: 80` fails 1 test. |
| Changed W3g test | Accepted | The old check, "no 80%, 50% or half in the words", cannot hold once the words say the payload's own shares. It is replaced by (a) the words following the payload (the 40, 70 and 90 test) and (b) a scan of the screen's code, comments stripped, for a literal 50%, 80% or 100% or "half", with a planted copy caught. That guards the same rule, no copy of BG1's numbers in the screen, at its source, the code. It is not looser. |
| Gates on 0971581 | MET | `check_contract` and `check_fno_screens` exit 0, including 2.11's copied-figure check. Code size is OK, `sync-design` is clean, `tsc` passes, `npm test` gives 571/571 (0 skipped), and `next build` exits 0 with all F&O pages built for India. |
| Trial merge with 2.12 (7edaf78) | MET | It merges without conflict and `npm test` gives 571/571. |
