# Judge 14: SEC1b minors, branch `story/SEC1b-minors`, SHA e01d717

**PASS, lane 1, judge 1.** It is based on `main` after the SEC1 merge (c656700) and changes 4 files: `ops/relock.sh`,
`tests/test_pinned_installs.py`, `docs/PIPELINE_DESIGN.md` and the SEC1 story.

| Check | Verdict | Evidence (my own runs) |
|---|---|---|
| The be23751 changes I passed carry over unchanged | MET | The `expected_uv` pin, the header-to-pin test, `pipx` in the scanner and the design wording all match be23751 (diff of the doc's changed lines: identical) |
| Portable header write | MET | `{ printf '# uv-version: %s\n' ...; cat; } > "$output.tmp" && mv`: POSIX, no GNU `sed -i`. Running the branch's `relock.sh` (uv 0.11.32) in a clean tree regenerates all three locks byte-identical to `main` and leaves no `.tmp` file |
| The pin is enforced | MET | Plant: `expected_uv=0.11.31` makes 3 tests fail |
| Gates | MET | 255 passed; ruff, check_imports and check_numbers clean |

Findings: none.

Note: this supersedes my be23751 verdict (`judge_13`, Addendum 4); be23751 itself was not merged.
