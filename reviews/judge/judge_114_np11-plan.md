# Judge 114: NP11 feed provenance (plan doc, privacy focus), round 1 at e050a46: FAIL

**Lane 1 plan, two judges; this is judge #1.** Branch `story/NP11-plan`, frozen SHA e050a46: one file, `docs/stories/NP11-feed-provenance.md` (60 lines). I checked the claims against `main`.

## The central question: storing the join only in private Drive is safe, but the public receipt can confirm it (B1)
**The join really is the secret (strong evidence, code).**
- Article keys are **unsalted** digests of public strings: `keys.py` `_digest("google-news", "guid", guid)` and `_digest("publisher", "url", canonical_url)`. Anyone can compute the key of any public article, so a key in `articles.csv` points to a known news item.
- Planned feed ids are HMAC-hidden `q-` ids (`planning/query_id.py`), and the poll log publishes them.
- So "key K was found by feed `q-…`" says that `q-…` is the query for the company in K's headline. That is **the owner's private company list, recovered one query at a time.**
- The plan is right to keep that join out of git.

**But the public receipt makes a small provenance file guessable (strong evidence for the inputs; the attack is reasoned).**
- Every receipt in git holds the file's **SHA-256 and size** (for example `receipts/data/vix/.../*.sha256`: digest, byte count, time, writer, run id). NP11's files would get the same.
- The file is a **pure function of public facts plus one 3-way choice**: the keys (public), the feed ids (public in the poll log), and the scope (`broad`, `targeted` or `unknown`), serialised with sorted keys.
- Take a **supplement file** (rule 3), written for one late poll from one feed. An observer knows:
  - the late poll's feed id and time, from the poll log;
  - the keys it added, from the same commit's manifest rows;
  - which of 3 scope values applies.
- They build the few candidate files, hash each, and compare with the receipt. A match **confirms the join** for that feed.
- The supplement's **path** carries `sha8`, a plain hash of the pairs, which makes the check easier still: it needs no receipt at all.
- A normal day file is safe only while many feeds poll that day. On a day where one or two feeds ran (early operation, or a single dispatch), the same guess works.
- **So "git gets only a receipt and a manifest row" is not enough by itself.** A receipt of a low-entropy, deterministic private file publishes a confirmable fingerprint of its contents.

**Fix (any one design that keeps determinism; I recommend the first):**
- **(a) Add private entropy that is still deterministic.** Put a field in every provenance file such as `"seal": HMAC-SHA-256(private feed-list salt, day + suffix)`. The bytes stay a pure function of the polls plus a secret, so re-promotion is still a no-op, but no one without the salt can build a candidate.
- Name supplements with a sequence number (`<day>-2.json`) or with the HMAC, **never a plain hash of the pairs**.
- Add a plant: removing the seal must fail a test that a file's SHA cannot be reproduced from (keys, feed ids, scopes) alone.
- (b) The alternative is to keep provenance out of the receipted Record altogether. That breaks the "every Drive file has a receipt" rule, so I do not recommend it.
- **Also say plainly** that the receipt's size leaks the approximate number of pairs. A seal does not hide that; it is a minor leak, so state it rather than fix it.

## B2 (required, text): staging cleanup can delete a day's polls before its provenance file is written
- The day file is built from that day's **staged polls** (rule 1), and it is written only after the day closes (rule 4).
- `staging_cleanup/cleanup.py` trashes staged polls older than `MAX_AGE = timedelta(days=7)` once they are proven promoted. It knows nothing of provenance.
- If no promotion ran in the 7 days after a day closed (say a paused schedule, or a failed run), the polls are trashed with **no provenance file and no alert**: a silent hole.
- **Fix:** either cleanup refuses to trash a closed day's polls until that day's provenance file exists (a new check behind its existing interface), or the provenance writer reports `provenance_polls_missing` for a closed day without a file. Pin it with a row.

## What holds
- **Not an Article field.** It is kept out of `fixed_fields`, so another feed's later poll cannot create a false revision. That is right (judge 111's revision reasoning).
- **The multi-feed set, the union across a day's files, and no rewrites** match the write-once pattern of `news/revisions`.
- **The "unknown" scope is never guessed from the id.** It is reported in its own bucket, so a missing label cannot flatter recall. I agree. The owner's open point 1 (require a scope) is a stricter option, not a need.
- **Counts-only measurement.** It is read-only, `contents: read`, and has a whitelist over every output line, like NP3c (J10, J11). Buckets: broad only, targeted only, both, unknown only, none.
- **The limit is stated plainly.** "Both" proves overlap, not what was missed.
- **Scope rule (CLAUDE.md, owner 27 Oct):** in scope. This is archived derivation, and the measurement is a pipeline tool.

## Notes (not blocking)
- **N1.** The private feed list gains `scope`. Say whether that is a new feed-list format (parse refuses unknown keys today?) and that adding it needs a new feed-list version (the feed pin, NP1/NP3b).
- **N2.** The `provenance.csv` row should carry the path's day, but the size column is the leak noted in B1. State that it is accepted.

## Hard lines
No orders, no Groww, no secret in git. The provenance join must stay unguessable from public data, which is B1.

## Verdict: FAIL round 1 at e050a46. B1 (seal the provenance files with private entropy; no plain-hash supplement names) and B2 (cleanup must not silently remove a day's polls before its provenance exists) required; N1 and N2 requested.
