# Judge 217: dashboard contract 2.8.0 (story/fno-contract-2-8 at 5f6ab3c4) and mockups 37, 41-45 (story/fno-mockups-2 at 04ae2091)

Repository exepex/omenix-dashboard, read through a read-only clone; both branches start from main f617139. **Verdict:
FAIL, 2 should-fix.** The contract's checks pass on the mockups head:
- `check_contract`: OpenAPI 3.1 valid; examples valid and current; catalog complete; screen rules hold; every planted
  break caught;
- `check_fno_screens`: 9 pages, 29 Mock examples, every rule holds;
- `check_semantics`, `check_mapping` (zero gaps), `check_stored`, `check_chain` and `check_calendar`: all exit 0.

## The orchestrator's checks

| | Check | Result | Evidence |
|---|---|---|---|
| a | No field carries an input threshold or level | PARTLY | `FnoWeather` and `FnoWeatherHistory` carry no input value, no `reaches` and no level; both list them in `x-never-sent`, and `push` is the sign of the change. But `weather_history` sends colour, probabilities and base rates together, against the strict rule you asked me to apply: should-fix 1 |
| b | No strategy internals; the brake reveals no strategy rule | MET | `accounts[].brake` = the book's loss from its high against `pause_at` (Rs 1,20,000, the owner's published book brake, `risk.profiles.books.drawdown_brake_rs`): a book limit, not a strategy's filter. Shadows carry a display name only ("never its rules") |
| c | Owner-only fields guarded | MET | `open[].alerts` is `x-visibility: owner`, and `fno_rules.py` `OWNER_PATHS` gains `payload.open[].alerts[]`, so the rule check enforces it |
| d | Shadows and books never summed | MET as contract | `shadows[]` is its own array ("never added to a book"); mockup 41 draws one card per book (`2-books.js`: "its own account (never summed)") |
| e | Additions only; `us_overnight` kept and documented | MET, one note | The new fields are additions, but they are added to `required` (`shadows`, `brake`, `alerts`, `recent[].label`, `red_share.basis`, `scores[].exploratory`), so a 2.7.0 payload fails 2.8.0. That is harmless only because no F&O screen page is published yet (story W3); say so in the version note. `us_overnight` stays in the enum, documented "never sent"; nothing stops a producer sending it (note B) |
| f | Example and Mock labels | MET | 29 Mock examples pass the screen rules; each new mockup page carries the Mock labels (34-35 mentions each) |
| g | 45 as its own page; 38 keeps the stock tab | MET, accepted | 38's `changes.md` records the move; 38's F&O example data stays only for the "both books together" line until the web screen draws it from both pages |

## Should-fix

1. **`weather_history` breaks the strict weather rule it is meant to wait on.**
   - **The conflict:** `FnoWeatherHistory` requires, per session, `colour`, `p_big_1d`, `p_big_5d`, `base_rate_1d` and
     `base_rate_5d`. Its own header says "whether the colour and the probabilities are shown together waits for the
     owner's choice (story W3, rule 4)". Yet the schema already requires both, and the Mock examples show both.
   - **Why it matters:** story W3 rule 4 (judge 216 addendum 3) says that under (b), private from now on, the history
     page drops either the probabilities or the colour. Over about 2,400 sessions, colour plus p plus b give
     `colour.py`'s floors and multiples back. You asked me to judge to the strict rule until the owner answers.
   - **Fix, either:**
     - (i) ship 2.8.0's `weather_history` in its strict form, keeping colour and label and leaving the probabilities
       and base rates out (or the reverse), and add the other half in a later minor version if the owner answers
       (a); or
     - (ii) hold `weather_history` out of 2.8.0 until the owner answers.

     Today's `weather` page (one day: colour, p, b and `times_usual`) does not allow a read-back on its own. Its
     `recent[]` carries colour only.
2. **Mockup 37's rebuild drops the owner's requested features without saying so.**
   - **What the owner asked for:** the replaced 37 (5f6ab3c4) was a "third draft for the owner's sign-off" built from
     two rounds of the owner's feedback (13 Oct). It had today's predictions on top and the past below, overall
     ranked cards, a period you choose with a table and a race chart, "what made the difference" story cards, and
     which family is best at which prediction.
   - **What the rebuild has:** only a forecaster table and one card per question; the race, period, why and overall
     files are deleted. Its notes and rationale do not mention the feedback rounds or what was dropped.
   - **Fix:** in 37's notes, list each owner request from the 13 Oct rounds as kept, changed (and how) or dropped (and
     why: for example, not in `FnoForecastLab` yet), so the owner signs off knowingly. Or keep the requested views
     drawn from the catalog's fields.

## Notes (not should-fix)

- **A.** The version note should state that 2.8.0's new required fields reject a 2.7.0 payload, and that no
  F&O screen page is published yet.
- **B.** `us_overnight` stays a valid enum value although it is "never sent". Add one rule to `check_fno_screens.py`
  (or the P2 page test) that no payload driver is `us_overnight`, so the documentation is enforced.
- **C.** `design/mockups/_platform/forecast_data.py` is deleted. `git grep` on 04ae2091 finds no remaining user of it
  (only 37's notes mention it), so the deletion is safe.

## Addendum 1: contract 39d1829 and mockups f04cb50 (response 225)

**Verdict: PASS.** Both should-fixes and both notes are closed.

- **Should-fix 1.** `FnoWeatherHistory` rows now require only `session`, `colour` and `label`. The chances and the
  usual chances are removed and listed in `x-never-sent`, with the reason: beside the colours they would give the
  colour rule's floors back. A later minor version adds them only if the owner chooses (a). This is the strict form.
- **Should-fix 2.** Mockup 37's notes now carry a table of each owner request from 13 Oct:
  - kept: "lab", plain language, today on top and the past below, which family is best at which prediction, the
    official statistics folded;
  - changed, with reasons: ranked within each question only, since Brier and QLIKE do not add; settle dates per
    question;
  - dropped for now, with the reason (the contract has no per-day or per-period series) and a 2.9 proposal: the
    "what made the difference" cards and the period chooser with its race chart.

  The JS now has today, best, questions and forecasters views. The owner can sign off knowingly.
- **Note A.** The version note now says 2.8.0's required fields reject a 2.7 payload, which is harmless because no
  F&O screen page is published yet.
- **Note B.** `fno_rules.check_never_sent_values` fails any `getFnoWeather` example with a driver `us_overnight`. The
  page side is P2a's test (judge 218 addendum 1).
- **Gates.**
  - f04cb50: `check_contract`, `check_fno_screens` ("9 pages, 29 Mock examples… every rule holds"),
    `check_semantics`, `check_mapping` and `check_stored` all exit 0.
  - The contract branch alone (39d1829): `check_contract` and `check_fno_screens` exit 0. Its `MOCKUPS` list ending
    at 41 is as intended.
