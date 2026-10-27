# S1: Staging cleanup, one week

**Lane 1, two judges (a destructive Drive operation and the owner's no-data-loss line).** Owner decision, 27 Oct 2026 (relayed by the
orchestrator): "we don't want to lose any data anymore"; staging copies older than 7 days that are PROVEN promoted are removed.
**Status: built; owner chose (b) for news polls (27 Oct 2026, "Owner decision" below).** Ships dormant (`workflow_dispatch` only); the owner enables it at go-live.

## What is true today (read from the code)
- `RawFileStore` has no delete, by design (the Record is write-once). Staging is a Drive area `staging/`, laid out
  `<source>/<archive path>/<fetch stamp>` (`promotion/staging.py`), one write-once object per fetch; NSE copies are in
  `staging/nse/...`, news polls in `staging/news/<feed>/<Y>/<m>/<d>/poll/<stamp>`. Staging copies carry no receipt.
- A news poll that fails "stays in Staging with its fixed code (never pruned, re-read on every run)" (`news/record/gate.py`). The NSE gate
  keeps failing copies in Staging too (`promotion/gate.py`). Those must survive cleanup.

## Design
1. **A narrow deleter, not a delete on the store.** A new interface `StagingTrash` with one method
   `trash(source, archive_path, stamp)`. It builds `staging/<source>/<archive path>/<stamp>` itself from validated parts (`path_parts`, the
   stamp must parse as a fetch stamp), so a caller cannot hand it a Record path. Its Drive-backed class additionally hard-refuses any full path
   that is not strictly inside `staging/` (`NotStagingPath`), so even a bug that builds a wrong path cannot touch `raw/`, `config/`,
   `data/`, the staging root or a look-alike such as `staging2/`. `RawFileStore` and the Record writers are not changed. The composition
   root's docstring states the limit plainly: this is a property of the code, not of credentials (one Drive credential is shared, as for G7).
2. **Trash, not permanent delete (my recommendation, for the orchestrator to confirm).** The class moves the file to Drive's trash (a
   PATCH `trashed: true`), which Drive keeps for about 30 days and the owner can restore. It removes the file from `staging/` listings, so
   the pipeline no longer sees it, and nothing is lost for good in a mistake. Same "no real delete" spirit as the Record.
3. **Promoted is proven, never inferred from age.** A `PromotedProof` per source decides, from the Record and the manifests:
   - NSE copy: `Record.get(path)` holds the SAME bytes (the promoted copy or an exact duplicate), OR the revisions index lists the copy's
     SHA-256 for that path (a later version the gate kept). Anything else, including a path with no Record file, is kept.
   - News poll: the poll still parses with ZERO rejected items, and EVERY article in it is held by the Record with the same fixed fields
     (the article file, or the revision file for that version) AND has its manifest row (`NewsManifest.has`). It reuses the writer's own
     decision rule (extracted to one shared function so there is one definition, not a copy). One missing article, one parse error, one
     Drive error: the poll is kept.
4. **Age**: strictly older than 7 days by the copy's own fetch stamp against an injected clock (a copy of 7 days less a second is kept).
5. **Behaviour**: report-only by default (`python -m fno staging cleanup`); `--apply` trashes. At most `--limit` copies per run (default
   500) so a run is bounded; counts only in the report and alert (scanned, young, unproven, unreadable, trashed, failed), never a path,
   headline or URL. A trash that fails is counted and the copy stays. It also stops at the first sign the host refuses (shared retry layer).
6. **Workflow** `staging-cleanup.yml`, `workflow_dispatch` only, `apply` input default false. Two jobs, each in the concurrency group of
   the writer it must not race (`news-record` and `pipeline-staging`), so cleanup never runs while a promotion does.

## Plants and tests (all offline; a local folder stands in for Drive)
Must fail a test when planted: a cleanup that trashes an un-promoted copy (proof bypassed); one that trashes a poll with a rejected item or
a missing article; one that trashes a copy younger than 7 days (or exactly 7); a deleter handed a `raw/` (or `config/`, `..`, staging root,
`staging2/`) path that does not hard-refuse; apply mode that is on by default; a failed trash read as success; a path or headline in the report.

## Decided (orchestrator, 27 Oct 2026) and built
- **Trash, not permanent delete**: confirmed. `DriveStagingTrash` PATCHes `trashed: true` (Drive keeps it about 30 days).
- **Keep the newest copy per path regardless of age: no** (the proof covers it).
- **Split by what is lossless.** NSE copies: the Record holds the same bytes, so removing a proven-promoted copy loses nothing: BUILT
  (`NseCopyProof`). News polls: the Record keeps an article's fields (title, summary, canonical link, times), NOT the raw poll, which also holds
  the full body, author, categories and, for wrapper items, the real link. Removing a poll is therefore NOT lossless, so it is the owner's
  decision. Owner chose (b), trash after promote, built as `NewsPollProof` (`news_proof.py`): a poll is trashed only when every article in it is in the Record. What that permanently loses once the 30-day Drive trash expires: the poll's body, author, categories and wrapper-item real links, none of which the Record keeps.
- **Errors are loud, never silent (S1b, contract row E6):** a proof never swallows an error. If it cannot decide (Drive down, a damaged index, a
  bug) `StagingCleanup` keeps the copy, counts `proof_error` and turns the run red with an alert. A damaged staged poll that is not a refused poll
  therefore reds every run until it is fixed; that is intended (an undecidable copy keeps its data and keeps being reported).
- **Before emptying the Drive trash:** read the run's report first. A trashed copy is recoverable for about 30 days; emptying the trash by hand makes
  the removal permanent, and for news polls that is the loss stated above.
- **What cleaning staging does and does not do:** staging is in the private Drive, not in GitHub, so this saves Drive storage only; the
  repository and clone size is the receipts story (R2).
- **Built in `fno/ingestion/staging_cleanup/`**: `trash.py` (the narrow deleter), `proof.py` (`NseCopyProof`, which also needs the manifest row, `PromotedProof`), `cleanup.py`
  (`StagingCleanup`, report-only without a deleter), `wiring.py` (composition root, docstring states the code-level limit), `cli.py`
  (`python -m fno staging cleanup [--apply] [--limit N] [--source TAG]`); `StagingArea` gained read-only `stamps`, `read`, `archive_paths`;
  `.github/workflows/staging-cleanup.yml` is dispatch-only, `apply` off by default, in the `pipeline-staging` concurrency group.
- **Tests** (`tests/ingestion/staging_cleanup/`): 63, offline. Contract rows E1 to E5. Eleven deliberate breaks each fail a test: deleter accepts any
  path, no second check before Drive, stamp not validated, an un-promoted copy proven, any Record file counts (bytes not compared), a doubt
  proves, a news poll trashed while an article is not in the Record, exactly 7 days trashed, age ignored, a failed trash counted as trashed, an already-gone counted as trashed,
  a deleter built without `apply`.
- **Not testable offline:** the real Drive trash call. The first live run is a report-only dispatch by the owner.
- Existing tests edited: the subcommand list and count (`staging`), the pinned-installs count (18 workflows), and the pause-log test's
  "reaches Drive only" list (`staging-cleanup.yml`).

## Owner decision on news polls (27 Oct 2026): (b) trash after promote
**What this permanently loses, stated plainly for the judges and the owner.** The Record keeps an article's fields (key, kind, source, title,
summary, canonical link, times). It does NOT keep the raw poll. Removing a promoted poll therefore loses, once Drive's trash is emptied (about 30 days
after the move; the seven-day wait before the move is on top of that), what the Record never took: the full item body, author, categories, media and,
for wrapper items such as Google News, the REAL link (their canonical link is empty in the Record). The owner accepted this; the 30-day trash softens it.
- `news_proof.py::NewsPollProof` (all safety controls above unchanged): a poll is promoted only if its feed has a kind, it parses whole, NONE of its items
  was rejected, it has at least one article, and EVERY article is already held by the Record exactly as the writer's own rule treats it (`ArticlePlanner`
  says NO_OP, in the article file or the revision file of that version) AND has its manifest row. A poll the gate left staged on purpose (refused,
  rejected item, unknown feed) is therefore kept, as are all polls when the Record cannot be read.
- One definition of the rule: the writer's decision moved to `news/record/planner.py` (`ArticlePlanner.plan`, read only); `ArticleWriter.write` acts on its
  plan. Behaviour unchanged (the existing 280 news tests pass); the contract plants N1, N2, N5 now point at the planner and the writer.
- Workflow: a second job `news-staging` in the `news-record` concurrency group (the NSE job stays in `pipeline-staging`).
- Contract row E4 with a plant; seven further breaks fail tests (two more are equivalent mutants: an unknown feed kind and a non-NO_OP outcome both end in an
  exception that already answers "not promoted").

## Questions for the orchestrator (settled above)
1. Trash (recoverable ~30 days) instead of permanent delete: OK? I recommend it; it is the only place this repository would remove a file.
2. Should the newest staged copy of each path be kept regardless of age? I propose NO (the proof already covers it); say if you prefer yes.
3. I cannot test the real Drive trash call offline; the first live run is a report-only dry run by the owner, then `apply`.
