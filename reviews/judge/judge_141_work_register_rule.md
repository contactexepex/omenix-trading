# Judge 141: CLAUDE.md rule "One builder per function": `story/x-work-register` a1991c7e6c7588ce062975b8789f11d72322cf23 (lane 1, a rule document), judge A

**The change.** Three lines in CLAUDE.md's "How to work with the owner" list:
> **One builder per function (owner, 15 Oct 2026).** Before starting any story, fix or design change, read
> `docs/WORK_REGISTER.md` on the latest `main`; if a row already covers the same function, files or rule, agree with
> its owner session first, and add or update your own row in your first commit. Never build a second version.

## Checks

- **It is the owner's own ask.** The register quotes the owner on 15 Oct: "make sure that no two agents are trying to
  implement or develop the same functionality or same functionality but contradictory implementation".
- **The register exists on `main`** (21338c0, lane 3 status rows). Its active rows name real stories, sessions and
  branches.
- **A real path makes the rule necessary.** Sessions on two accounts commit to `main`, and some cannot be messaged
  (01Mt6d…, 01MgTu…). Today's overlaps are real: two sessions edited CLAUDE.md's 3 pm section and the routines, and
  response numbers clashed (137/138/139 earlier today). So the repository is the only shared channel. One file plus one
  rule is the simplest mechanism, with no tool, no check and no lock, so it meets the owner's "keep the design simple".
- **The wording** is short and concrete:
  - what to read (one file, on the latest `main`);
  - when (before any story, fix or design change);
  - what counts as an overlap (the same function, files or rule);
  - what to do (agree first; add your row in your first commit).

  It agrees with the register's own rule paragraph.
- **The merge is clean.** It merges cleanly with `main` as of now, and CLAUDE.md is a document, not covered by the
  350-line code rule.

## Note (one line)

The CLAUDE.md line says "agree with its owner session first", but some owners cannot be messaged. The register names
the fallback ("or write a `reviews/claude/response_<n>` note"). Add "(by message, or a response note when it cannot be
messaged)" to the line, so a session never stalls or skips the step.

### Verdict: PASS for a1991c7e6c7588ce062975b8789f11d72322cf23

It is the simplest rule that meets the owner's ask. One wording note.
