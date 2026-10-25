# Judge 431: A17e global markets beyond the US, story text (story/a17e-global-markets @ a95591c0), for response 297

Judge F (independent), quality rule 1. Story `docs/stories/A17e-global-markets.md`, claims response 297. Lane 1
(outside services, Drive, a schedule). Labels: **strong**, **some**, **reasoning only**.

## Verdict: FAIL (1 blocking, 3 minor). The fix is small.

What is right:
- Step 0 tests every market the owner named. It quotes each publisher's terms with a URL and sorts sources into
  allowed, restricted and none, so nothing restricted is built without an owner decision.
- KOSPI without a key reports "not configured" and does not fail the run, so there is no daily red masking real
  failures (unlike judge 408's A20c).
- A same-day Asian close is never `live` at 09:15.
- Everything is private in Drive, and nothing new is scheduled.
- The boundary with A22 is agreed, and the evidence-based "Asia opens: out" closes A22's question.

## Re-checked by me (21 Oct 2026, about 21:30 UTC)

CSIndex `index-perf?indexCode=000001&startDate=20261001&endDate=20261021`: HTTP 200, 11 rows. The first row is
`20261001 3811.9` and the second `20261008 3811.9`. 1 Oct was a Chinese holiday, so the start-date row is a copy of the
next session, exactly as step 0 says **[strong]**.

## Blocking

**B1. No gap list (quality rule 2, `docs/JUDGE.md`).** As in judges 353 and 355: every requirement must map to a
criterion, or to "Out" with its reason. Here those are:
- the owner's 21 Oct words (Australia, Singapore, Hong Kong, Japan, South Korea, China; "don't consume US data only");
- A17's point-in-time rule;
- the private rule (a927390);
- O9;
- the A22 boundary;
- quality rules 5, 6 and 8.
The text covers most of them, but in prose. Add the table, with each market the owner named mapped to built / owner
decision n / out (no usable source).

## Minor

1. **Boundaries (rule 5).** Criterion 2 should pin each market's `available_at` at, just before and just after its
   close (Shanghai 15:00 CST = 12:30 IST, Taipei 13:30 = 11:00 IST, Seoul 15:30 KST = 12:00 IST). Criterion 1's
   fake-row rule should cover a real start-date session whose close equals the next one's.
2. **The text says "the Asian closes of day d ... are out by 21:10 IST on d".** They are out by about 11:00-12:30 IST
   on d. That does not change the 09:15 use (only d-1 counts as known), but the 14:11 IST run of day d can already hold
   them, which matters to the 15:45 report. Correct the sentence, and say whether the 14:11 run should take them (it
   is cheap: the same `once_a_day` rule decides).
3. **The fake-row rule drops a start-date row "whose values equal the next row's".** That is right for CSIndex's
   behaviour, but a calendar-based rule is safer: drop the start-date row only when the start date is not a trading
   date in a wider window of CSIndex's own answers. If you keep the equality rule, add the flat-close test from
   minor 1.

## Owner decisions

The six questions (VIX, Nikkei, TAIEX history, Europe and Singapore, a paid API, the KRX key) are correctly the
owner's, each with a recommendation and its label. Nothing restricted is built before an answer.

## Addendum 1: re-judge at 3faedabb (revision 1, under the owner's data rule, DESK_DECISIONS row 281)

**Verdict: FAIL (B1 still open, 1 new should fix, 2 minor).**

Under row 281 a source's redistribution terms no longer block it, so the restricted publishers and Yahoo's chart API
may be used. Part A is now complete for all eleven indexes. Checking Yahoo against the official files row by row is
good work [strong as reported]:
- Nikkei: 927 of 927 equal;
- SSE: 3 sessions missing on Yahoo;
- VIX: 1,960 of 1,963 equal, with one large error (6 Feb 2026, 20.37 vs 17.76);
- the reading prefers the official value, and an overlap check lists every difference.

**B1 (from round 1) is still open: there is no gap list.** Revision 1 adds criteria but not the table that quality
rule 2 requires. Map each market the owner named (Australia, Singapore, Hong Kong, Japan, South Korea, China), Europe,
the VIX, A17's point-in-time rule, row 281's three kept rules, O9, the A22 boundary and quality rules 5, 6 and 8 to a
criterion or to Out.

**New SF1. Row 281's second kept rule needs a stated behaviour for when Yahoo blocks us.** The text says Yahoo answers
"no login, cookie or CAPTCHA" today. Yahoo's chart API is known to start requiring a consent cookie and a "crumb", or
to answer 401 or 429, without notice [reasoning only]. Fetching a crumb or rotating identities to get past that would
be the circumvention row 281 forbids.

Fix expected: say that on 401, 403, 429, a consent or crumb page, or a CAPTCHA, the Yahoo cue stops, alerts once (an
episode) and is never retried with a cookie, a crumb, another user agent or another address. Add a criterion with a
planted 401 and a planted consent page. The STOXX TLS point is accepted: supplying SSL.com's public intermediate
certificate to complete a chain the server leaves incomplete bypasses nothing.

## Minor

1. For Hang Seng, ASX 200, Straits Times and FTSE 100 there is no official file, so the overlap check cannot guard them.
   The text's "the overlap check is our only guard" is wrong for exactly these four. Label their readings
   `unverified (Yahoo only)` so a study can see it.
2. Boundaries (rule 5): part B's 20-minute stale rule at 20:00 and 20:01. Criterion 4's close-time test should be at
   and just around each market's `available_at`.

## Addendum 2: re-judge at febca555 (rev 2)

**Verdict: FAIL, only addendum 1's SF1 left.** Rev 2 answers round 1 and crossed with addendum 1.

| Finding | Rev 2 | My check | Result |
|---|---|---|---|
| B1: no gap list | "Gap list (quality rule 2)" table: each named market and each rule mapped to a scope item, a criterion or Out | read | **Accepted** |
| Round 1 minor 1: close-time boundaries | criterion 4: each market's close at, minus 1 minute and plus 1 minute IST, the AU and EU clock changes, and an empty case | read | **Accepted** |
| Round 1 minor 2: same-day closes for 15:45 | the 14:11 cron landed 3 h 42 min to 7 h 09 min late (17-21 Oct), so same-day closes are Out (FL1 decides), with the reason stated | consistent with the GitHub lateness I measured (judges 350, 351) | **Accepted** |
| Round 1 minor 3: fake-row rule | each CSIndex request starts ten days early and drops every row before the wanted date, so the fake first row never lands and there is no equality guess; tests cover a planted holiday start and a flat close | better than my calendar suggestion: no calendar needed, and nothing circular | **Accepted** |
| The builder's own fix | a duplicate Yahoo date is left out and listed, not the whole answer refused (ASX back-fill) | reasonable, and the date is listed, not hidden | **Accepted** |

**Still open: addendum 1, SF1.** There is no stated behaviour when Yahoo starts blocking (401, 403, 429, a consent or
crumb page, a CAPTCHA). Line 39 says only that Yahoo answers today "no login, cookie or CAPTCHA". The gap list maps
"no getting around blocks" to step 0 and STOXX only. Add: the Yahoo cue stops, alerts once (an episode) and is never
retried with a cookie, crumb, another user agent or another address; and a criterion with a planted 401 and a planted
consent page. Addendum 1's minors (label the four Yahoo-only indexes `unverified`; the stale rule at 20:00 and 20:01)
go in the same revision.

## Addendum 3: re-judge at 6f0725f8 (rev 3)

**Verdict: PASS for the A17e story text.** Code may start.

| Finding | Rev 3 | My check | Result |
|---|---|---|---|
| Add. 1 SF1: Yahoo blocks | lines 65-68: HTTP 401, 403 or 429, a consent or "crumb" page, or a CAPTCHA page stops that Yahoo cue for the run, writes nothing, and is named in the run's alert line; never retried with a cookie, crumb, other user agent or other address; the next scheduled run tries once, the same plain way. Criterion 8 plants a 401, a 403, a 429 and a consent page (HTTP 200), counts exactly one request, and checks that the other cues still run; the gap list maps it | read | **Accepted** |
| Add. 1 minor 1: Yahoo-only indexes | `unverified (Yahoo only)` in every reading and check line (line 69, criterion 8, gap-list rows) | read | **Accepted** |
| Add. 1 minor 2: stale boundary | 20:00 not stale, 20:01 `stale` (criterion 7) | read | **Accepted** |

Note (no change asked): A17's run alerts once per run, so a Yahoo block that lasts gives one line per run (three runs
a day). That is A17's accepted pattern, and with "never worked around" it is the right side to err on. If a long block
happens, an episode rule like A20b's is the follow-up.
