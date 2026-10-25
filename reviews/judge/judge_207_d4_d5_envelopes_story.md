# Judge 207: stories D4 (Book 2's authority envelope) and D5 (Book 3's constitution and registry), story text (judge F)

**Commit judged:** `0cb5234d` on `story/d4-d5-envelopes`. Claims: response 204. Builder:
session_01SFDjjZx7JYziM3jqJytG2z. Lane 1 (new stories; text only, owner 16 Oct: "D4/D5 text only, no AI cost").

**Verdict: FAIL (text).** 2 should fix and 2 minor. The cut-down envelope v1, the reuse of D6 for hashes (no new
register), C4 plugging in at one line each and D1's format for Book 3's specs are all sound and checked.

## The orchestrator's checks
- **No owner override on paper (strong evidence).**
  - Neither D4's action enum nor D5 has any owner action.
  - Design v2 03, rule 5 (`03_layers_factory_desk.md:121-123`), and `REPLAN.md:41` drop owner overrides on paper; only
    S1's safety stop remains.
  - D3 still carries `owner_override` (`decision_record.py:21-25`). The builder raises that honestly as owner
    question 4; it is outside D4/D5. Accepted as a slot.
  - C5b's brake restarts (`owner_overrides.csv`, `restart_brake`) restart a safety brake. They do not override a
    trade, so they do not conflict with the rule.
- **Numbers reference C2's limits, not copies (strong evidence).**
  - D5's constitution holds `risk: risk.profiles.books` and `scoring: PROTOCOL.md` as references, and criterion 6
    refuses a number in their place.
  - D4 sets no number of its own: lots and widths come from the version.
  - The two constitution values (21 days, the structure list) are design 12.3's own limits on what Book 3 may
    invent. They are not C2's risk limits.
  - The conflict the builder reports (3 open trades and Rs 30,000 in DESK_DESIGN 12.4 and S1, against
    `config.yaml`'s Rs 1,20,000 brake and no open-trade limit, `config.yaml:45-52`) is real. It is S1's to settle.
    D4/D5 work with either figure.
- **The five owner questions are slots.** Each has a recommendation and its evidence level, and none blocks the text.
  Q3's evidence is checked: only monthly NIFTY expiries are recorded and priced.

## Claims checked (strong evidence: code read on main)
1. The only machine exit is the time exit (`exit_terms.py:1-6`), and strikes are set by code
   (`structure_spec.py:30`). So envelope v1's cut is correct.
2. `delay` is `no_trade` under E3's fixed timetable (deadline 15:12): correct.
3. D6 treats served components as a free mapping and pauses scoring on any difference (`versions.py:93-101`), so no
   new register is needed: correct.
4. `validity_modes()` maps Books 2 and 3 to `WaitsFor` (`checks/wiring.py:72-80`): one line each, correct.
5. D6's `_registered_before` is strictly before (`versions.py:70-76`): reused, correct.
6. D3's `served` takes any non-empty named string (`decision_record.py:146-148`): correct.

## Should fix
1. **The envelope's D6 component key does not fit `choose_strategy`.**
   - D4 has "one envelope per playbook version", with "the envelope's SHA-256 is a D6 component
     (`components["envelope"]`)". That is one key for Book 2's version.
   - `choose_strategy` only matters when two or more `paper` versions are eligible, which means two or more envelope
     files. One key cannot hold both, and the text does not say whose envelope governs when the AI picks version B
     over the rule default A.
   - The word "envelope" is also already taken in Book 2: Hybrid's forecast envelope (`fno/ai/envelope.py`,
     `ai/versions.py:26` `envelope_width`). A shared D6 key would be ambiguous once Book 2's forecast versions
     register in D6.
   - Fix (simplest of the two):
     - (a) one trade envelope per Book 2 version (a book-level file listing the playbook versions it covers), or
     - (b) a key per playbook version, such as `trade_envelope:<version_id>`.
   - In either case, `permits` checks the envelope of the version actually traded. Add a test where A and B are both
     eligible with different envelope statuses.
2. **A `shadow-only` action's credit on scoreboard A has no reader.**
   - D4 says the shadow action is "recorded as Book 2's shadow action for scoreboard A (S3 reads it as Book 2's action
     there)". But S3's `action_of` reads only `record["decision"]` (`matched_actions.py:61-70`), and `decision` is the
     account's action, the rule default.
   - Design 12.2 requires the shadow-only action to be scored on scoreboard A. As written, nothing scores it, and
     S3's passed code would silently score the rule default instead.
   - Fix: add an S3 reading change to Depends and to the gap list (through the orchestrator to S3's builder), with
     the record field it reads (`chosen_action` with status shadow). Or say plainly that shadow-only is not scored
     until that change.

## Minor
1. **D5 `proposed_on`:** say that `register()` sets it from the clock on the registration day and never takes it
   from the AI's spec. Otherwise "proposed on an earlier session" rests on a value the proposer writes. With the
   strict-ancestor commit check this is a small hole, but one line closes it.
2. **The new `ValidityProposal` fields** (`action`, `rule_default`, `strategy_id`) live in C4's file. Put "C4 owner
   agreement" in Depends for both stories, not only in response 204 and the register row.

## Addendum 1: revision at e40a5d7d (docs only)

**Verdict: PASS (text).** Code waits for slice E's trigger. The branch diff against main is the D section, response
204, its README row and the register row.

| Finding | Fix | Judge's check | Result |
|---|---|---|---|
| SF1 envelope key | One D6 component per playbook version, `trade_envelope:<name>-v<n>`, with the same key in `served`. The traded version's envelope governs every action of the trade, `choose_strategy` included. Criterion 8 tests A and B both eligible with differing envelopes | It fits D6's free component mapping (`versions.py`); there is no clash with Hybrid's `envelope`; the governing rule is testable | Fixed |
| SF2 shadow-only scoring | Recorded with status `shadow`, listed and unscored until S3 reads it. S3's change is in Depends and the gap list; criterion 3 forbids scoring the rule default under the AI's name | It matches `matched_actions.action_of` as built, and the gap is explicit | Fixed |
| m1 `proposed_on` | Set by `register()` from the IST clock; a spec's own earlier date is replaced (test in criterion 1) | | Fixed |
| m2 C4 owner agreement | In both stories' Depends | | Fixed |

- The owner's five answers are written in from `DESK_DECISIONS.md` row 229 ("Accept all five (Recommended)"), and
  the text quotes it.
- D3's refusal of `owner_override` is recorded as a slice E code item: consistent with "never override on paper".
- Risk and scoring stay C2 and S1 references.

## Addendum 2: after ChatGPT review 130 (a7b3a0d2)

**Verdict: PASS (text).**
- **Text only:** `git diff origin/main...a7b3a0d2` changes 7 files, all docs and reviews (the D section, response
  204, responses 210 and 212's request, review 130, the READMEs and the register row). The `fno/` changes seen
  against e40a5d7d come from main's merge, not this branch.
- **Matches response 212's five points:**
  1. **Estimand:** "AI veto and width selection within the same registered playbook"; veto rate and width changes
     shown; a zero difference reads "inconclusive". In D4.
  2. **Trial family:** every registered Book 3 strategy enters the G0-G6 trial ledger and family; confirmatory
     claims belong only to a frozen selection policy; no cap and no wait. D5 criterion 8 tests two prior-session
     variants.
  3. **C4's check:** D4 criterion 9 checks the eligible set, the trade_envelope hash against D6 and `served`, and
     the action, with the A-forbids/B-allows fixture. As 212 states, there is no "default must also permit" rule.
  4. **Universe label:** "monthly NIFTY defined-risk strategies with planned time exits of at most 21 days". In D5.
  5. **Order of D3's refusal:** D3's `owner_override` refusal is built before any Book 2 or 3 paper decision (D4's
     gap-list row).
- Nothing else changed in the stories. Addendum 1's PASS stands.
