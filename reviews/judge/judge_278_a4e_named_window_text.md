# Judge 278: A4e story text, a named quote window for protocol v4's 14:30-14:40 pack (story/a4e-named-quote-window at 6e6f3b6b)

Judge B, 16 Oct 2026. Lane 1 (the 3 pm recorder; Groww). Builder: A4b/A4c (01MKtUHB). The interface was agreed with
G10's builder; assigned to me as G10's judge.

**Verdict: FAIL.** One should-fix: the named capture does not record a receive time for three of the pack's fields.

## What holds

- **Default run unchanged:** the default `QuoteWindow` is A4's constants; criterion 1 holds it to the byte-for-byte
  baseline and the v2 golden cases (`recorder.py` and `config.yaml` are "recorded, not byte-checked" in FREEZE_v2).
- **Own dataset:** `quote-snapshots-v4`, so the `nifty_*.canonical` globs of the default readers never see it.
  Criterion 3.
- **The window agrees with G10's pack (judge 277):** no request before 14:30:00, and none started after 14:40:00. A
  late answer keeps its real time, and the 14:40 cut is the pack's. A16's 14:30 mark on 16 Oct sent at 14:30:00.0004
  and answered at 14:30:00.753, inside the pack's inclusive window.
- **Refusals before any request; A16's clock check in the sidecar; honest known limits** (about 190 more calls on the
  one Groww key at 14:30; the routine's 14:05 start is O1's and the owner's).

## Should-fix: every pack field needs its own receive time, and three have none

G10's passed text (judge 274 addendum 1, section 1) gives **every** pack field its own `observed_at`: "this host's
checked clock at the answer's receipt". Part (a)'s code (judge 277) refuses a pack without one. A4e is the capture the
pack is built from, but today's recorder records a receive time only for option quote rows
(`request_sent_at`, `response_received_at`, `fno/quotes/recorder.py:58`). The other three fields have none:
- **India VIX and the futures** come from `MarketLevels` (NSE's public API), with NSE's own index-list stamp
  (`vix_time`) but no time of this host's receipt (`market_levels.py`, `meta()`).
- **Spot** is `chains[0].spot`, taken from the chain call, whose receive time is not written.

So the pack builder (part b) would have to fill `observed_at` for spot, future and VIX with the capture's
`started_at` or `finished_at`, which is not an honest receipt time, or call the day `system_late`. Neither is what
G10 agreed.

The text needs:
1. For a named capture, record the host receive time (and request time) of the levels call(s) and of each chain call
   (spot), in the sidecar or the rows. Named captures only, so the default run is unchanged.
2. A criterion with a fake clock: the VIX, futures and spot each carry their own receive time, and a level answered
   after 14:40:00 keeps its real time (the pack cuts it).

## Notes only

- NSE's futures list carries last price and volume, no bid or ask. G10's `future` allows `bid` and `ask` to be None,
  so this is fine, but say so in the text so part (b) does not expect them.
- The retry "each minute" inside a 10-minute window gives at most about 10 attempts. That is fine; A16's mark remains
  the A2 path.

Story text only; I checked the claims against `fno/quotes/recorder.py`, `fno/quotes/market_levels.py`, G10's text
and part (a)'s code.

## Addendum 1: story/a4e-named-quote-window at c350d375

**PASS.** The should-fix is met by the new criterion 4b. A named capture's sidecar adds, on the same clock:
- `chains`: per expiry, `expiry`, `spot` and `received_at` (that chain answer's arrival);
- `levels_received_at`: the time the level reads returned. That is an honest upper bound for both India VIX and the
  futures, since both had arrived by then. NSE's `india_vix_time` is kept beside it.

There are fake-clock tests for both, and the default sidecar is unchanged. Criterion 4 now names A16's `ClockCheck`
fields (`clock_checks` before and after, `clock_status` `clock_ok` only when both are, and
`clock_worst_skew_seconds`), with the 5-second threshold and a stopped-run case. One rule, no copy.

My note stands for part (b): NSE's futures carry no bid or ask, which G10's pack allows as None.

## Addendum 2: story/a4e-named-quote-window at 08c6f465

**PASS stands, strengthened.**
- Criterion 4b now gives each expiry's chain call its own `request_sent_at` and `response_received_at`.
- `levels_requested_at` and `levels_received_at` bracket the one `levels()` call; the receive time is an honest upper
  bound for India VIX and the futures.
- The text states that NSE's futures have no bid or ask.
- A fake-clock test checks that a level read returning after the window's end keeps its real later time, never
  clamped.

The default sidecar is unchanged.
