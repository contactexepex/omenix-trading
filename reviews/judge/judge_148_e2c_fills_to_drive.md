# Judge 148: story E2c text (fills, marks and equity history to Drive), `story/e2c-fills-to-drive` cf6da93156530bdf702172b9e819fcdc26c6f9a5 (lane 1, story check under quality rule 1, response 148)

Judge B. The owner's simplicity rule (15 Oct, "Keep the design simple") applies: every finding below is a path the
daily desk run takes, shown in the code on `main`.

**Read:**
- the E2c story text and response 148;
- the owner's row "Per-contract paper fills, marks and equity history move to Drive" ("A: move to Drive");
- ChatGPT review 105 (points 1 and 3) and response 131;
- on `main`, every module that reads or writes a book's account folder (`git grep` for the account paths).

## The orchestrator's question: does the dashboard read model count as "public"? Ruling: no; drop the contract change

- **Where the publisher writes.** `fno/market_read_models/wiring.py:84-88` builds a `PostgresPublisher` on
  `FNO_DB_URL` (Azure `fno.pages_history`). `LocalFolderPublisher` is used only for tests and `--local` dry runs.
  `.github/workflows/market-publish.yml` has no `git add`, no commit and no artifact upload. `market_run.py` prints only
  counts and hashes, so the public Actions logs carry no values.
- **Who can read it.** The dashboard project runs "behind Vercel Authentication" (dashboard `CLAUDE.md`). The public
  gateway project answers 404 for everything except Slack, `/mcp`, OAuth, the brief and the legal pages
  (`web/lib/tools/gateway.ts`), so `/api/v1/...` is not served there.
- **What the decision guards.** Review 105 and response 131 are about rebuilding bids from the **public repository
  record**: journal, scoreboards, decision inputs, alerts and pushed files. The owner's Groww row of 15 Oct allows
  storing and **private display**. A sign-in-only dashboard is private display.
- **So the contract change is not needed.** The scope bullet "The dashboard contract (...) becomes owner-only" and
  acceptance criterion 6 should be dropped. In their place, one Known-limits line: "the read models go only to the
  dashboard's Azure store behind sign-in; P2 or any later job must never commit a page holding these fields to a
  public repository".

## Must-fix (story text)

**1. The private packs would keep publishing the account files.**
- `fno/desk/private_pack.py`: a book's private pack holds "the book's own files as they stand at build time, each with
  its path, SHA-256 and **text**", from `journal/<book>/`, the account folder included.
- E3's `build_pack` step commits `self.packs.files(day)` (`fno/desk/daily_steps.py:85`, committed by
  `daily_run.py:82`), which includes each book's `journal/<book>/packs/<date>/private.json` (`pack_store.py:28`).
- So, after E2c as written, the account folder is downloaded from Drive into the git-ignored local folder. The next
  daily pack then copies `cash_ledger.csv` and `equity_history.csv` (fill prices, cash, marked equity) verbatim into a
  committed file. That is the very leak review 105 named, on the normal daily path.
- **Fix:** add the private packs to E2c's table. Either keep them in Drive beside the account, with the public record
  holding the pack's SHA-256 only, which D3 already uses for evidence; or leave the account files out of the committed
  pack and keep only their hashes there. Add the private pack to criterion 1's committed-file scan.

## Should-fix (story text)

**1. The list of readers misses two that run every day.**
- **T1's card** (`fno/cards/status.py:29`, `:83-100`) reads `journal/<book>/account/positions.json` from the
  **committed** record. After the `git rm`, every card would name each book's account "not committed" and show
  "unknown" trade counts.
- **C4's `LedgerAccounts`** (`fno/checks/validity_account.py`, wired in `fno/checks/wiring.py:91`) reads the local
  cash ledger. Without a download first it fails closed, which is safe but means every entry is refused.
- Also on the list: E1's account CLI (`fno/composition.py`) and the shadow books (in scope; say where they download).
- **Fix:** name these readers. The simplest design is the story's "one shared function", called once at the start of
  each run or command that reads accounts, rather than one per reader.
- C4's replay stays valid on a Drive copy, because C4 already counts only "ledger rows filled by the decision cutoff"
  and the ledger is append-only. One line saying so is enough.

## What is right

- **The leak is a real path.** A public fill plus a public mark gives the bid, and STR1's single-leg structures make
  it reachable. No fill has happened yet, so the move costs no history.
- **The public part is minimal.** `daily_totals.csv` has five columns, holds no marks and no open-position cash, and a
  closed trade's net is not a bid-ask pair (reasoning, stated).
- **One writer.** `DriveAccountSync` replaces `GitAccountSync` behind E3's port, so the git reset logic goes. That is
  simpler.
- **Review 105 point 3.** "A run with no exits step blocks the next session's entries, one alert; exits still run"
  matches response 131's decision. The incident record ChatGPT asked for was "Partial" there and is rightly not built.
- **Known limits are honest:** two concurrent runs, and closed nets.
- **Size:** M is plausible.

**Verdict: FAIL for the story text at cf6da93156530bdf702172b9e819fcdc26c6f9a5**, on must-fix 1 (private packs) and
should-fix 1 (readers), plus the ruling: drop the dashboard contract change. It is text only, and a re-check needs
only the E2c section and response 148.

## Addendum 1 (15 Oct 2026): story text at c62ef47d129eeae867fd84bb719a61c97d1b1a28

**Scope.** 25f83f0 and c62ef47 change only the E2c section and response 148. The merge of `main` (23fef60) brings judge
files only.

| Item | Result | Evidence |
|---|---|---|
| Ruling: dashboard contract change | **APPLIED** | The bullet and criterion 6 are gone. Known limits now say that read models go only to the Azure store behind sign-in, and that no later job may commit such a page publicly |
| Must-fix 1: private packs | **MET** | The table gains `private.json`, which goes to Drive, with only its `.sha256` committed (D3 already records the hash). Book 1's decision reads the downloaded copy to hash it (`book1_inputs.py:42`). Criterion 1's fixture day runs the pack step and scans the packs' folders |
| Should-fix 1: readers | **MET** | One shared download, once per run or command, before any read. The named readers are: E3's daily run (C3 and C4 included), Book 1 with its pack, C4's `LedgerAccounts` (the line on cutoff replay is present), T1's card (now the downloaded folder, not the committed record), E6, scoreboard B, Home, E1's account command and the shadow books. Criterion 3 tests each on a fake Drive store |

Nothing else changed. What judge 148 found right still stands.

**Verdict: PASS for the E2c story text at c62ef47d129eeae867fd84bb719a61c97d1b1a28.** Code may start. The code review
will run criterion 1's committed-file scan on a real fixture day and check that no committed file holds a fill price,
a mark, cash or marked equity.
