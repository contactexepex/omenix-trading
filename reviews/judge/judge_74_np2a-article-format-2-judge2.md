# Judge 74: NP2a article format 2 (code, lane 1), judge #2 of 2

Frozen SHA `20c8c32` (branch `story/NP2a-article-format-2`, stacked on NP1 `df3fe62`). I read the story first, then
reviewed `git diff df3fe62 20c8c32`:
- `article_file.py`, `source_facts.py`, `parse_feed.py`, `raw_item.py`;
- `cluster_record/article_source.py`, `record/planner.py`;
- the tests, contract rows F1-F8 and their plants.

I judged this independently of judge #1.

**Gates (cleared `__pycache__`):** 1348 passed; ruff check and format clean; imports clean (514 files); code size
passed; contract plants all ok.

**My plants (8 of 8 killed):**

| Plant | Tests failed |
|---|---|
| any port allowed | 3 |
| credentials allowed | 3 |
| `http` allowed | 6 |
| wrapper link unchecked | 6 |
| `wrapper_link` compared | 2 |
| union of fields instead of shared | 1 |
| format 1 refused | 2 |
| empty shared set accepted | 2 |

## Checked and correct

- **The wrapper key is unchanged.** `keys.py` is not in the diff. `item_key` reads guid, title, summary, the source
  name and the time, never `link`, `source_url` or the facts.
- **No feed value reaches `source_domain` or `wrapper_link` unchecked.** Both go through `https_host`: https only, no
  user or password, port empty or 443, and `plain_host`, which is ASCII only, refuses whitespace, and requires a plain
  name. My attempts are refused or harmless:
  - a backslash before the at-sign, or a backslash in the host: refused;
  - tabs or newlines: `urlsplit` drops them for the check, and the resolver will re-parse the same way;
  - `http:` and an explicit port 8443: refused.
- **The cluster reader now reads both formats** through one `article_from_bytes`, which closes the trap the story
  names (F1).

## Findings

1. **F1 (must fix): a third migration trap. A version already kept as a format-1 *revision* gets a second revision file
   when it is seen again in format 2.**
   - `plan` still names a revision `sha8 = sha256(_fixed(data))[:8]` (`planner.py:86`). `_fixed` of a format-2
     article includes `source_domain`, even when it is empty, so the name of an unchanged version changes with the
     format.
   - Reproduced (strong evidence, my script). The Record holds the article file at version T1 and the revision for T2,
     both format 1 (revision `d98f05bf.json`). When T2 is seen again as format 2, the plan is **REVISION** at
     `baa4c05a.json`: a second write-once copy of the same version, with its own manifest row.
   - The story says "two migration traps, both reproduced". The `same_version` fix covers the article file and the
     collision check, not how a revision is *named*.
   - **Today there is no live data:** main has no news receipts or manifest, and `news-promote` is dispatch-only. It
     becomes real if a promote is dispatched before this merges, and again at every future format bump.
   - Fix (the builder's choice):
     - before naming a new revision, compare against the key's existing revision files with `same_version` (one
       listing of `news/revisions/<k2>/<key>/`); or
     - name revisions over a format-stable field set.

     The second needs care: two format-2 versions that differ only in `source_domain` must not collide.
   - Add the reproduction as a test, and a contract row with a plant.
2. **F2 (must fix): "compared on the fields both carry" lets a file with too few, or unknown, fields match.**
   `same_version` accepts any non-empty shared set (`planner.py:57-62`). Reproduced:
   - a held `{"key": K, "format": 1}` is the "same version" as a full format-2 article with that key;
   - a held file with an extra unknown key `evil` is the same as the article without it.

   In `plan` that is a **NO_OP**, and S1's `NewsPollProof` treats a NO_OP plus a manifest row as "promoted": a staged
   poll can be trashed against a Record file that does not hold the article's title or summary. The writer never
   produces such a file, so the path needs a hand-made or foreign file in the Record (reasoning only on likelihood).
   But the S1 deletion proof now rests on this rule, and the fix is small.

   Fix: compare only when each side holds at least the format-1 field set, minus the uncompared fields, and no key
   outside the known field set. Otherwise the files differ, as for a damaged file. One constant and two set checks.

## Notes (not blocking)

- `article_from_bytes` accepts `"format": true` (`True in (1, 2)`), a format-1 file carrying format-2 keys, and a
  format-2 file missing them (dataclass defaults). Consider an `is int` check and a per-format key set, so "an unknown
  format, a missing key or an unknown extra key is refused" holds exactly as the docstring says.
- The privacy constraint and the hand-off to NP2b (a Google-only egress guard in the resolver) are stated plainly.
  That is the right place, as long as NP2b's judges hold it.
- The reversed P2 test assertion is disclosed and matches NP0's approved mechanism. Accepted.

**Verdict: FAIL** (round 1, `20c8c32`). F1 and F2 are in the migration and comparison logic this story introduces;
each has a small, contained fix.

## Addendum 1: round 2 (final) on `a72a037` (includes NP1 final `d6f28e4`)

`git diff 20c8c32 a72a037 -- fno`:
- the new `article/formats.py`: `read_document` takes an `int` format that we know and exactly that format's key set;
  `same_version` compares on the older format's fields;
- the planner searches the key's existing revisions before it names a new one;
- `clean_https_link` for `wrapper_link`;
- `article_from_bytes` goes through `read_document`.

**Gates (cleared `__pycache__`):** 1377 passed; ruff check and format clean; imports clean (515 files); code size
passed; contract plants all ok.

**My round-1 reproductions, re-run:**
- **F1 fixed.** T2, kept as format-1 revision `d98f05bf.json`, is found when seen again in format 2, giving a NO_OP at
  that name.
- **F2 fixed.** The stub `{"key", "format": 1}` and the extra key `evil` are both now not the same version.
- **Note fixed.** `"format": true` and `1.0` are refused.

**`clean_https_link` checked:** the fragment is dropped; the scheme and host are lower-cased; port 443 is refused,
along with spaces, controls and backslashes; a trailing line break is trimmed by `strip()` before the checks.

**Plants (6 of 6 killed):**

| Plant | Tests failed |
|---|---|
| no revision search | 4 |
| key set loosened to "at least format 1" | 5 |
| `bool` format accepted | 2 |
| always compare format-1 fields | 2 |
| port 443 allowed | 1 |
| backslash allowed | 1 |

## Should fix (not blocking; a regression, but it fails closed)

The final collision check (`planner.py:64-66`) no longer compares versions. If the folder listing does not show a
revision that the planner itself holds in its cache, the same version is reported as a **name collision**. This
happens when the revision was written earlier in the same run (`ArticleWriter` stores it in `planner.held`) and
Drive's `files.list` has not caught up yet.

Reproduced with a store whose listing lags: the first plan gives REVISION; the second plan of the same article gives
`RawFileConflict ... revision name collision`. The old code answered NO_OP there.

The run then ends red with `record_conflict`, so no data is harmed. But it is a false alarm on a re-seen live blog in
a single promote. How likely is reasoning only: Drive's list index is not guaranteed instant, and the O9-child
incident shows this repository has met a lagging Drive read before.

Fix in one line: when `self._held(revision)` is not None and `same_version` holds, return NO_OP at that name; raise only
when they differ, as before.

**Verdict: PASS** (`a72a037`, final round), with the collision-check should-fix above.
