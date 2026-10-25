# Judge 23: story A9, Drive uploads as the owner, and the historical-data librarian

**Verdict: PASS.** No blocking or should-fix findings; 3 minor findings.

I ran every "judge verifies" step myself against the owner's real Drive:
- the coverage run;
- 5 random participant-OI files hashed;
- a different file planted at an existing path.

I also hashed 6 random files from NSE's live archive against the two new manifests, and checked 3 deliberate breaks
of the code.

**A8 criterion 1, Drive half: now MET** (evidence below). A8's only remaining open item is criterion 3, the 20
measured release days. That is a data wait, not builder work, so A8's issue can close on the Drive side.

**What I judged**
- **Repository:** trading `main` at e11ff87, which contains the A9 commits 260454c, 85d3bac and a6efeb6, and the
  claims commit 13c5cfa.
- **Claims:** `reviews/claude/response_43_2026-10-13-a9-drive-librarian.md`.
- **Story:** `docs/stories/A-data-foundation.md`, section A9.

## Checks run by the judge

```
$ python -m pytest -q                                   671 passed   (claims say 598: later B1 commits added tests)
$ ruff check fno tests tools; python tools/check_imports.py; python tools/check_records.py
                                                        all clean; record scan: clean (393 files)
```

### `python -m fno data-coverage --from 2019-01-01 --to 2026-10-12` (real Drive, read-only service account)

```
dataset                                    from         to expected present missing damaged
nse/derivatives/fo-bhavcopy-legacy   2019-01-01 2024-07-05     1367    1366       0       0
nse/derivatives/fo-bhavcopy          2024-01-01 2026-10-12      690     690       0       0
nse/indices/index-close              2019-01-01 2026-10-12     1929    1929       0       0
nse/derivatives/participant-oi       2019-01-01 2026-10-12     1929    1929       0       0
excepted nse/derivatives/fo-bhavcopy-legacy 2021-03-30: ... 404 from both archive hosts, checked 12 Oct 2026
result: complete
calendar sha256 6101c8746fe17926498fbfcac895b7aad5218c4653982bba82337b6b5dea3961
exit=0
```

This is identical to the builder's run. It is the first exit 0: judge 18's run exited 1, with only 478
participant-OI files present.

### Independent Drive listing

This is my own walker, using the Drive v3 API; only the sign-in token comes from the app.
- **Files under `raw/`:** 5,914, which is A1's 3,985 plus 1,929 participant-OI files.
- **Participant OI per year:** 245, 252, 248, 248, 246, 249, 249 and 192 (2019 to 2026). These equal the session
  counts of the index-close dataset.
- **Duplicate names:** none.
- **Participant-OI names against the manifest:** an exact match, 1,929 = 1,929, with none on either side only.
- **Root of the project folder:** `raw/`, `_probe/` and `evidence/`. `_probe/` is empty, consistent with the claim
  that the probe file was deleted and the folder kept. I did not see the probe file myself: criterion 1 rests on the
  builder's log, my conflict plant below and the 1,929 real uploads. `evidence/` is not A9's; see minor finding 3.

### 5 random participant-OI files (seed 91013): SHA-256 of the Drive bytes against the manifest

`26062023`, `22012021`, `11042019`, `03012023` and `06062022`: all 5 match.

### Conflict plant on the real Drive (production classes, `wiring.build_owner_drive_store()`)

```
before 906 077609a6a5226c92907cff49397c19db6ed3878a657c49fde75a086303986dc0     (= manifest row 2019-04-11)
refused: raw/nse/derivatives/participant-oi/2019/04/fao_participant_oi_11042019.csv already exists in Drive with different content
after  906 077609a6…86dc0 unchanged
same bytes again: no error
```

The code reads the stored file and raises before any write (`google_drive_upload.py:37-41`), so the refusal cannot
leave a partial write.

### The two new manifests against NSE's live archive (seed 1310)

These manifests were made by reading Drive, so on their own they only prove that Drive matches Drive. I checked them
against the source:

| Manifest | Day | HTTP | Bytes (live = manifest) | SHA-256 |
|---|---|---|---|---|
| fo_bhavcopy_legacy | 2020-12-28 | 200 | 479,153 | MATCH |
| fo_bhavcopy_legacy | 2023-10-06 | 200 | 671,135 | MATCH |
| fo_bhavcopy_legacy | 2024-06-27 | 200 | 772,595 | MATCH |
| index_close | 2023-08-14 | 200 | 10,621 | MATCH |
| index_close | 2021-03-24 | 200 | 8,658 | MATCH |
| index_close | 2019-03-01 | 200 | 7,515 | MATCH |

Together with the builder's 10 identical files and my 4 from judge 18, 20 files have been checked against NSE, with
no difference.

### Do the tests bite? Three deliberate breaks (reverted; `git status` clean afterwards)

| Break | Result |
|---|---|
| `GoogleDriveUploadStore.put` never compares the stored bytes (conflict rule off) | `test_drive_upload.py`: 2 fail |
| The librarian ignores a stored file (resume rule off) | `test_librarian.py`: 3 fail, including `test_a_stopped_run_restarted_uploads_only_what_is_missing` |
| `run_librarian` no longer sends the alert on `DriveSignInRefused` | `test_librarian.py`: 2 fail |

### Credentials

For each of `FNO_GDRIVE_OAUTH_CLIENT_ID`, `..._CLIENT_SECRET` and `..._REFRESH_TOKEN`, the shell compared the value
(never printed it) against the working tree and the trees of the last 30 commits: 0 hits each.

## Criteria

| # | Criterion | Judge's own evidence | Result |
|---|---|---|---|
| 1 | A real upload to `_probe/`, read back byte-identical, Drive ID recorded | The builder's log records the ID and the read-back. I saw an empty `_probe/`. The same production `put` path made 1,929 real files whose bytes I hashed (5 of them) and which coverage validated (all of them). | MET |
| 2 | Same bytes change nothing; different bytes raise `RawFileConflict` and change nothing (fake Drive tests and one real check) | Tests pass, and the break test shows they bite. My own real plant was refused, with the file unchanged and a same-bytes save a no-op. | MET |
| 3 | Participant OI 1,929 of 1,929 present, 0 damaged; SHA-256 match the manifest | My coverage run (the validator is `FingerprintCheck` on `manifest_participant_oi.csv`). My 5 random hashes. My listing equals the manifest's names. | MET |
| 4 | A restarted librarian uploads only what is missing (test) | `test_a_stopped_run_restarted_uploads_only_what_is_missing` passes, and the break test shows it bites | MET |
| 5 | An expired or refused token gives a clear error and an alert naming the fix (test) | Tests at `test_librarian.py:131` and `:145` pass, and the break test shows they bite. `SIGN_IN_REFUSED` names the tool and the setting. A real expiry has not happened yet (the builder says so). | MET |
| 6 | No credential value in any file, log or message | My grep: 0 hits. Record scan clean. `tests/conftest.py` removes the Drive secrets from every test. | MET |
| 7 | (Added from judge 18, minor 1) SHA-256 manifests for every NSE dataset | All four datasets are wired to `FingerprintCheck`. The two new manifests have 1,366 and 1,929 rows. My 6 NSE hashes match. | MET |

## Claims vs reality

- **Coverage output:** true, reproduced line for line.
- **"1,929 uploaded":** consistent with my listing and coverage. I did not rerun the 2-hour upload.
- **"598 passed":** true at 13c5cfa as far as I can tell. Main now has 671 because the B1 commits came later; all
  pass.
- **"Largest new file `librarian.py`, about 120 lines":** true (121). `wiring.py` grew to 233 lines; it is not new,
  but it is the largest file A9 touched. Under the limit.
- **The doubts are stated honestly:**
  - the 403 root cause is "some evidence, not proven";
  - the refresh token may expire after 7 days in Testing status;
  - only one writer at a time;
  - `manifest.csv` ends on 9 Oct.
  I agree with each; see minor finding 1 on the last one.

## Engineering standards

- **Interface plus adapter:** `GoogleDriveUploadStore` extends the reader behind `RawFileStore`.
- **DRY:** the shared sign-in and retry rules sit in `drive_session.py`.
- **Composition root:** all wiring is in `fno/storage/wiring.py`.
- **Retry design:** IDs are reserved before each create, which removes duplicate creates at their cause rather than
  catching them afterwards.
- **Sizes:** `drive_session` 92 lines, `owner_token` 48, `google_drive_upload` 81, `librarian` 121, `librarian_cli`
  69, `fingerprints` 78, `fingerprints_cli` 47, `wiring` 233.
- **Breaches:** none found.

## Findings (all minor)

1. **Files after a manifest's last row are checked by content only, and nothing says so.**
   - `FingerprintCheck` (`fno/storage/coverage.py:65-69`) skips the hash when the manifest has no row for a file.
   - Today `manifest.csv` (current-format F&O) ends on 9 Oct 2026, and the index-close and participant-OI manifests
     end on 12 Oct 2026. The old-format dataset is closed (2024-07-05). So 12 Oct for current-format F&O, and every
     new day from 13 Oct in the three live datasets, is unfingerprinted, while coverage still prints "0 damaged" and
     "complete".
   - Expected: the store-side code that saves a new raw file (librarian, library) records its SHA-256 into the
     dataset's manifest. Or, at the least, coverage prints per dataset how many files were checked without a
     fingerprint.
2. **The current-format manifest is still the laptop tool's file**, stopped at 9 Oct. The other three are now
   Drive-made. One way of making every manifest (the `data-fingerprints` command, which appends and never rewrites)
   would remove that split. It overlaps with finding 1.
3. **An unexplained `evidence/` folder sits next to `raw/` in the Drive project folder.**
   - It is not A9's, and probably belongs to X1's evidence.
   - `fno/storage/README.md` describes the layout as `raw/` (plus areas "next to it").
   - Expected: whichever story owns it documents it in that README, so the archive layout stays fully described.
