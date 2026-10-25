# Judge 407: A22 pre-open data, story text (story/a22-preopen @ 5fbc44c9)

Judge F (independent), quality rule 1. Story `docs/stories/A22-preopen-data.md`. Lane 1 (new story; NSE, Groww, Drive,
Slack, a Claude routine). Labels: **strong**, **some**, **reasoning only**.

## Verdict: FAIL (1 should fix, 3 minor)

What is right:
- Step 0 reads every source and names what cannot be read: NSE's terms page, and NIFTY/BANKNIFTY pre-open in the
  evening.
- Asia opens are Out with a reason.
- The design reuses A16b's read-only Groww adapter rather than copying it.
- "No data" is never "complete".
- Raw answers and the day row go to Drive under O9, and failures use O10's `record-error`.
- The clock choice is right: a Claude routine, because GitHub's crons start 4-5 h late (judges 350, 351).

## Should fix

**SF1. If the 08:38 routine does not start, nothing alerts that day, and there is evidence it will sometimes not start
[strong for A16's record].** Every alert in the text is raised by the run itself, so a routine that never fires leaves
no line and no O10 row. A16's 15-minute recorder is the closest precedent: a Claude routine with a 09:00 first fire.
Its committed slot files show the first fire missed on 16 Oct (09:15, 09:30 and 09:45 `missed` / `not_taken`; first
good mark 10:00). It ran on 19 and 21 Oct (09:15 `good`, request at 03:45:00 UTC). 20 Oct was an NSE holiday
(Dussehra). So 1 of 3 sessions on record missed the first fire, a small sample [some].

A21's text faced the same question and said so plainly, naming A16's heartbeat and O8 as witnesses (judge 355 add. 1).
A22 has no witness at all.

Fix expected:
- name the witness;
- either an O8 freshness row "pre-open day row receipted by 09:20 on a trading day", agreed with O8's owner, so the
  evening check reports and the trial counts a missed morning;
- or a check by A16's 09:00-fired routine that today's GIFT Nifty and pre-open rows exist, alerting once if not;
- add a criterion for it;
- state the measured miss rate of the 08:38 routine in the first live week's claims.

## Minor

1. **Window boundaries (quality rule 5).** Criterion 4 should name exact instants: GIFT read at 08:39:59 (waits),
   08:40:00 and 08:44:59 (on time), 08:45:00 (late); pre-open retry at 09:13:59 and 09:14:00.
2. **"Trading day"** should be A20a's `is_trading_day` (regular or special, not muhurat-only), not just "a session of
   A7's calendar". A muhurat evening has no 09:08 pre-open.
3. **GIFT Nifty "one read"** should retry within 08:40-08:44 (for example each 30 s) before failing. One NSE hiccup
   would otherwise cost the 08:45 forecast its only input.

## Open questions, correctly sent to the owner

Step 0b (whether `key=NIFTY` / `key=BANKNIFTY` and BANKNIFTY's Groww pre-open candle answer at 09:08) and the
personal-research rule for NSE's pages are open questions, as the text says. Criterion 3 stays unmet until step 0b
proves at least one index source.

## Addendum 1: re-judge at e14c1a3f

**Verdict: PASS for the A22 story text.** Code may start once both witness lines are agreed with their owners (O8's
and FL1's), as scope 5 says.

| Finding | Answer in the text | My check | Result |
|---|---|---|---|
| SF1: no witness if the routine never starts | Scope 5 and criterion 8. An O8 freshness row "pre-open day row receipted by 09:20 IST on a trading day" (the evening check), plus the 09:15 forecast's own line "pre-open data: missing" (the same morning). Both are to be agreed with their owners before code. The first live week's miss rate goes in the claims | Both witnesses run outside A22's routine, so a routine that never fires is still named that day. A holiday gives neither (criterion 8) | **Accepted** |
| Minor 1: boundaries | 08:39:59 / 08:40:00 / 08:44:59 / 08:45:00 and 09:08:29 / 09:08:30 / 09:10:59 / 09:11:00, commit by 09:12:00, all on an injected clock | read | **Accepted** |
| Minor 2: trading day | `is_trading_day` (regular or special; muhurat-only, weekends and holidays print "not a trading day") | read | **Accepted** |
| Minor 3: one GIFT read | retried every 30 s inside the window until fresh; a stale first read then a fresh retry counts as fresh (criterion 4) | read | **Accepted** |

The new owner timing (committed by 09:12 for the 09:15 report) narrows the pre-open window to 09:08:30-09:10:59. That
still covers NSE's 09:08 close of order entry; the `lastUpdateTime` seen in step 0 was 09:08:44. Step 0b (whether
NIFTY/BANKNIFTY pre-open and BANKNIFTY's Groww pre-open candle answer at 09:08) stays open, and criterion 3 needs one
index source proven before the code round.

## Addendum 2: step 0b at 41e3591d

**Verdict: the PASS stands at 41e3591d.** This is a text change only. It records step 0b and moves the index value from
"the 09:07 or 09:08 candle" to the 09:09 candle.

Step 0b, as the builder read it through A16's `ReadOnlyGroww`, printing differences and times only:
- NIFTY and BANKNIFTY 1-minute candles exist for 09:00-09:14;
- over 21 regular sessions (21 Sep-21 Oct 2026) the close settles at the 09:08 candle (10 sessions) or the 09:09
  candle (11);
- on 21 of 21 sessions, for both indices, the 09:09 close equals `ind_close_all`'s Open Index Value exactly.

This satisfies criterion 3's "one index source proven" [strong as reported]. **I did not reproduce it:** this session
holds no Groww key. The code round's claims must include the comparison script's output, so a reader can re-run it.

**A risk to measure on the first live morning [reasoning only]:** the 09:09 candle closes at 09:10:00, and the window
gives Groww until 09:10:59 to serve it. If Groww serves 1-minute candles later than about 60 s, the index part fails
every day. The first live week's claims must give the serving delay per day. If it is close to the limit, widen the
window toward 09:11:30, which still meets the 09:12 commit.
