# Judge 592: T1f story text, the card in a rehearsal and every step after the post guarded (story/t1f-card-rehearsal-clock at a70c4cb23)

**FAIL, lane 1.** Round 1 of 2. Judge I, own session (session_01CHtddAzFcEdQh4HFiz3mqU), 24 Oct 2026. The diff
changes only `docs/stories/T-cards.md` (a new T1f section). Judged by reading and against the code on `main`.

## Claims checked (root cause)

| Claim | Verdict | My evidence |
|---|---|---|
| The guard refuses GitHub with a `RuntimeError` | MET | `http_guard.py:16` allows only Google and Slack hosts; `RehearsalCallRefused(RuntimeError)` at `:22` |
| `HttpDateClock.now` catches only `requests`' errors; `check_server` only `ServerTimeUnknown` | MET | `server_clock.py:52` (`RequestException`), `:102` |
| The clock check runs after the post, so the record and metadata are lost | MET | `issue.py:50-52` posts, then runs `check_server`; save and `_write` come later. `_write` catches `OSError` only (`:66`) |
| O1 takes a failed command's reason from its last stdout line | MET | `fno/daily/steps.py:49` `lines[-1]` |
| The guard is installed only in a rehearsal | MET | `rehearsal/process.py:14-21` |
| REH1c's `NOT_CHECKED` exists to reuse | MET | `rehearsal/preopen_wiring.py:15` |
| The hook's home and choice point fit REH1's rule (only the roots and the package know the mode) | MET | `card_label.py:20` beside `rehearsed_card_poster`, chosen in `cards/wiring.py:88`. REH1's owner's agreement is pending (Split) |
| A rehearsal's metadata never reaches `main` | MET, unstated | a rehearsal works in its own clone on `rehearsal/<day>-<run_id>` (`mode.py:19,45`; 10 such branches on origin) |

**Rulings asked for.**
- The rehearsal clock hook in REH1's package: right, it is REH1c's pattern. It needs REH1's owner's yes before code.
- Guarding every step after the post, for any error, posting once, with the delivery line printed last: right, and it
  is T1's own promise (`issue.py` docstring). Finding 1 is about the parts that are left unguarded.
- O1's stderr item as Out for O1's owner: right. It is O1's code (`steps.py:49`), and T1f no longer depends on it.

## Findings

1. **Should-fix: the guarded steps are listed incompletely, and the facts-failure case is not testable.**
   - Between the post and `_write`, `issue()` also builds the Drive record outside `save`'s guard:
     `_section(s)` for every section, `_record_name(...)` and `_json(record)` (`issue.py:54-57`). The Scope lists the
     clock checks, the facts, the save and the metadata write only. A raise in `_json` (a non-JSON value) still leaves
     a posted card with no record.
   - Criterion 4: "A raise building the facts is printed and stored the same way". When the facts fail there is no
     metadata to print, so "the same way" says nothing about what is printed, what is stored (Drive? metadata?), or
     which exit code results.
   - Fix expected: name every step after the post, including the record build (or state one guard around everything
     after `poster.post`). Then define the facts-failure fallback exactly: the fields kept (for example the day,
     `slack.sent/ts/channel`, `card_sha256`, and the error type), where it is stored, and exit 1. Add a test-plan
     case and a plant for it.
2. **Minor: say where a rehearsal's metadata goes.** Criterion 2 should state that it goes to the rehearsal branch
   (`rehearsal/<day>-<run_id>`), never `main`.
3. **Minor: criterion 6's wording.** After criterion 3, "the reproduction" (where `issue` raised) can no longer
   happen. Say what the test asserts instead: with the hook removed, GitHub is unchecked with `RehearsalCallRefused`
   instead of the rehearsal line, so the test fails.

## Plants

None (a text round). P1-P6 are planned; finding 1 needs one more (the record build outside the guard).

## Gates

Doc-reading tests at a70c4cb23, with `FNO_SLACK_BOT_TOKEN` kept (owner, 24 Oct): 853 passed, 15 xfailed. Record scan
clean.

## Addendum 1: round 2 at 57a5f0f38 (diff a70c4cb23..57a5f0f38)

**PASS, lane 1** (Judge I, own session). The diff changes only the T1f section of `T-cards.md`. It also carries REH1's
owner's two conditions (2d4e93719).

| Item | Verdict | My evidence |
|---|---|---|
| 592.1 should-fix | FIXED | Four stages after `poster.post`, in `issue.py`'s order, each guarded so a raise never skips the next: clocks, facts, Drive record build and save (now including `_section`, `_record_name` and `_json`), metadata JSON and write. The minimal facts are listed field by field and stored in both files with `failure: "facts not built (<Type>)"`. Exit 1 on any failed stage. Tests 3b and 3c, plants P6, P6b and P6c. The fallback keeps what the next card's `misses()` reads: `slack.sent/outcome`, `drive.saved/outcome` (added by the delivery) and `clock[].server/warning/line/checked` (`deliveries.py:80-86`), so `clock: []` is safe |
| 592.2 minor | FIXED | Criterion 2 and the Scope: metadata only on `rehearsal/<day>-<run_id>` (`checkout.py`), never `main` |
| 592.3 minor | FIXED | Criterion 6 asserts the rehearsal line on GitHub's entry (without the hook it becomes "RehearsalCallRefused"), and that no `HttpDateClock` is built (P8) |
| REH1 condition 1 | MET (text) | Criterion 7, test 6, plant P7: the card's clocks join `guard.builders()` (`rehearsal/guard.py:24`, which already lists `build_card_poster`), with `test_guard.py`'s map and count updated |
| REH1 condition 2 | MET (text) | `CardClocks` interface with `ServerCardClocks` and `RehearsalCardClocks`; GitHub's `HttpDateClock` is built only inside the real form's builder. One interface, two forms, chosen in the composition root (CLAUDE.md "Design for change") |

Notes for the code round (not findings):
- When the facts fail, `clock: []` drops checks already made in stage 1. That is safe for `misses()`. Keeping the
  checks' `stored()` form, when it can be built, would lose less.
- Test 3b could also feed the minimal metadata to `card_from_delivery` and the pinned contract
  (`test_p1_t1_card.py`), since every committed delivery is validated there.
- The 592.1 answer says the fallback keeps `drive`, but stage 2's list has no `drive`. It comes from the delivery
  wrapper, which is fine; the code should keep it that way.

Doc-reading tests at 57a5f0f38, with `FNO_SLACK_BOT_TOKEN` kept: 853 passed, 15 xfailed; record scan clean.
