# Judge 66: S1 staging cleanup (code), round 1 at f41b1df: FAIL

**Lane 1, two judges; this is judge #1** (a destructive Drive operation, under the write-once Record bar). Branch `story/S1-staging-cleanup`, frozen SHA f41b1df, merge base 91589b1. Story: `docs/stories/S1-staging-cleanup.md`. I wrote this without reading judge #2.

## What holds (strong evidence unless marked)
- **Gates:** ruff, format, check_imports and code size are clean; 1211 passed; contract plants all `ok`. The largest new file is 100 lines.
- **The refactor you asked me to check hardest** (`ArticlePlanner` and `ArticleWriter`). I read it line by line against the old `writer.py`, and it is the same:
  - the same Drive reads in the same order (article path, then the revision path only when the article differs);
  - the same `RawFileConflict` on a revision-name collision;
  - the same NO_OP for a held revision;
  - the same `held[path] = data` after each save.
  - Plants: collision read as a no-op → 1 failed; the writer not updating the held cache → 8 failed.
- **The deleter** (`trash.py`): it builds `staging/...` from validated parts and refuses at the name and again before Drive. It moves to the trash, never deletes outright. The Record writers have no delete.
  - Plants: second gate removed → 12 failed; `staging2` or root accepted → 2 failed; stamp not checked → 1 failed.
- **Report-only default:** no deleter is built without `--apply` (plant: built anyway → 1 failed). The workflow is dispatch only with apply off. `LIMIT` reaches the shell quoted through env. Both concurrency groups match the writers' workflows (`pipeline-staging`, `news-record`).
- **The news proof:**
  - `read_poll` and `parse_poll` drop no item silently: every item is an article or a counted rejection.
  - Plants: the manifest row not required → 1 failed; rejected items ignored → 1 failed.
  - The NO_OP rule is the writer's own.
- **The NSE proof:** "any Record file proves" → 2 failed. The revisions proof is sound because `RevisionArchive.capture` writes the bytes before the index row (`revisions.py`, "bytes first").
- **Age and limit:** an inclusive age boundary → 1 failed; the limit off by one → 1 failed.

## B1 (required; strong evidence from the code, likelihood is some evidence): the NSE proof ignores the manifest row, so a cleanup can remove the gate's only self-heal source

**What the proof checks.** `NseCopyProof` calls a copy promoted when the Record's *Drive bytes* match. The gate's Record is a `FingerprintingStore` (`storage/wiring.py:92`): Drive first, then the manifest row.

**How the gate heals.** A stopped promote run (Drive written, row not written) is healed only by the gate itself, when it finds a staged copy with the held bytes. `gate.py:62-65` re-puts in that case "writes a missing manifest row". With no staged copy left, `promote` returns `NOT_STAGED` at line 54 and the row is never written.

**What the cleanup does to that.** After 7 days it trashes exactly that copy, because Drive holds the same bytes.

**What is left.** The only remaining way to heal is a hand re-run of `stage` plus `promote` over that old date range, with NSE still serving identical bytes. Nothing flags the missing row: `ALREADY_RECORDED` counts as recorded.

**Fix.** Require the manifest fingerprint for the path to equal the copy's SHA-256, as well as the Drive bytes (or the revisions entry). Pin it with a test and a plant. The news proof already does the same with `manifest.has(...)`, so this also makes the two proofs agree on what "PROVEN promoted" means.

## B2 (required, text): the composition root of a destructive operation describes it wrongly

- `staging_cleanup/wiring.py:11-12` says: "News polls are not removed ... They have `KeepForever` until the owner decides." But `proofs()` wires `NewsPollProof`, so news polls *are* removed after promote (owner's choice (b)).
- The story doc's line 49 says the same ("The code has `KeepForever` for news as the default"). Line 53 lists `KeepForever` as built for that purpose.
- CLAUDE.md requires that "the root's docstring says what it wires". Correct both places.

## Minor (not blocking)
- **M1 (some evidence).** The feed-kind check is not pinned. My plant, which gives an unknown feed a kind, passes all 146 tests. The unknown-feed test's articles are not held, so the NO_OP check rejects the poll anyway. That check is what keeps polls the gate left staged on purpose (`feed_unknown`). Give that test held articles, so the kind check is the only guard.
- **M2.** `KeepForever` is now used only by a test. That makes it dead production code: either wire it (for example for an unknown source tag, which `proofs.get` already keeps through `NO_RULE`) or remove it.
- **M3.** `STAGING_ROOT = "staging"` in `trash.py` repeats `STAGING_AREA` from `promotion/wiring.py`. Import it so there is one definition. If the two ever diverged it would fail safe (everything refused), but it is still a duplicate.
- **M4 (reasoning only; it predates S1, and the owner's accepted loss covers it).** `parse_poll` reads Atom entries with `findall`, which takes only direct children. "Every article held" therefore means every item the parser sees; anything else in the raw poll is lost with it, which is within choice (b).

## Hard lines
No order path, no secret, no Groww call, nothing committed by the workflow, and no change to a recorded file. The trash call is the only live Drive write, and it is untested offline. As the implementer states, the first live run must be report only.

## Verdict: FAIL round 1 at f41b1df. B1 and B2 required; M1 to M3 requested.
