# Judge 443: O1-status-only story text (story/o1-status-only at f4a02858)

**Verdict: FAIL, 2 should-fix (both small). The design is right and is the one I would choose.** One boundary at
`DailyRun._step`, injected from O1's composition root and tested to be always present. Codes instead of producers'
text, `unlisted` for anything unknown, and child stderr no longer merged. The full text goes only to a git-ignored local
log and to Drive. The inventories are useful, and I spot-checked them: `fno/desk/daily_steps.py` 148 writes
`inputs["blocked"]`; the four readers that show text; `_unfilled`'s `["reason"]`.

## Answers to the builder's two questions
- **Matching by template prefix is acceptable as the closed set,** with the guard in should-fix 2. Producers need not
  emit codes: the boundary is closed by default, and their Slack alerts keep the full text.
- **The owners list is right:** E3 for `_step`, the block readers and the `build_daily_run` parameter; O8, T1 and S2
  as readers only. Add E3's `fills` inputs (`inputs["blocked"]`) to the field list (should-fix 1).

## Should-fix 1: default-deny must apply to every leaf value, not only to named free-text keys
The rule says "no float, no free text". But design point 2 maps only the free-text fields by name ("`reason`, `error`,
`line`, `lines` and the like"). A value under any other key passes untouched. That is a concrete path:
`fno/desk/daily_steps.py` 148, `inputs["blocked"] = dict(blocked)`, holds each book's block text under the key
`blocked`, not `reason`. Any later step result with a money figure under a new key would pass the same way.

**The text must say** that `PublicResult` walks every leaf of inputs and result, whatever its key:
- a bool is kept;
- an int is kept only under an allow-listed count key (`rows`, `n`, `attempts`, `exit_code` and the like). Elsewhere
  it is dropped, because an int can be money;
- a float is always dropped;
- a string is kept only if it matches the closed vocabulary (id, hash, ISO date or time, step or book name, the step's
  status words). Otherwise it becomes a template code or `unlisted`.

Criterion 1's planted test should put one value under an unlisted key (for example `inputs["blocked"]`, and a new
`result["net"]`) and prove it does not appear.

## Should-fix 2: a template whose fixed prefix is empty or shared matches everything
"The fixed prefix (the text before its first `{`), longest first." Several real templates begin with a placeholder, so
their prefix is empty, and an empty prefix matches every text:
- `APPLIED = "{done} applied, ..."` in `fno/desk/owner_timing/step.py` 32;
- `OPENED = "{legs} legs filled ..."` in `entry_fills.py` 29.

Every unknown text would then become `APPLIED` or `OPENED` instead of `unlisted`, and the closed-by-default promise
breaks. Long shared prefixes such as "F&O daily run {day}: ..." are also ambiguous between templates.

**The text must say:**
- a template is matched on its whole fixed skeleton (every literal piece in order, for example by turning the template
  into an anchored regular expression with each placeholder as `.*?`), not on its prefix alone;
- a template with no literal piece of at least a few characters is not matchable and maps to `unlisted`;
- the registry test asserts that no two templates can match the same text.

## Notes (not should-fix)
- The Drive copy of the full log is written at the run's end. If Drive is down, only the local copy exists. Say that
  this is acceptable (the alert already holds the text) or alert it.
- `waiting` items pass the same vocabulary. If they become `unlisted`, the list stays non-empty, so `_unreviewed` still
  blocks; criterion 5 covers it.

## Addendum 1: head 1ca3a8c3
**Still FAIL: both should-fix items are open.** The heads crossed: 1ca3a8c3 changes only the owners section and the
register row, recording that the orchestrator agreed the change for E3, O8, T1 and S2 (no live owner), limited to the
named files. That part is accepted, and at code review I will check that the diff stays inside those files. The design
text is unchanged, so should-fix 1 (default-deny every leaf by type) and should-fix 2 (match whole template skeletons)
still need their sentences.

## Addendum 2: head 6b50aa57
**Verdict: PASS (text). Lane 1; the code is next.** Both should-fix items are closed.

| Item | Result |
|---|---|
| Should-fix 1: default-deny by type, whatever the key | MET. Every leaf at any depth: bools and None kept; ints only under allow-listed count keys; floats dropped; strings only in the closed vocabulary (hash, ISO time, run or snapshot id, step or status word, identifier), else a template code or `unlisted`; lists keep their length. Criterion 1 plants values in `inputs["blocked"]`, under an unnamed key, and as an integer amount under an unlisted key |
| Should-fix 2: whole-skeleton matching | MET. An anchored regex of each template's literal text with placeholders as `.*?`; a template with no literal piece is refused. Registry tests: each template maps to its own code, no two match the same text, APPLIED and OPENED only their own, unknown text is `unlisted` |
| Note: Drive down at the run's end | MET. Skipped with one alert, and the day's status is unchanged |

## For the code (a condition I will check, not a should-fix at text level)
The "identifier" rule ("starts with a letter, no spaces") still lets a spaceless value through, for example `Rs12345.60`
or a contract symbol such as `NIFTY26OCT25000CE`, which names a paper position (E2c keeps positions private). No
producer emits either into the log today, but the boundary should not depend on that. In the code, limit an identifier
to letters, digits, `_`, `-` and `:` (no `.` or `,`). Add `Rs12345.60` and a contract symbol to criterion 1's planted
values, expecting `unlisted`. Trade ids and `how` values still pass.

## Addendum 3: the identifier rule, corrected
The builder is right: my condition in addendum 2 ("letters, digits, `_`, `-`, `:`, no `.` or `,`") refuses
`Rs12345.60` but still passes `NIFTY26OCT25000CE`, which is letters and digits only. **I accept their refinement as the
condition for the code:**
- an identifier is `[A-Za-z][A-Za-z0-9_:-]*` with no run of 3 or more digits;
- the ids that do carry long digit runs keep their own exact patterns, checked first: hashes, ISO times, run ids and
  snapshot ids.

The real ids pass: `t1`, `b1`, `book1_rules`, `shadow:b0-monthly-sc-v1`, `forecasts_v4`, `raised:OSError`.

Criterion 1 plants `Rs12345.60`, `NIFTY26OCT25000CE` and `Rs12345`, all expected `unlisted`, with those real ids as a
positive control. The stated limit (a value of at most two digits beside letters, such as `VIX15`, still passes) is
accepted as a known limit: no producer writes such a token.
