# Judge 257: P11 code, the per-page hold

Trading `story/ph1-page-hold` at abef96fd (P2 builder 013xqaNTCbSBytKgqpfaYFqZ; claims: response 244, addenda 4-7).
abef96fd contains the orchestrator's 30038563 plus the final wording (addendum 7). Story: `docs/stories/P-publishing.md`
"## P11" (text PASS, judge 251 addenda 1-2). Lane 1. Judge D, 16 Oct 2026.

**PASS on the code built. Do not merge yet:** P11's own Depends requires `FnoPageHolds` pinned and `page_holds`
wired before this code merges. On this head `holds_page` is `None`, so a hold would drop or keep a page with no
on-screen notice. Send the pin-and-wiring head; it needs only a short re-check.

| # | Criterion | Result | Evidence |
|---|---|---|---|
| 1 | Only the held page; its row is the previous one byte for byte | MET | `PublicationBuilder` catches `PageHeld` per block, and only that. The held record keeps `as_of`, `cutoff`, `built_at`, `source_commit` and `market`, and takes this publication's id and hash. Test with a held weather page. |
| 2 | One value-free line | MET | `HELD_LINE` is "<day>: <page> held back: <rule>", and each rule is a fixed sentence. A test checks every reason in the code for no digit. |
| 3 | Run status `published` with a reason | MET | `Outcome(PUBLISHED, reason="; ".join(held))`. |
| 4 | No earlier page: absent, the rest publish | MET | Test. |
| 5 | Same-day rerun adds nothing | MET | Test. |
| 6 | Other failures still stop the run | MET | `FiguresNotComputed` and `ContractBroken` still raise to `Stopped` (the existing tests stand). A failed read of the current publication is `PublishFailed`, also a stop. |
| 7 | Local and Azure alike | MET | Both publishers' `current()` read only the current publication (`fno.current_publication` join); the dashboard reads the same way (`web/lib/fno/store.ts`). |
| 8 | Home's two stops are holds | MET | `FnoBooksBlock` and `FnoPicksBlock` are `HeldWithoutRow` (`held()` gives None). **My mutation** making picks a plain `BlockBuilder` fails 1 test. |
| 9 | Held screens say so; no false payload | MET (trading side) | `page_holds_payload` gives `{page_key, since, reason, shows}`, with `since` carried while held and reset after a lift. **My mutation** `since = day` fails 2 tests. Home's two show nothing. The screen side is W3 (judge 256, open: Home's panels). |
| 10 | A held copy that fails the pin: no row, no stop | MET | `_held` catches `ContractBroken` only, records `broken`, and the line says why. **My mutation** catching `KeyError` instead fails 1 test. |
| — | `page_holds` never held | MET | It is built by the publication after every block, and `PageHoldsBlock.build` raises if ever called. |
| — | Gates | MET | On abef96fd: 7110 passed (`-n auto`, Slack token unset), ruff check and format clean, check_imports clean. A trial merge with main conflicts only in reviews/claude/README.md (the known artifact). |

**Notes:**
- A held paged block (`<block>:<parameter>` pages) would keep only its main key. Today's users are all single pages.
  Say so in the code or refuse `PageHeld` from a paged block.
- The tests use `FreePageHolds` (no schema) until 2.13.0 is pinned. The pin head must switch them to the real
  `FnoPageHoldsResponse` check.

## Addendum 1: the pin head 102bd870 (main merged)

**FAIL: one should-fix**, small.

**Met:**
- **The pin:** 2.13.0 at dashboard main d53cefeb. All pinned `api/` files are byte-identical to `git archive d53cefe
  api` (`diff -rq` lists only the unpinned files), including the new `fno-page-holds.yaml`, and `python -m fno market
  contract-check` says "same as the dashboard's".
- **The wiring:** `build_market_run` passes `holds_page=PageHoldsBlock()`, so every publication carries `page_holds`.
- **The tests:** they use the real `FnoPageHoldsResponse` (`FreePageHolds` is gone), and the reason test reads the
  pinned pattern. Holds are ordered as the schema says (since, then page key).
- **A paged block's `PageHeld`** raises a named `TypeError` (tested with P9's chain rows). It is a crash, so the whole
  run stops, which is right for a programming error.
- **Gates on 102bd870:** 7154 passed (`-n auto`, Slack token unset), ruff check and format clean, check_imports clean.
  A trial merge with current main merges WORK_REGISTER cleanly.
- **The builder's stash slip:** checked. The results above are mine, on the committed tree.

## Should-fix: the production wiring is untested

**My mutation:** removing `holds_page=PageHoldsBlock()` from `wiring.py:126` leaves all 212 `tests/market_read_models`
tests passing, because the tests build their own `PublicationBuilder`. That one line is what makes every held screen say
so (criterion 9, the owner's "say so on screen"), and nothing would notice it gone. Add one test that the real
`build_market_run`'s publication builder carries a `PageHoldsBlock`, or that a publish through it writes a `page_holds`
row. The mutation above must then fail.

## Addendum 2: head 1082b285 (the wiring test)

**PASS. P11 may merge.** The new `test_the_daily_runs_publications_carry_page_holds` builds the composition root's own
`build_market_run` (only the Drive rows builder monkeypatched) and checks that its `PublicationBuilder` carries
`PageHoldsBlock`. **My mutation** removing `holds_page=PageHoldsBlock()` from `wiring.py` now fails it. On 1082b285:
7155 passed (`-n auto`), ruff and check_imports clean. The only change since 102bd870 is this test.
