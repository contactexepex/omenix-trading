# Judge 15: SEC1b minors (judge #2)

Branch `story/SEC1b-minors`, SHA `e01d717e815e11c62fbf887304f811d285983517`, 4 files on `main`. **PASS**, lane 1.

| Item | Verdict | Evidence |
|---|---|---|
| `pipx install` scanned | MET | regex plus a plant; my `pipx install foo` in `ops/` fails 1 test; removing `pipx` from the regex fails 1 test |
| `PIPELINE_DESIGN.md:19`, `:127` wording | MET | "malicious when locked / any other open root listed above" |
| Portable uv-version header | MET | `printf` + `cat` + `mv` replaces GNU `sed -i`. **I ran `sh ops/relock.sh` with uv 0.11.32: all three locks were rewritten byte-identical (`git status` empty)**; counts 21/438, 53/1,561, 14/353 |
| uv pin in `relock.sh` | MET | `expected_uv=0.11.32`; a different uv stops the script; the test matches each lock header to it (changing the pin fails 3 tests) |

Gates (`.sh` and `.py` changed, so the full set): 255 passed; `ruff check`, `check_imports`, `test_code_size` clean.

No findings. This closes every SEC1 minor I raised (judge 12, Addenda 2-4). `be23751`, which I passed in judge 12
Addendum 4 but which was never merged, is superseded by this change.
