# Judge 67: S1 staging cleanup (code, lane 1), judge #2 of 2

Frozen SHA `f41b1df` (branch `story/S1-staging-cleanup`). Reviewed `git diff origin/main f41b1df`:
- `staging_cleanup/*`;
- `promotion/staging.py` (`stamps`, `read`, `archive_paths`);
- `news/record/planner.py` and the `writer.py` refactor;
- the workflow, the story, the contract rows and the test edits.

For context I also read `read_poll.py`, `revisions.py` (`capture`), `promotion/wiring.py`, `storage/wiring.py`
(`build_owner_drive_store`) and `feeds.py` (`kinds_ever_listed`). I judged this independently of judge #1.

**Gates (cleared `__pycache__`):** 1211 passed; ruff check and format clean; imports clean (498 files); code size
passed; contract plants all ok.

## Checked and correct (strong evidence, code read and plants)

- **The deleter only reaches `staging/`.** `staged_name` validates the stamp and builds `staging/<source>/<path>/<stamp>`.
  `inside_staging` compares whole path parts, so `staging2`, `Staging`, `staging` alone and `..` are all refused. It
  runs again in `_trash_path` just before Drive. The move is to the trash (`trashed: true`), never a permanent delete.
  - Report-only builds no deleter (`wiring.py:62`).
  - The workflow is dispatch-only, has `apply` off and `contents: read`, and commits nothing.
- **The NSE proof is right.** The Record area is `raw` (`build_owner_drive_store` is `AreaStore(drive, "raw")`), so
  `record.get(copy.path)` is the same path the gate writes. The bytes are compared exactly. The revisions index gets a
  row only after its bytes are stored (`revisions.py:142-143`), so an index row proves the bytes exist. Any error
  keeps the copy.
- **The news proof is right on the cases it names.** `read_poll` returns `items = articles + rejected`, so no item can
  drop out silently. A rejected item, an unknown feed, a non-poll path, a refused poll and a revision-name collision
  are all kept. A kept article also needs its manifest row with the held bytes' digest.
- **The planner refactor matches the old writer.** I compared every branch of the old `write` and `_revision` with
  `plan` plus `write`, and they match:
  - RECORDED: save, then cache the data;
  - NO_OP: document the article file;
  - REVISION: save the revision, then cache it;
  - NO_OP on a revision: document the revision;
  - two versions under one revision name: raise.

  Removing the post-save cache line fails 9 tests.
- **Concurrency.** The NSE job shares `pipeline-staging` with the stage and promote workflow. The news job shares
  `news-record` with news-promote and news-cluster. `news-fetch` only adds new stamps, and the cleanup touches only
  copies older than 7 days.

**My plants: 11 of 14 killed.**

| Plant | Tests failed |
|---|---|
| root check dropped | 8 |
| staging root alone accepted | 2 |
| NSE: any Record file proves | 3 |
| news: a rejected item allowed | 1 |
| news: no manifest row needed | 1 |
| news: no `poll` folder check | 2 |
| a deleter built without `--apply` | 1 |
| a revision collision called NO_OP | 1 |
| the writer's post-save cache line removed | 9 |
| the limit ignored | 1 |
| a doubt in the NSE proof treated as proof | 1 |

Survivors: see F2 for the empty-poll and unreadable plants. "A REVISION or RECORDED plan counted as held" also
survived, but it is equivalent today: `hashlib.sha256(None)` raises `TypeError`, which the proof's catch-all turns into
False. The story declares this mutant equivalent, which is correct, but the safety rests on an exception.

## Findings

1. **F1 (must fix): the owning documents still say news polls are never removed, while the code removes them.**
   - The story's "Decided (orchestrator, 27 Oct 2026) and built" section says: "The code has `KeepForever` for news as
     the default ... **No news poll is removed by this story**" (`S1-staging-cleanup.md:49-50`).
   - The composition root's docstring says: "News polls are not removed ... They have `KeepForever` until the owner
     decides" (`staging_cleanup/wiring.py:11-12`).
   - Both are false at this SHA. `proofs()` (`wiring.py:51-53`) wires `NewsPollProof` for `news`, and the workflow's
     `news-staging` job runs it.

   This is the one irreversible path in the repository, after 30 days in the trash. A reader of the "built" section,
   or of the root that the docstring rule says states what it wires, is told the opposite of what happens.

   Fix in place (the one-owner rule): rewrite those lines to say decision (b) and point to the section below; fix the
   docstring; and correct the "Tests ... Eleven deliberate breaks ... a news poll trashed" line, which describes the
   superseded design.
2. **F2 (should fix): two stated rules have no test.**
   - **"It has at least one article" (`news_proof.py:45`).** Dropping `or not reading.articles` survives the full
     suite. With the check gone, a poll with zero items, which is a feed's "nothing new" observation, would pass
     `all([])` and be trashed. Add a test: an empty poll older than 7 days is kept.
   - **"A read that failed ends the run red" (`cleanup.py:42`, the CLI docstring).** Dropping `UNREADABLE` from
     `ok` survives. Add a test that an unreadable copy makes `ok` False, so the run exits 1 and alerts.
   - Optional: in `_held`, check `plan.held is not None` explicitly rather than relying on `TypeError`.

## Notes (not blocking)

- `build_staging_cleanup` always calls `kinds_ever_listed()` (`wiring.py:63`). A missing or broken feed list
  (`FeedListError`) therefore stops the **NSE** job too, which needs no feed list. Build the news proof only when
  `news` is among the sources.
- Recoverability relies on Drive's ~30-day trash, which the owner's Drive settings or "empty trash" can shorten. The
  story says "about 30 days"; worth one line saying the owner must not empty the trash before checking a run's report.

**Verdict: FAIL** (round 1, `f41b1df`). F1 is a doc and docstring fix; F2 is two small tests. No code defect found.

## Addendum 1: round 2 (final) on `d88f82c`

`git diff f41b1df d88f82c -- fno docs tests`:
- `NseCopyProof` now also needs the manifest row's SHA-256 to equal the copy's (`ArchiveFingerprints`; judge 66 B1);
- `KeepForever` is removed;
- the story's decision text and the `wiring.py` docstring now state owner choice (b) and what it loses;
- there are new tests for an unknown feed and for `STAGING_ROOT == STAGING_AREA`.

The `circulars.yml` and RUN_LOCATIONS lines in the range come from main (CP1 and RR1).

**Gates (cleared `__pycache__`):** 1217 passed; ruff check and format clean; imports clean (499 files); code size passed;
contract plants all ok.

**The new manifest-row check:** correct. It fails closed: no row, or no dataset with a manifest, gives `None`, which never
equals a digest. It is keyed by file name like the existing coverage check and librarian (`manifest_folder.py:61-63`),
so it is no weaker than them.

| Plant | Tests failed |
|---|---|
| row ignored | 3 |
| any row accepted | 2 |

A third plant of mine was invalid (`hashlib` is not imported in `wiring.py`) and is discarded.

**F1:** fixed where it mattered. The "Decided ... and built" text and the composition-root docstring now match the
code. One stale line remains: `S1-staging-cleanup.md:56-58` still lists "a news poll trashed" among the eleven breaks
from the superseded `KeepForever` design. Should-fix: correct it with the next touch of that file.

**F2:** not addressed. Both plants still survive at this SHA:
- dropping `or not reading.articles` (`news_proof.py:45`): an empty poll would be trashed;
- dropping `UNREADABLE` from `CleanupReport.ok` (`cleanup.py:42`): an unreadable copy would not turn the run red.

The code is correct today. It is the protection against a future edit that is missing, so this stays should-fix, not
blocking (as I graded it in round 1). Two tests, recommended before the first `apply` run.

**Verdict: PASS** (`d88f82c`, final round). Open as should-fix: the F2 tests and the one stale line. The orchestrator
decides whether they ride this merge or the next touch.
