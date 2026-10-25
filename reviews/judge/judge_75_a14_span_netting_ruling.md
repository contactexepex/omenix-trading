# Judge 75: A14 early ruling, which SPAN figure C2 must receive (branch not final)

Date: 14 Oct 2026 (UTC). Asked by the orchestrator before the 09:25 IST broker check. Source:
`reviews/claude/response_74_a14-nse-margins.md` (findings, item 1) on `story/A14-nse-margins`, and C2's
`fno/risk/rules.py` `MarginRoom` on `main`. This is a ruling on the definition only, not a verdict on A14.

## Ruling

C2 must receive the exact figure, `max(0, scan − NOV) + min(0, NOV)`, plus exposure. The builder's formula is right.
- Neither (A), scan alone, nor (B), scan minus NOV, is right for every structure.
- Store scan risk, NOV and exposure as separate columns, so that this figure and the stressed one below are computed
  and never retyped.

Strength: strong evidence (algebra, checked on the builder's 14 Oct numbers) for a book with no other open trade.
Reasoning only for books with open trades (below).

## Why

Symbols:
- NOV is the net option value, the position's value at mid: negative for a credit structure.
- The entry's cash flow is about −NOV (costs left out).
- The account starts with cash = marked equity (no other open trade).

C2's `MarginRoom` leaves `min(cash + cf, equity + cf + marked) − X − exposure` free:
- `cf ≈ −NOV` and `marked = NOV`;
- so C2 leaves `cash − max(NOV, 0) − X − exposure`.

A broker that nets the premium (SPAN with NOV) leaves `cash − NOV − max(0, scan − NOV) − exposure`.

Setting the two equal gives `X = max(0, scan − NOV) + NOV − max(NOV, 0)`, which equals
`max(0, scan − NOV) + min(0, NOV)`.

Checked on the builder's rows:

| Row | Scan | NOV | X by the formula | Matches |
|---|---|---|---|---|
| SF 100 | 822.25 | −6,071 | 6,893.25 − 6,071 = 822.25 | (A) |
| BF 100 | 831.35 | +6,071 | 0 + 0 = 0 | (B) |

- **(B) for a credit structure** counts the premium twice: C2 already refuses to count the received premium as free
  cash. That makes it too strict by the premium, Rs 6,071 to 17,134 a lot here.
- **(A) for a debit structure** is too strict by `min(scan, NOV)`.

Both errors are on the safe side, so neither is a loss of protection. But too strict means fewer trades than the
real account would allow, so the desk would not trade what was tested.

`X` is never negative (for NOV < 0 it is at least the scan risk). It can be 0 (the BF row), so the stored margin must
include exposure: C2's margin file refuses a value that is not above 0 (`fno/risk/margins.py`).

## Two consequences the builder must handle

**1. The stressed margin must stress the scan risk, not `X`.**
- Under stress, SPAN's scan risk grows; the premium already paid or received (NOV) does not. So the stressed input is
  `max(0, k·scan − NOV) + min(0, NOV)` (plus stressed exposure).
- `k × X` is right for credits, where `X` = scan.
- `k × X` is too loose for a debit structure whose scan risk exceeds its NOV: `k·(scan − NOV) < k·scan − NOV` when
  k > 1.
- That is why the columns must be stored apart. Whether exposure is stressed too, and by what, is part of the owner's
  stressed-margin choice.

**2. Books with open trades (reasoning only).**
- When the book already has a marked loss, C2's `min(...)` binds on marked equity. C2 is then stricter than the
  broker, never looser.
- One test: a book with an open losing trade, where the exact input still never lets C2 allow more than the broker
  formula.

## The 1.45 stressed factor

The 1.45 stressed factor from the 2020, 2024 and 2026 windows stays a proposal for the owner, as the orchestrator
says. I have not checked it. I will judge it when it is offered as a setting, including whether it applies to scan
alone (consequence 1).

## What the 09:25 IST broker check should record

It should record SPAN, exposure and total exactly as the broker shows them, and whether the broker's SPAN line equals
(A) or (B) for the SF basket. That tells us what the broker displays. It does not change this ruling, which follows
from C2's own formula.
