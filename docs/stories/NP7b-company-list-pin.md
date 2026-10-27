# NP7b: the version 2 run refuses an older company list, and one edited in place

Lane 1, two judges. Plan: [NP7](NP7-company-list-safeguard-and-cutover.md) section NP7b (judge 100 N4, judge 101 B1). Contract rows Z17 to Z23
(appended to the NP6a section). **Reads the Record and the private company list; changes the version 2 cluster file's content (one more field);
writes nothing new, adds no workflow.** Version 2 has not been dispatched, so no existing file changes meaning.

## What it is
- The version 2 cluster file records `companies_sha256`, the SHA-256 of the list bytes it used, next to `companies_version` (private Drive file
  only, never git or a log). `CompanyList` gains `sha256`; `PrivateCompanyFile` fills it from the bytes it read; `parse_cluster_file` reads both
  fields back (0 and "" for a file with none).
- `ClusterRun` hands the latest earlier file of its version to `SymbolGrouping.inputs`, which compares (`_refuse_going_behind`): an OLDER list
  version stops the run with `company_list_rolled_back`; the SAME version with other bytes (an edit in place; a version number alone would not
  show it) stops it with `company_list_damaged`; a newer version is a new list and is recorded. Nothing to compare before the first file or after a
  run with no list.
- A list the last file used that is now MISSING stops the run (`company_list_missing`); only a run that never had a list is version 0.
- Every stop writes nothing and is a red run with the existing alert, like the other `GroupingBlocked` codes.

## A change from the plan, said plainly
The plan said to pass `used={version: sha}` to `VersionedFiles.latest` and to refuse when it skipped a damaged newer version. I compare in the
grouping instead: the newest list is read as before and checked against the previous file. The outcomes for the cases that matter are the same
(rollback, edit in place, a list that vanished) and no skipping logic is involved, so there is no path where an older list is quietly used while a
newer one is skipped. `VersionedFiles` and the other private files (feed list, discovery, materiality) are untouched.

## Said plainly
- Only the version 2 cluster run is protected. The materiality file has no reader in any run today; the feed plan and the discovery file keep their
  own existing rules.
- An owner who deliberately replaces `companies-vN.json` with a corrected copy under the same number is stopped by this; the way through is a new
  version number. That is the intended cost.
- A first file after a list appeared for the first time records it; nothing before it can show that an earlier list was removed.
