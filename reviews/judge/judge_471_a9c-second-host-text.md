# Judge 471: A9c, a second NSE archive host, story text (story/oss1-second-host @ 5d6d852e)

Judge F. Round 1 of 2 (owner, row 294). Lane 1 (NSE downloads). Labels: **strong**, **some**, **reasoning only**.

## Verdict: FAIL (1 blocking, 2 minor). A small text fix.

The design is right where it matters:
- the fallback happens only on `RawSourceUnavailable`;
- a refusal or a cooling-off never reaches the second host, which keeps rule 281 item 2 (no getting around a block);
- a 404 stays "not published" and never becomes the second host's answer;
- write times, A11's revision sweep and the in-place snapshot files stay primary-only, each with its reason;
- the evidence is labelled honestly: 8 of 8 datasets byte-identical on one day, and different Akamai edges.

## Blocking

**B1. No gap list (quality rule 2, `docs/JUDGE.md` line 110; still required after row 294).** Map each rule to a
criterion or to Out:
- the owner's rule 281 items 2 and 3 (no getting around a block; paced downloads: the second host gets its own pacer);
- O9 and A10's write-once store with its receipt;
- A8's and A11's point-in-time evidence (Out, with the reason);
- A9b's retry policy (the doubled worst case);
- the morning librarian's 08:50 deadline (FL1-1d step 1b);
- O10's failure row and alert when both hosts fail;
- quality rules 5, 6 and 8.

## Minor

1. **Different bytes from the second host [reasoning only].**
   - Criterion 5 covers "a later primary fetch of the same bytes". It should also say what happens when the bytes
     differ: a stale or newer edge copy kept write-once, then a different primary copy.
   - Name the path: the store's conflict, or A11's revision record, and whether it alerts. Test it.
   - One identical day is some evidence. NSE's 23:20 rewrites (A11) show that the bytes can change.
2. **The morning deadline in numbers.** "The worst case to be stated with the measured number in the claims": put the
   computed worst case in the text now (primary plus secondary retries, from `RETRY_WAITS`, against FL1-1d's 08:50).
   If it can pass 08:50, say what the morning edition does.

Plants: none (text round).

## Addendum 1: round 2 at 7ff35af9

**Verdict: PASS for the A9c story text.** Code may start (no merge before 26 Oct, as the builder states).

| Finding | Answer | Check | Result |
|---|---|---|---|
| B1: no gap list | A 15-row gap list: rule 281 items 2 and 3 (NSE's own public host, the same User-Agent, no login; its own pacer, one try), O9/A10, point-in-time as Out with the reason, A9b, FL1-1d's 08:50, O10, quality rules 5, 6 and 8 | read; each row maps to a criterion or to Out | **Accepted** |
| Minor 2: 08:50 in numbers | The secondary now gets one try (`retry_waits=()`): 660 s per file against 600 s today, not 1,200 s. One file: 08:50:00 (today 08:49); two: 09:01 (today 08:59), before `lab open`'s 09:15 cut-off. Criterion 8 bounds it | The arithmetic follows from `RETRY_WAITS` and the 120 s Retry-After cap [reasoning, checked] | **Accepted**; a better design than mine |
| Minor 1: differing bytes | A later differing primary copy goes through A11's existing revision path (a REVISION line and an index row, no alert). The first copy stays the one readers get, and the manifest URL names the second host. Criterion 9 | Consistent with how a primary rewrite is handled today [reasoning only] | **Accepted** |

For the code round: show criterion 8's request count and pacer key with fakes, and the live `hosts` lines for one day
(quality rule 6).

**Note after addendum 1 (no new number; the builder's correction before any code).** The builder found that the text's
"manifest rows already carry the full URL" is false. I confirmed it: `FingerprintingStore.put`
(`fno/storage/manifest_folder.py`) records `Fingerprint.of(source, path, data)`, built from the class's `url_for`, so
the row always names `nsearchives` [strong]. The proposed fix is accepted:
- a provenance row per second-host fetch in `research/data/manifests/second-host/<dataset>.csv` (path, SHA-256,
  size, URL, fetched_at), committed by the librarian's existing manifest committer;
- criterion 9 is reworded to that row.

Conditions:
- put it in the story text as a short amendment before the code, saying that the manifest row's URL is the canonical
  URL, not the serving host;
- keep `tests/test_fingerprints.py`'s one-folder rule green, or change it only by adding the subfolder to its known
  exceptions, as `revisions/` is.

I check it in the code round; it is not a third text round.
