# NP6a: the grouper, clustering algorithm version 2

Lane 1, two judges. Plan: [NP6](NP6-tiered-clustering.md) (passed by judge 96, round 2, with condition C1). Contract rows Z1 to Z15
(the plan called them W1 to W12; `W0` to `W6` already belong to the write-once rows). **Reads the Record and the private
company list; writes one new kind of cluster file (format 2) in a new folder; changes no existing Record file.** The scheduled
cluster workflow stays dispatch-only; version 2 is chosen by the new `algorithm` input (default 1), so nothing changes until the owner
dispatches it, and version 1's behaviour and bytes are as before.

## What it is
- **Preparation** (`cluster/prepare.py`, `Preparer`): per article, the shingles of its title form (as in version 1), the SYMBOLS the
  `Tagger` (NP5a) finds in the title (never the summary; the article's source is passed so an outlet suffix never tags; Z1, Z1b), and
  its identity URL (`cluster/url_identity.py`). Version 1's fixed 22-name list (`entities.py`) is untouched.
- **The bar** is the unchanged `entities.bar_for`: a common symbol lowers it, different symbols raise it, none leaves it, an entity alone
  merges nothing. Only what supplies the symbols changed.
- **The identity URL** (`resolve/effective_url.py`: the resolution file's URL for a Google News item, the item's own link for a
  publisher item; never feed text or a label) counts only when it can identify one story (`url_identity.py`, judge 96 B1): a query after
  tracking parameters are removed, two or more path segments, or one segment with a hyphen or a digit. A home, a section or a tracking-only
  link is refused and counted (`url_joins_refused`, Z2b, Z2f). **The rule is a guess (reasoning only).**
- **Assignment** (`cluster/assign.py`): URL first (an article whose URL was taken by an earlier member of a cluster joins that cluster,
  any member; one URL belongs to the cluster that took it first; the 36 h match window applies; Z2, Z2a, Z2e), else title against the
  ANCHOR only (no chaining by score, Z4). `url_joins_unlike_title` counts URL joins the title rule would not have made (**condition C1**,
  Z2c): the early-warning count for a generic URL the rule accepted.
- **The run** (`cluster_record/grouping.py`, `SymbolGrouping`; `run.py`): reads the newest company list and the resolution files of the
  window's Google News items (read only). **No company list at all is `companies_version` 0 and a run with no bar movement; a list that
  exists but cannot be loaded (invalid, rolled back, damaged, or the store unreadable) stops the run with its fixed code and writes nothing**
  (judge 96 B3, Z6, Z6b); like every other stop it is a red run with the existing `#fno-desk` alert. A damaged resolution file stops the
  run too (`resolution_unreadable`, Z13); a missing one is an item not resolved yet.
- **Format 2** (`cluster_record/cluster_file.py`): version 1's fields plus `companies_version`, `resolutions_used`, `url_joins`,
  `url_joins_refused`, `url_joins_unlike_title`, in the folder `news/clusters/2/`. The parser accepts formats 1 and 2 (Z12, Z15).
- `news cluster --algorithm 2` and the workflow input `algorithm` (a choice, default 1).

## The guarantee, stated honestly (judge 96 B2)
The same articles, the same resolution set and the same company list give the same bytes. A re-run of a closed window that sees other
input (a resolution or an article recorded since) is refused by the write-once rule and reported, as version 1 already does for a late
article. There is no day cutoff and no time in the resolution file. The file records `resolutions_used` and `companies_version`.

## Changed outside the new files, and why
- `tests/.../cluster/test_window_determinism_privacy.py`: the "no I/O" check forbade the whole `urllib` package; it now allows only
  `urllib.parse` (string splitting, used by the URL rule) and still forbids the rest. Judges: check this is a fair narrowing.
- `view.py` uses `effective_url` (same rule, moved so the cluster code can share it; plant U11 re-pointed).
- Two fakes in `test_reader_wiring_privacy_cli.py` take the new `algorithm` argument.

## Said plainly
- **Nothing here says version 2 groups better.** The threshold, the windows and the URL rule are untuned defaults; the version 1 against
  version 2 comparison on real polls (merge rates, and `url_joins_unlike_title`) is required before NP7. A high `url_joins_unlike_title`
  means the URL rule lets generic links through: tighten it.
- A publisher URL cannot join two publisher articles: the article key is built from the link, so one link is one article. The URL join
  matters for a Google News item and its publisher copy.
- A story re-published after 36 h with the same URL is split (the fail-safe direction); counted only through the cluster sizes.
- Hourly runs read the resolution files of the window each time (a few thousand small reads at most); not measured.
- The private company list is read here; no symbol or name is written to a file, a log or a code.
