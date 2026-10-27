# Judge 82: NP2c resolve pass (code), round 1 at feb5fa9: FAIL

**Lane 1 (outside requests once dispatched, Record writes, a workflow); judge #1.** Branch `story/NP2c-resolve-pass`, frozen SHA feb5fa9. Reviewed `git diff origin/main...feb5fa9`: `resolve/{run,resolution_file,report,cli,wiring}.py`, `news/write_once.py`, `news-resolve.yml`, rows V1 to V12.

## Gates (locked venv; strong evidence)
1556 passed; ruff and check_imports are clean; contract plants all `ok`.

## B1 (required; strong evidence, reproduced): a broken resolver is silent, so links are lost for good with no alert and a green run
- `ResolveReport.ok` is red only on rejections. `needs_attention` adds only `expiring > 0`.
- But `expiring` counts only articles that were **examined** on the last look-back day. Those left unread by `MAX_READS` are counted as `unexamined`, which is never alerted.
- No alert on a high failure share exists anywhere, although NP2b's adapter says "the caller counts codes and alerts on a high error share" (`decoder_adapter.py:94`).
- **Reproduced** with the story's own `World` helpers: a resolver that always answers `decode_failed`, 4 wrapper articles on each of the 4 look-back days, and `MAX_READS` patched to 5 to stand in for 600:

  ```
  news resolve (applied): examined 5, ..., pending 5, backlog 0, expiring 0, unexamined 11, decode_failed 5
  ok True | needs_attention False
  ```

- **At real scale (reasoning, from the plan's numbers):**
  - With the resolver broken, unresolved wrapper articles grow by about 1,280 a day, so the 600 reads are spent on the newest articles within about half a day.
  - The last look-back day is then never examined, `expiring` stays 0, and every link ages out of the 3-day window with **no alert**, while every run is green.
  - Publisher articles (never resolved, re-read on every pass) also use up reads.
  - The probe-then-apply rollout makes this likely: the endpoint is unprobed from a runner (the story's own known limit).
- **Fix, two small rules:**
  1. Raise attention when the resolver asked about links and resolved none (or the failure share is above a stated threshold), and when `paused` repeats.
  2. Count `unexamined` on the last look-back day as `expiring`, or alert on any `unexamined`.
  - Pin both with this scenario as a test, plus a plant.
- **Recommended (some evidence):** skip publisher articles without reading them. The kind is in the article's key path or can be recorded in the manifest, so the read budget goes to wrapper articles.

## What holds (strong evidence)
- **Bounds and plants (each fails a test):**

| Plant | Result |
|---|---|
| cap not clamped to 80 | 1 failed |
| an already resolved key asked again | 1 failed |
| the probe writes | 2 failed |
| the look-back ignored | 1 failed |

- One resolver call per pass (V1). The pass reads only the Record, never Staging.
- **The resolution file:** facts only (URL, host, claimed domain, agreement, resolver), no time, so the same answer gives the same bytes. It is write-once through `WriteOnceWriter`, with the conflict path reported as `resolution_conflict`.
- **The workflow:**
  - dispatch only, so merging requests nothing;
  - `apply` defaults to false;
  - concurrency group `news-record`;
  - the commit runs only with `apply` and through the shared guard;
  - `LIMIT` reaches the shell through env, quoted;
  - a failure alert step is present.
- **The printed line** is counts and fixed codes only.
- **A note for the owner:** the default (no `apply`) is a *probe*, which still sends real paced requests to the service and only skips the write. The workflow comment says so; the dispatch form should say so too.

## Hard lines
No order path, no secret, no Groww call, and nothing requested without a dispatch.

## Verdict: FAIL round 1 at feb5fa9. B1 required.
