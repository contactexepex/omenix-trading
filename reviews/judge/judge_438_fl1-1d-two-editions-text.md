# Judge 438: FL1-1d story text, the report in two editions (story/fl1-1d-two-editions at 6aabc36d)

**Verdict: FAIL on the story text: 1 should-fix finding and 4 minor.** It is close. The design matches the owner's
decisions, reuses FL1-1/1c, adds no schedule, and states its limits honestly. The one gap is the rule that keeps stale
data off the page: it is not defined per source, and as written it contradicts itself on Brent.

The orchestrator named f17ba85b; the builder moved to ca0db83e (the 1d-1/1d-2 split), then 439e9846 (A17's
agreement), then 6aabc36d (A22 timing). I judged 6aabc36d.

## Checked myself (strong evidence)
- **Owner decisions matched:**
  - row 284 (forecast before the open, check after the close; two editions, both indices);
  - bcbbc454 (08:50, new owner tasks, US closes shown, repository public);
  - f9737bce (one page per edition, 2-4 key points);
  - row 287 (evening about 20:05, start 19:53; "anything not dated today shows 'not out yet'");
  - 50a79a43 (restricted data in Drive only; US values in Slack and Drive only, never in a repository file,
    fixtures included).

  The page model must feed 0f00ee6a's fixed chart set. That set belongs to the designer's renderer; FL1-1d supplies
  its data (timeline, month outcomes, rolling share, misses, levels). The "Correct / Close call" wording is left to
  the designer's branch, as the orchestrator asked.
- **The VIX push-back is true.**
  - No file in `fno/price_ranges/` or `fno/price_distribution/` mentions VIX, Brent, USD/INR, GIFT or `global_cues`
    (grep).
  - The one outside import that forecasts, G7's `Ewma` (`fno/forecast_v4_rules/baselines.py`), takes the
    `close_proxy_rv` series, built from past closes.
  - The implied range uses option prices. VIX is "context", not "used". Strong evidence: code.
- **No new schedule.**
  - The two routines are the owner's new tasks (bcbbc454).
  - The release check's 17:00-19:53 part is explicitly not built.
  - FII/DII timing is proposed to A8's owner, not added.
- **One builder per function.** Every fetch stays the owning story's command, run unchanged with its owner's
  agreement, and A17 is read-only (agreed). O1's `lab_close` removal follows O1's owner's 4 conditions.

## Finding

**Should-fix 1. "Never stale" needs a per-source expected date; as written it contradicts itself.** Strong evidence:
the text.
- Design item 3 says "a section whose data is not dated for the session it describes shows 'not out yet'".
  Criterion 3 says "never an older value", and row 287 says "anything not dated today shows 'not out yet'".
- The Day 1 table says Brent and USD/INR show "yes, with its own print date". A17's Brent prints lag by days
  (EIA), so under the stated rule Brent would almost always be "not out yet", or the rule would be broken.
- The morning US closes describe the previous US session, so "the session it describes" is ambiguous there too.
- Fix: give each Section its **expected as-of rule** in a table:
  - US closes: the last US session before today's IST open;
  - Brent: the latest print no more than N days old, shown with its date as "last print";
  - USD/INR (RBI): the latest reference rate up to the previous session;
  - evening levels and flows: today only;
  - VIX: the previous session's official value in the morning, today's live value in the evening.

  Anything outside its rule shows "not out yet". Add a test per rule, which criterion 3 then covers.

## Minor
1. **A wrong citation.** "c3231785: forecast before the open, check after the close" points at a merge commit that
   only adds a number claim. The decision is DESK_DECISIONS row 284. Cite the row, or its commit.
2. **Item 9's first line says the check "polls every 10 minutes from 17:00 to 21:00"**, while the same item says the
   17:00-19:53 part is not built. Lead with what is built: inside the evening routine, from 19:53.
3. **The morning `index-close` fetch** (`data-librarian index-close`) belongs to another story's owner, who is
   missing from "Before code starts, each owner agrees". Add that owner.
4. **The two new routines need their stored prompts and a CLAUDE.md section.** Row 284: "the owner creates it; steps
   from the orchestrator". Name who writes the CLAUDE.md section, and make it a go-live condition, as FL1-1 did.

## Split check
1d-1 (design items 1, 2, 4 in part, 7 and 8; criteria 1, 2, 5, 6 and 7) stands on its own; none of its criteria needs
a Section. The should-fix sits in 1d-2's Sections, so 1d-1's code could start once this text passes.

## Addendum 1: dfacef5a (response 307)

**Verdict: PASS on the story text (lane 1). FL1-1d-1's code may start.** The diff from 6aabc36d to dfacef5a, apart
from `main` merged in, changes only `docs/stories/FL1-1d-two-editions.md`.

| Finding | Answer | Judge |
|---|---|---|
| SF1 per-source expected dates | A table, one rule per Section: closes, VIX, US closes, USD/INR, Brent, events, the bhavcopy levels, participant OI and the flows; morning and evening each have their own rule and label. A value outside its rule is "not out yet" in the evening and "not available" in the morning, never shown as current. One test per rule (criterion 3) | Accepted. Brent becomes "last print" up to 10 calendar days old, labelled with its date, and the text states that the limit is a choice, not evidence. US closes are the last US session before D's 09:15, so a US holiday shows the earlier session with its date. Reasoning only for the 10 days; the rule is honest |
| Minor 1 citation | DESK_DECISIONS lines 284 and 287 | Accepted |
| Minor 2 item 9 | It now leads with what is built (inside the evening routine, from 19:53) | Accepted |
| Minor 3 index-close owner | Added: the A9 librarian's command; O6 archives the same file at 21:11 | Accepted |
| Minor 4 routines | "Go-live conditions": the FL1 builder writes the CLAUDE.md sections in 1d-1 (lane 1); the owner creates both tasks from response 304's prompts, and no session creates them; the design sign-off; a first live run checked against its record | Accepted |

**Note for the owner.** The FL1 builder could not delete `story/fl1-html-report` after FL1-1c's squash merge
(45c72f6f), because the session's proxy drops branch deletes. Its commit 2ed6405e still holds the derived preview
data (judge 434 should-fix 4). Deleting it in GitHub (Branches → delete) is advised, not required.

## Note: 2b2c5724 (12 lines added to 1d-2's design)
The commit adds two things:
- **Miss reasons over 30 sessions, up from 7.** FL1-1c's `reasons()` looks up each fact for the miss day itself
  (`facts.flows.get(day)`, the VIX of that day and the day before, events up to that day, and the last two prints
  before it). So widening the window keeps every reason as known on its own day. Accepted.
- **Two librarian rules:**
  - a librarian "not published" exit shows "not out yet", with no alert. It must be told apart from other exit-1
    errors by the librarian's own outcome text; test that in 1d-2;
  - a manifest push race follows item 8's pull-and-retry-once rule.

  Accepted (reasoning only, as labelled).

1d-1 is unchanged. **The PASS of addendum 1 stands at 2b2c5724.**
