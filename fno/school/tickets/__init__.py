"""Tickets and the three counts (story MS-P1f, 327 item 1).

A ticket is a 1-lot virtual trade where a driver's rule fired but its account did not trade: beyond the slot's trade
limit, or refused only by an account limit (bucket, open risk, new risk a day, margin room). It obeys the same quotes
and laws as a trade with only those limits relaxed (a stopped or braked driver issues no tickets that day), lives in
its own ledger (never a driver's account) and is never summed into rupees shown to the owner. Every scheduled
decision is counted: eligible, fillable, executed."""
