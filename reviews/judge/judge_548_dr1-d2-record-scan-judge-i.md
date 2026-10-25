# Judge 548: DR1-d2, the commit hook's record scan on the standard library only (first judge)

**Scope:** story/dr1-d2-stdlib-record-scan at 29d3c9d8 (code at 8f04d4c2; 29d3c9d8 adds Markdown only), builder
session_01SPR8hz6AY8S99wE6ypFRik. Judge I (session_01MvZneCLZqBuiGyNxawdVee), the first of two judges (a hard line:
the scan that keeps secrets out of commits); judge K follows. Lane 1. Round 1 of 2.

**Verdict: PASS.** No finding.

## Checked
| Point | Result | Evidence |
|---|---|---|
| The scan refuses exactly what it did | MET | `build_record_scanner` moved unchanged into `fno/record_scan/wiring.py`: same patterns, allowed values, credential shapes and forbidden paths. I ran main's and this branch's `tools/check_records.py` on the same files. 19 planted files (every pattern in the test suite) plus one clean file: byte-identical output, 21 findings, exit 1. A private paper-account path: identical refusal, exit 1. The whole tracked repository: identical apart from the file count. Plants caught: a forbidden path dropped, the credential shapes dropped |
| The value is never printed | MET | none of the 19 planted values appears in the output |
| A failed alert never turns a refusal into a pass | MET | `main` prints the alert outcome and then returns 1 whatever it says. A sender that cannot load returns "alert NOT sent ... \| <text>", and any other error exits non-zero. Plants caught: exit 0 after the alert, the alert text dropped |
| The hook cannot skip on an import failure | MET | `.githooks/pre-commit` `exec`s Python on the script, so an import error exits non-zero and git refuses the commit. With no Python at all it refuses by name. With `python -S` (no site-packages) the scan still refuses a planted credential and passes a clean file |
| Standard library only | MET | `test_the_scan_and_its_root_import_no_third_party_module` (a fresh interpreter, `-S`); plant (`import requests` in the root) caught. `fno.composition` re-exports `build_record_scanner`, so its callers are unchanged |
| End to end through the real hook | MET | in a throwaway worktree with `core.hooksPath .githooks`: a staged Slack-shaped value is refused (HEAD unchanged); a clean file commits. Nothing pushed; the worktree is deleted |
| Gates | MET | full `pytest -n auto` 14,647 passed, 16 xfailed, 0 failed; ruff check and format, check_imports and check_records clean |

## Plants
5 planted, 5 caught.
