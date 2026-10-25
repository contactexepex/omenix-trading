# Judge 236: W3h, the F&O scoreboards screen

Dashboard `story/w3h-scoreboards` at d777a54 (W3 builder 0134MoC6f7aAJVcHRBiyATo6; claims: response_42). It is built
from main f4f7f40, on contract 2.10.0 (`FnoScoreboards`), with mockup 42. Story W3, step 8: '"not run yet" until S2/S3
runs exist'; answer (a): scoreboards in Strategies, "A and B as tabs". Lane 1. Judge D, 16 Oct 2026.

**PASS.**

| Criterion | Result | Evidence |
|---|---|---|
| W12 pattern | MET | `lib/fno-scoreboards/` follows the same split. The import-graph test matches route endpoint `fno/scoreboards` to the screen `fno-scoreboards`. The view reuses paper books' `pnlLook`, `rs` and `signedRs` from their pure view (DRY; a view, not a wiring). |
| B and A never combined | MET | `boardsOf` returns two cards, B then A, each with its own question and rows, and no total or winner field. The test checks that 31,730 (the sum of the three nets) appears nowhere. |
| Pilot: no verdict, no yardstick | MET | `beats_do_nothing` null gives no verdict, `do_nothing_net` null gives no yardstick (behind example, board A pilot). |
| Not run | MET | Both boards say "Not run yet" with no rows, matching today's real state (no S2 or S3 run). |
| India only; nav beside the stock tool's page | MET | The build has `/india/fno-scoreboards` and no US page. "F&O scoreboards" (`india: true`) sits beside "Scoreboards (Rule vs AI)", which keeps page `compare` (route test). |
| Tabs vs stacked | Accepted (reasoning only) | Answer (a) said "A and B as tabs", but mockup 42 (judged) stacks them. Stacking shows both questions at once and still never combines them. The owner may prefer tabs. This is a layout choice, not a rule. |
| Gates on d777a54 | MET | `check_contract` and `check_fno_screens` 0, code size OK, `sync-design` clean, `tsc` OK, `npm test` 529/529 (0 skipped), `next build` 0. |

**Note:** the view shows `do_nothing_net` whenever the payload sends it, so the contract's examples, not the screen,
keep a pilot's yardstick null. P2h should send null in a pilot.
