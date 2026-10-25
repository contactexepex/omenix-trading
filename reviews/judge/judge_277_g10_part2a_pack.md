# Judge 277: G10 part 2 code (a), the v4 pack format, SHA, paths and binding guard (story/g10-part2a-pack at df9432e9)

Judge B, 16 Oct 2026. Lane 1 (forecast records' binding; the protocol's terms), against the text passed in judge 274
addendum 1. Builder: A16/G8/G10 (01VK88Lx).

**Verdict: PASS.**

| Item | Result | Evidence |
|---|---|---|
| Section 1's fields, each with its own `observed_at`; `mid` only with both sides | MET | `model.py`; `Pack.observed_by()` is the latest `observed_at` (the release record's) |
| One pack, one identity | MET | `pack_bytes` is canonical JSON (sorted keys, no spaces, UTF-8, `allow_nan=False`). `read_pack` refuses other bytes (SHA), a broken format (exact key sets, label A or A2, non-empty chain, CE/PE, finite numbers, offsets, the future's expiry after the day) and non-canonical bytes. A tampered or stale `mid` re-encodes differently, so it is refused too |
| Every `observed_at` in 14:30:00-14:40:00 IST | MET | `_Window`, inclusive at both ends |
| The binding guard, keyed by forecaster (my judge-274 should-fix) | MET | `PACK_READERS = {book2_hybrid, book3_ai}`. A reader must name exactly the released SHA, so empty or other is refused; a reader on a `system_late` day is refused; a non-reader naming any SHA is refused |
| `terms.V4_LATEST_FIRE = 14:55`; Drive paths | MET | |
| My two notes from judge 274 written into the text | MET | O1 named beside A4's owner; "A2 is the normal path until the routine moves" |

## The builder's three points

1. **The lower bound 14:30:00: ACCEPT, checked on real data.** A16's committed 14:30 mark on 16 Oct
   (`research/data/intraday/slots/2026/10/16/nifty_20261016_1430.csv`) has `request_sent_at` 14:30:00.0004 IST and
   `response_received_at` 14:30:00.753, inside the window. The margin is 0.4 ms, so part (b) must test the A2 path on
   a real A16 row. A16 must keep its rule of never asking before the slot time, or every A2 pack would be refused,
   making the day `system_late`.
2. **M1's method hash moves with `terms.py`: ACCEPT, verified.** `fno/weather/wiring.method_sha256` on main gives
   6a295227, while the committed M1 v4 rows carry 2495d512, so it was already moving. Nothing compares the hash across
   records before the v4 freeze (judge 254), and the freeze pins it. Moving the constant out of `terms.py` would
   contradict the passed text.
3. **The builder rules (late field absent; missing required field means `system_late`) are part (b)'s: AGREED.**
   Part (a) refuses such a pack on read, which is the right half here.

## Mutations (real cases, all caught)

- The guard letting an empty SHA through: 2 tests fail.
- The canonical-bytes check removed: 3 tests fail.
- The window's lower bound removed: 1 test fails.
- A non-reader allowed to name a SHA: 4 tests fail.

**Gates (run by me on df9432e9):** 7,672 passed (`-n auto`, Slack token unset), no failures. `ruff check`: clean.
`ruff format --check`: 1,379 files already formatted. `check_imports`: clean.
