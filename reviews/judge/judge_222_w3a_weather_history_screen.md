# Judge 222: W3a part 2, the weather history screen (exepex/omenix-dashboard story/w3a-weather-history at f4c2d6e)

**Verdict: PASS.** `npm test` gives **499 passed, 0 failed, 0 skipped** in a read-only clone at f4c2d6e (the claimed
figure).

- **Colour and label only:** `history-view.ts` and `weather-history.tsx` carry no chance, base rate or level. The
  only mention of chances is the comment saying they stay on the weather page. The no-threshold test now also scans
  what the history views say for all three examples.
- **The counts are the backend's:** the view shows `counts` as sent, never re-derived from the sessions. The strips
  are by month, oldest first, sorted by date in the view. "Not scored" says it blocks like RED.
- **India only:** `/india/weather/history` uses the same static-params, `dynamicParams = false` and `notFound`
  pattern, so `/us/weather/history` is a 404. A route test covers it.
- **Judge 221's optional note is taken:** `weather.test.ts` again asserts the whole red-share sentence
  (`assert.equal`), so the 15% limit and "RED still blocks until you approve it" are pinned again.
- **The stated weakening in `screens-import-graph.test.ts`: real, small, accepted, with one tightening suggested.**
  - The test moved from "exactly one reader of a screen's wiring" to "at least one reader, and every reader is a W3
    page loader", because the weather now has two pages (today and history).
  - What the test still catches: a component, adapter or non-loader reading a wiring (the planted component read
    still fails it); a screen with no reader; more than one adapter pick.
  - What it no longer catches: another screen's W3 loader reading the weather's wiring. No concrete harm follows,
    since a page loader may read any screen's published data and nothing private differs by screen, so this is not a
    should-fix.
  - **Suggested tightening:** require each reader to be a loader of a route whose `endpoint` belongs to that screen
    (for example, `routes.ts` entries with `fno/weather*` for `fno-weather`). That keeps "this screen's pages only"
    without a count.
