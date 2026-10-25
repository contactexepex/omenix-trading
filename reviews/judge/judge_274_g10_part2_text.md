# Judge 274: G10 part 2 story text, the pack, its release record and the AI fire (story/g10-part2-text at 338080fe)

Judge B, 16 Oct 2026. Lane 1 (a new story part; forecast records; a workflow), before the v4 freeze. Builder: A16/G8.
Register: the "G10 v4 timeline" row. One new subsection in `docs/stories/G-forecasts.md`, before G11.

**Verdict: FAIL.** One should-fix: the pack-SHA rule leaves an empty SHA open for the records it is meant to bind.

## What holds

- **Storage through O9** from day one: `DataStore.put` for writes, `DriveCache` for reads, receipts in GitHub. Groww
  values stay in Drive (A4b).
- **The pack:** outside the frozen `fno/forecast_v4/`; its SHA is of the stored canonical bytes; every field has its
  own `observed_at`, with `last_trade_time` never used as observation time; a field after 14:40:00 is out; a missing
  required field means `system_late`. Criterion 1 is testable.
- **The deadline:** 15:10:00 on GitHub's receipt time through O8's `file_pushed_at` behind an interface, never the
  commit time; criterion 4 pins 15:10:00 against 15:10:01.
- **The fire:** a `push` trigger on `receipts/v4/days/**`, no cron (a test refuses any `schedule:`); `V4_LATEST_FIRE`
  14:55. The evidence that the owner's routine push starts workflows is cited (15 Oct, bf16247a, run 38714143717).
- **The design point (G7 and M1 rows carry `pack_sha256` empty): ACCEPT.** They commit before 14:30 from closes up
  to d-1, before any pack exists; their method hashes and part 1's proofs show they read no pack. Requiring a SHA
  would push them past their own cutoff.
- **Criterion 6 says plainly** that the "push starts the fire" proof needs the owner's schedule change. That is
  honest, and it is the owner's call.

## Should-fix: an empty SHA must be refused for every pack-reading record

Section 4 says "a live record naming any other SHA is refused". Criterion 3 says "a pack-reading record with another
SHA is refused; G7 and M1 rows carry it empty". As written, an **empty** `pack_sha256` names no SHA, so a pack-reading
record (an AI book's) that leaves it empty passes. That is exactly what the binding exists to stop. Because G7 and M1
legitimately carry it empty, the rule cannot be "empty is fine".

The text needs:
1. Which records must carry the pack SHA is decided by the **forecaster** (a fixed list in code: the AI books, and V4
   and V5 when built), never by the record's own field.
2. For those, an empty or different SHA is refused before writing. For the others, a non-empty SHA is refused (they
   read no pack).
3. Criterion 3 gets both cases as tests.

## Notes only

- **Label `A` versus `A2` in practice.** The 3 pm routine starts at 14:33 IST (CLAUDE.md) and runs its setup first,
  so a 14:30-14:40 capture cannot start at 14:30 until the routine moves. Until then, `A2` (A16's 14:30 mark) is the
  normal path, not the fallback. Say so, so the day-label counts are read right.
- **Ownership.** Moving the capture's window is A4's recorder (`fno/quotes/`, the A4b/A4c builder), and the routine's
  timing and prompt belong to O1 (register "Handover / routines": "A4c, G10 and A14c send their lines through O1").
  Name O1 beside A4's owner.

Story text only; I checked the claims above against the register, CLAUDE.md and the cited code paths.

## Addendum 1: story/g10-part2-text at df5dcf35

**PASS.** The should-fix is met. Section 4 and criterion 3 now refuse "a pack-reading record with another SHA **or an
empty one**", through a guard in `fno/v4_pack/` fed the released SHA from the release record.

Checked:
- `records.py` checks only the form (empty or 64 hex), and `read()` takes a missing column as empty. So the committed
  G7 and M1 CSVs (9,636 M1 rows in its two forecaster folders) are not regenerated, and a file's next write adds the
  empty column with no value changed.
- `records.py` is not in G7's `METHOD_FILES` (`series`, `baselines`, `rules`, `vix_rule`, `capture`) nor in M1's
  list, so no method hash moves. True by the files.
- The future's expiry `e` and the chain's minimum expiries are now defined.

**A condition for G11's code verdict (recorded, not a should-fix here):** the guard is opt-in. It binds a record
only if that forecaster's writer calls it. "Reads the pack" is therefore decided by which writers call the guard, a
fixed set in code, not by the record's own field, which is what my should-fix asked for. G11's judge must check that
every pack-reading writer calls the guard (a test per writer). A writer that skipped it would let an empty SHA
through. A non-pack forecaster naming a SHA is not refused; that is harmless, as it reads no pack.

My two notes from judge 274 remain notes: until the 3 pm routine moves, `A2` is the normal path; and O1 owns the
routine's timing.

## Note (judge B, 16 Oct 2026): the A2 fallback cannot make a complete pack

The G10 builder reported this while reading A16 for part (b). I checked all three points in A16's code:
- **No India VIX:** `fno/intraday/groww_source.py` never reads it (grep: no "vix").
- **One monthly, not two:** `fno/intraday/expiry_plan.py` asks for the nearest listed expiry (the weekly) and the
  nearest monthly. IV30's two-monthly input is therefore missing.
- **No `e` on a monthly expiry day:** the monthly is "on or after" the day (`expiry_plan.py:48-51`), while `e` is the
  monthly strictly after `d`.

So under section 1, every `A2` day would be `system_late`. My judge-277 condition ("part (b) must test A2 on a real
A16 row") would fail for these reasons, not for timing.

The text passed here needs a change, which is the orchestrator's choice: drop `A2`, a reduced `A2` pack, or a wider
A16 mark. My view, reasoning only: drop `A2`. Now that A4e has passed (judge 281) and the routine moves to 14:05, a
failed 14:30 capture made honestly `system_late` is better than a reduced pack whose inputs differ by day, which would
make families' forecasts incomparable across days. The changed text comes back to me.
