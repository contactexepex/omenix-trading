# Judge 524: MS-P1d settlement fixture determinism

Judge B, 23 Oct 2026. Branch `story/ms-p1d-settle-determinism` at fe9350e6 (one commit on main), lane 1.

**Verdict: PASS.** No blocking or should-fix finding.

## Claims vs reality

| Claim | Reality |
|---|---|
| Root cause: `settlement_folder`'s plain-name `writestr` stamps the entry with the wall clock (2 s resolution); the test builds the file twice | True. On Python 3.13, `ZipFile.writestr(str, ...)` builds `ZipInfo(date_time=time.localtime(time.time())[:6])`. `test_each_index_settles_at_intrinsic_against_its_own_price` compares `rests_on` with a second build in `tmp_path / "again"` (line 52), so a 2 s boundary between the builds changes the SHA |
| Fix: the entry is stamped with the file's trading day | True: `ZipInfo(name, (day.year, day.month, day.day, 0, 0, 0))`. With no clock in it, the same arguments give the same bytes |
| Not production | True: the fix touches tests only; there is no `writestr` in `fno/school`, `fno/desk/settlement.py` or `fno/storage/raw_source.py`. The settlement fill hashes the stored bytes |
| New test: two patched clocks give one SHA-256 | True. `zipfile.time` is patched to two times about 3 years apart and the digests are compared |
| Plant (the old plain-name `writestr`) caught | Re-planted by me: `test_the_settlement_fixture_is_the_same_bytes_at_any_wall_clock_time` fails (1 failed, 10 passed); reverted |

## Hunt

- The changed bytes (stored compression, no `0o600` attribute) affect nothing else. The parser reads the member's
  text, and the 11 users of `settlement_folder` (in the execution and accounts tests) all pass.
- Other test fixtures call `writestr` with a plain name (fo_bhavcopy, roads listed contracts, r2_synthetic,
  span_builder, validity_sources, desk and itm_chance settlement, bhavcopy_chains). I checked each for a SHA
  comparison across two builds. None has one: span_builder's `FILE` is built once at import, and the validity record
  hashes are not zip bytes. So no second instance of this flake exists. Note only: they would need the same fixed
  stamp if one ever compares two builds.
- Project rules: files of 58 and 113 lines; the docstrings say why. The story text and the WORK_REGISTER row match
  the diff.

## Gates (run by me on fe9350e6)

13,986 passed, 16 xfailed; ruff clean; format clean; check_imports clean. I ran `tests/school/execution` 10 times
under `-n 4`: 44 passed every time.
