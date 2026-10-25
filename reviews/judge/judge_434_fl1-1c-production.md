# Judge 434: FL1-1c production pieces (story/fl1-html-report at 2ed6405e)

**Verdict: FAIL: 4 should-fix findings and 3 minor.** Each fix is small. The pipeline is well built: one page model
feeds the text, the picture and the file; there is one write-once record; and a picture failure gets an alert, never
silence. The visual design is out of scope, as stated, and `lab_close` stays null.

## Checked myself
- **Gates:** on 2ed6405e merged with today's `main` (no conflicts), one run:
  - 9,018 passed, 17 xfailed;
  - `ruff check` clean; 1,687 files formatted;
  - imports clean; record scan clean (7,379 files).

  Strong evidence.
- **12 planted mutations: 10 caught.**
  - Caught: flows' direction ignored; Slack `ok:false` counted as sent; end-of-day back-fill preferred over live; a
    picture failure without its alert; the files not stored in the record; an upload refusal ignored; the VIX limit
    at 20%; facts read after the report day; amber at 23; inward rounding.
  - Survived: 2 (minor 1).
- **The builder's four points:**
  1. **Direction-aware flows: accepted.** A flow counts only when its sign matches the miss
     (`reasons.py: (net > 0) == above`), and the mutation is caught. Strong evidence.
  2. **The double post: accepted.** T1's "accepted, no readable ts" outcome lacked the may-have-posted words. The new
     `Delivery.may_have_posted` is explicit. One path is untested (minor 1).
  3. **Today's issue shown once written, before its seal shows: accepted.** It is display only. FL1-1's seal checks
     still judge it, and scoring needs the seal. Reasoning only.
  4. **One write-once record holding the message and both files: accepted.** Mutation Q6 is caught.

## Findings

**Should-fix 1. The owner's one signal counts back-tested days as if they were live.** Strong evidence: code.
- `plain.record_words` prints "right X of the last Y days", and `light()` colours it. In `builder._index` the record
  is the best method's last 30 N1 points from `G13bHistory`, which falls back to G13b's 3 pm or end-of-day back-fill
  wherever no live row exists.
- On go-live day all 30 are back-fill. Many are end-of-day back-fill, a different basis from the live 3 pm method
  (judge 416 should-fix 3: back-fill is "some evidence", not strong).
- The Slack line, which the owner reads first, does not say any of this. Only the details file shows `live_days`.
- Fix: say it in the line itself until the window is all live, for example "right 27 of the last 30 days
  (26 back-tested)". Keep the light, or show it as "Too few live days", as the owner prefers. The details label each
  point "back-tested" or "live".

**Should-fix 2. The page's history pools G13b's method versions.**
- `G13bHistory.points` picks one row per (forecaster, horizon, target day) across method SHAs.
- `_records` keys bands by (label, issue day), so a band from one method version can be paired with another
  version's score.
- G13b's score rows carry `method_sha256` (judge 416.1, FL1-1's scoreboard keys on it). This code ignores it.
- It is latent today: one method SHA per back-fill label in Drive. It becomes real at G13b's first method change.
- Fix: key both on `method_sha256`, show the current method's record only (or one record per version), and add a
  two-version test. Strong evidence: code.

**Should-fix 3. The picture depends on Pillow, which is declared nowhere.**
- `camera.trim` imports PIL. Pillow is in neither `requirements.txt` nor `requirements-groww.txt`, so O7's routine
  setup never installs or checks it.
- It works today only because this container image ships Pillow 12.3.0. If the image changes, every day becomes a
  "picture not made" alert, losing the owner's chosen picture.
- Fix: add Pillow to `requirements.txt`, and so to O7's import check. Strong evidence: grep and the image.

**Should-fix 4. An 8,443-line data file in the public repository.**
- `docs/previews/fl1-html-report/pageview-2026-10-19.json` holds real derived G13b back-fill records: implied
  quantiles from the 3 pm chains, and closes. The two preview HTML files embed the same numbers.
- CLAUDE.md: "Every data file (fetched or derived) lives write-once in Google Drive ... GitHub keeps code, docs and
  one SHA-256 receipt". No code or test reads these files.
- Fix: remove the JSON (put it in Drive with a receipt if it is still needed), and keep the previews with synthetic
  numbers or with a pointer to the Drive copy. Strong evidence: the rule and the file.

**Minor.**
1. **Two survivors:**
   - Q2: a `ValueError` (unreadable JSON) after `completeUploadExternal` is not marked may-have-posted. The code is
     right; no test covers it, and it is exactly a double-post path. Add one.
   - Q10: history up to and including today's target. Harmless at 15:45, because today's close is not archived yet.
     Add a boundary assertion.
2. **The headline method is picked on the same history it is scored on.** The page should say so: "lowest error on
   its own history". The selection itself is IL's selector question.
3. **`ConnectionError` counts as may-have-posted.** That is conservative, but response 301 says a refused connection
   "is retried", and only `ConnectTimeout` is. Align the text with the code.

## Addendum 1: 996e3b2e (response 306)

**Verdict: PASS (lane 1). The builder may merge: pull, one full run on the merged tree, push.** `lab_close` stays
null until the owner signs off the design.

**Gates:** on 996e3b2e merged with today's `main` (no conflicts), one run:
- 9,024 passed, 17 xfailed;
- `ruff check` clean; 1,687 files formatted;
- imports clean; record scan clean (7,384 files).

Strong evidence.

| Finding | Answer | Judge (evidence) |
|---|---|---|
| SF1 back-tested days shown as live | `IndexView.backtested`; the line reads "right X of the last 30 days (N back-tested)" | Accepted. Mutations caught: the words dropped, the count inverted. Strong |
| SF2 method versions pooled | Only the current version counts, the version behind the newest record with live first; score rows and bands are both filtered to it; bands are keyed (label, day, issue) | Accepted. Mutations caught: the score filter off, bands from any version, the newest pick preferring end-of-day. I also checked that today's `method_sha256()` is `8d7d7301`, the same as both back-fill folders' version, so history carries over at go-live. Strong |
| SF3 Pillow undeclared | `Pillow>=10.0` added to `requirements.txt`; not added to O7's hard import probe | Accepted, the probe push-back included: a missing Pillow costs only the picture, with its alert, never the report. Reasoning only |
| SF4 data file in the repository | The JSON is removed; the previews are rebuilt from synthetic numbers through the real builder | Accepted. None of the real figures I checked (for example 22,871 or 22,536) is left in the preview HTML. See the note below on the branch |
| Minors | Q2 and Q10 tests; the "lowest error on its own history" wording; response 301's retry text corrected | Accepted. Both earlier survivors are now caught (R6, R7) |

**Note on the squash merge.** A squash merge keeps the JSON out of `main`'s history. That is acceptable, because the
gates run on the squashed tree as usual. The file still exists at 2ed6405e on the public branch until the branch is
deleted. It holds derived back-fill numbers, not raw restricted data (row 281), so deleting the branch after the merge
is advised, not required. No history rewrite is needed.
