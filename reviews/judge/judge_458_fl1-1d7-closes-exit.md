# Judge 458: CLAUDE.md, the evening's A4h exit rule (story/fl1-1d7-closes-exit at 2e7f8899)

**Verdict: FAIL: 1 should-fix finding (the wording).** The diagnosis is right; the instruction it adds would post the
wrong line.

## Checked myself (strong evidence: code)
- **The diagnosis is right.** `fno/close_read/cli.py:21-29`: with `--commit`, `cmd_closes` returns the read's own
  code unless the commit line holds "NOT committed". So exit 1 also means a failed or too-early read. The old text
  ("exit 1 means those receipts were NOT committed") was wrong. Judge F found it.
- **But the commit line is always printed last.** `cmd_closes` runs the read, then always calls `out(line)` with the
  commit's line. `fno/storage/manifest_commit.py:21` makes that line "<label> committed and pushed (N file(s))" or
  "<label>: nothing new to commit".
- So on a failed read, which leaves nothing to commit, the last line is "…: nothing new to commit". "Post its last
  line to #fno-desk" would then send an alert that says nothing about the failure. Only an uncommitted receipt makes
  the last line the problem line.

## Should-fix 1
Change step 1c to post the read's problem lines, not the last line, for example: "exit 1: post every line it printed
(the read's own problem line and the commit line) to #fno-desk, since nothing else alerts a failed read or
uncommitted receipts outside O1". The alternative is a code change in A4h's CLI, which belongs to A4h's owner and is
not needed if the routine posts all lines.

This is text only; one more round, and it must merge before Fri 19:53 IST.

## Addendum 1: 2eca4ad8

**Verdict: PASS (lane 1, rule document). The builder may merge: pull, the fast checks, push.** The diff against
`main` is 2 lines of `CLAUDE.md` and no code. Step 1c now reads: "exit 1: post every line it printed (the read's
problem line and the commit line) to #fno-desk, as a failed read or uncommitted receipts are alerted by nothing else
outside O1".

It is now true to `cmd_closes` in both failure cases:
- a failed read posts the read's own problem line;
- an uncommitted receipt posts the "NOT committed" line.

No full suite is needed for a text-only change; the merge runs the fast checks (ruff, `check_imports`,
`check_records`, `check_numbers`). It must be on `main` before Fri 19:53 IST.
