# Judge 301: F1t story text, the AI books' trading runner (story/f1t-ai-trading-runner at 2639b915)

**Verdict: FAIL on the story text (quality rule 1): 4 should-fix findings and 2 minor.** Code may start after the
fixes are pushed and re-checked. The request named e59b50be, but the branch moved to 2639b915 at 11:27, so I judged
2639b915. Since e59b50be the text has adopted the orchestrator's ruling (model "unknown" means no trade), the analyst
cards in the pointer, Book 2's rule default inside its private pack, and the write-path snapshot and restore. Those
are accepted below.

## What I checked myself (strong evidence)
- **Code facts cited by the text: all true on `main`.**
  - `RoutineTrigger` (`fno/pipeline/trigger.py:36`).
  - `Commitment`, `reveal_text`, `open_reveal` (`fno/ai/seal.py:33,61,65`).
  - `GitMainTransport` (`fno/ai/transport.py:30`) and the `PushReceipts` interface (`fno/ai/receipts.py:34`).
  - The stop rule: 2 breaches in the last 20 session days, under one version (`fno/ai/stop_rule.py:13-21`).
  - `PACKED_BOOKS = (BOOK1_RULES,)` (`fno/desk/pack_wiring.py:16`).
  - `collect_decisions` (`fno/desk/daily_steps.py:90`).
  - `--self-timed` (`fno/budget/cli.py:31`).
  - The private pack's per-book allowed folders (`fno/desk/private_pack.py:17-21`).
  - O1 is on `main`, with `book1` between `pack` and `decisions` (`fno/constants_operations.py:44-55`).
  - Timetable: pack at 14:58, retried until 15:10; decision deadline 15:12 (`config.yaml:157-163`).
- **Forecast routine audits** (`research/forecasts/ai_v1/2026/*_audit.json`): the facts are mostly right, with two
  errors (finding 1).

## Findings

**Should-fix 1. The "unknown model means no trade" rule would have blocked 5 of 6 real book-days.** Strong evidence.
`model_reported` was `"unknown"` on 15 Oct (both books) and 16 Oct (Book 2). Only 16 Oct Book 3 reported
`claude-opus-5-5`, with `model_check: match`. The text says "Book 3's model `unverified`", but it was Book 2. Under the
ruling, the forecast record shows 1 usable book-day out of 6, not "one of three days". The text also says the routines
were "fired at 15:10:20 IST", but 14 Oct fired at 19:27:47 IST and failed at the setup script.

Fix:
- Correct both facts.
- Add a way for the decision session to report its served model reliably, plus a criterion. For example, the
  bootstrap prompt has the session read its own model (the session's identity line or its session-description tool)
  and write that exact ID into `model_reported`.
- Measure it on the go-live non-counted fire. Otherwise the fail-closed rule turns most days into
  `model_unverified`, a silent cap on Books 2 and 3 that nobody chose.

**Should-fix 2. Step order cancels the AI books whenever `book1` is slow.** Strong evidence for the order; reasoning
for the effect. O1 runs its steps one after another.
- `ai_fire` sits after `book1`, but needs only the packs. Every second `book1` takes is lost from the AI's window
  (`latest_fire` 15:07).
- `ai_collect` must take observation 1 at 15:10:00, and its "started over 30 s late, so every book is `late`" rule
  fires whenever `book1` runs past 15:10:30. The text allows `book1` up to 600 s.

Fix:
- Place `ai_fire` right after `pack`, before `book1`.
- Either bound `book1` so that `ai_collect` starts by 15:10:30 and show the measured duration, or take observation 1
  independently of the step order.
- Add a boundary test with a slow fake `book1`.

**Should-fix 3. Nobody owns Book 2's and Book 3's fill and exit rules.** Strong evidence. The text adds per-book
`OrderBuilder`/`ExitRules` dispatch only.
- Book 1's `ReplayedOrders` (`fno/books/book1_orders.py:31`) replays D2 against the playbook.
- Book 1's `PlaybookExitRules` (`fno/books/book1_exits.py:34`) takes the time exit decided from the playbook.
- A Book 3 run needs a replay with the AI's picks against registered specs (D5), and exits from the spec. Book 2's
  run needs the envelope choice.
- F6's text (e1994f0a) lists "E4/E8 fills" under F1t. F1t lists the books' decisions under F5 and F6. So both
  implementations fall between the stories.

Fix: name the owner of each book's `OrderBuilder` and `ExitRules` (the natural owners are F5 and F6, who own the
replay), add them to the port table, and make criterion 8 use the real ones once they land.

**Should-fix 4. The public reveal can leak the private account.** Strong evidence for the facts; reasoning for the
risk.
- E2c moved fills, positions and marks to Drive (owner, 15 Oct, "A: move to Drive"): public fills let bid prices be
  rebuilt. The public record keeps per-book daily totals only.
- F1t prints the private pack (account files with fill prices) to the model, then publishes the model's answer
  (`reason` up to 600 characters, Book 3's proposals and shadow reasons) in the public repository as the reveal.
- `.gitignore` covers `.ai_book/` but not the new `.ai_decision/` working folder.

Fix:
- Either keep the reveal in Drive with its hash committed (as O9 does for data), or refuse at `seal` any number token
  in the answer that appears in the private pack's account files. The text should state which.
- Add `.ai_decision/` to `.gitignore`, with a test.

**Minor.**
1. The shape-check name is inconsistent: the design says `check_decision(decision) -> list[str]`, while open question
   1 says Book 2's is `check_answer(obj)`. Pick one name for the port.
2. Depends should list the private-pack hook that writes Book 3's day sheet and Book 2's rule default before the pack
   step (register row "Book 2 pack rule default"; F6 relies on the same hook). Also measure the O5 scan on a full
   fixture pointer: account files that the scan flags would make every day `not_fired`.

## Interfaces with F6, F5 and F2
- Agreed and consistent in both texts: the answer is `{"model_reported", "decision"}` with Book 3's keys inside
  `decision`; `AcceptedDecision` and `DecidedRun`; the registry `model` is `registered_model`; one commit for the
  registration and the run.
- `analyst_cards` comes from F2's `CardsOfDay` with a 30 s bound: consistent with F2 at 47fcb523.
- One contradiction remains, on F6's side (judge 302 should-fix 2): F6 restores "tracked files to HEAD"; F1t restores
  to a snapshot taken just before `decide()`. F1t's rule is the right one, because `research/ledger.csv` is shared
  with the research factory.

## Owner expectations covered
Fail closed on every miss, an alert and a record for each (rows 246-247), and no AI answer reaches a fill without C2
and C4: covered by the judging table and criteria 6, 8 and 10.

## Note: f72abb24 (11:30)
The diff from 2639b915 changes only the Files paragraph (three generic shared pieces in `fno/ai/`) and adds a "Build
rounds" paragraph. Splitting the shared pieces into their own judged round 1 is a sensible split. **The four
should-fix findings above stand unchanged at f72abb24.**

## Addendum 1: f1204a5a

**Verdict: PASS on the story text. Code may start, in the text's two build rounds (round 1 is the shared
`fno/ai/` pieces, judged on their own).** I read the diff from f72abb24 in full; every finding is answered in the
text.

| Finding | Answer at f1204a5a | Judge |
|---|---|---|
| SF1 model reporting, wrong facts | Context corrected (14 Oct at 19:27:47, a setup failure; unknown on 15 Oct both books and 16 Oct Book 2; "1 usable book-day of 6"). `brief` prints a fixed model rule first: the identity line, else the session-description tool, else `unknown`. `seal` refuses anything else. Criterion 3c: a go-live fire reporting `unknown` blocks the live switch | Accepted. Matches the four audit files I read |
| SF2 step order | `ai_fire` right after `pack`, before `book1`. A receipt-observer child process (O1's `Processes`) runs `git ls-remote` at 15:10:00 and 15:11:00, read-only on the remote, writing a git-ignored file. Missing, failed or over 30 s late means every book `late` and `ai_collect` refused. Criterion 3e: a fake `book1` until 15:11:30, and a killed observer | Accepted. `ls-remote` never touches the checkout, so O1's single-thread git rule holds |
| SF3 orders and exits unowned | Port block: owners F5 (Book 2) and F6 (Book 3), with F1t wiring them only; criterion 8 uses fakes until each go-live | Accepted. F6 at b096a4a2 takes Book 3's (judge 302 addendum 1) |
| SF4 public reveal | `seal` and collection refuse any number token (3 or more digits, or with a decimal) from the private account files that is not also in the common pack or public files. The message names the place, never the figure. `.ai_decision/` git-ignored. Criterion 3d with boundaries | Accepted. Drive is impossible without credentials, so option 2 is right; the D3 `reason` is covered too |
| Minor 1, 2 | One name, `check_decision`; the pack hook and F8c are in Depends; the O5 scan of a full fixture pointer and its time are in criterion 2 | Accepted |

New minor findings, for the code round:
1. **Number-token normalisation for 3d.** Indian grouping (`1,25,000`), `Rs`/`₹` prefixes and thousands commas must
   be normalised before tokens are compared. Otherwise `1,25,000` splits into `1`, `25` and `000` and passes the
   3-digit rule. Add those cases to 3d's boundary tests (reasoning only).
2. **A slow `book1` still loses the AI books.** If `book1` ends after 15:12, the AI runs commit after E3's deadline
   and are late. That is correct, fail closed and alerted, but it is a cost. Report `book1`'s measured duration on
   real days in the claims, so S1's timetable can size it.

## Note: 13653f05 (isolation for trading, found by the builder)
The builder found a gap that I also missed. Owner's decision, 14 Oct, "AI books' forecast isolation: `sealed_same_day`
accepted for the forecast contest", condition (3): "trading decisions (slice 4) still need full F1 isolation"
(`docs/DESK_DECISIONS.md` line 72, quoted exactly). F1t uses `sealed_same_day` for trading decisions.

The text now:
- states this in its Context;
- makes the owner's choice a go-live check: (a) `sealed_same_day` for paper trading, labelled, and not scored as an
  independent comparison, or (b) wait;
- has sent the question to the owner through the orchestrator.
No criterion changed, and the code is the same either way. **Accepted; the text PASS stands.** No live switch may be
set before the owner answers.
