# P4: Yahoo cross-check of NSE closes — a report, not a block (PLAN)

PLAN for the orchestrator's check before any code. Pattern: the official-against-Yahoo comparison that `global_cues` already runs
(`pair_checks.py`, story A17e). This plan reuses it; it does not build a second one. Authority rule from
[PIPELINE_DESIGN.md](../PIPELINE_DESIGN.md): NSE wins on conflict, and a cross-check source is never the primary record.

## What already exists (read, not assumed)

- **Yahoo is already an engaged source.** `YahooChartSource` fetches Yahoo's public chart JSON for other indices (Nikkei, Hang Seng,
  FTSE, DAX, VIX and more) in the scheduled `global-cues.yml`, with one plain GET, no redirects followed, and a block (401/403/429, a
  redirect, a non-chart page) as a stop for the whole run (`YahooGate`). Owner rule 50a79a43 (21 Oct 2026): a source's redistribution
  terms do not block a download for private research; **the values live in Drive only**. So P4 adds no new source and no new terms
  question. It does add new SYMBOLS on the same host.
- **The comparison exists.** `pair_rows(index, official, yahoo)` lists dates where the closes differ by more than 0.1 percent and dates
  only one side has, as **dates and kinds only, never a value**; the rows go to private checks in Drive and only counts are printed.
- **NSE's side exists.** NSE's index-close file is archived in Drive and read by `close_read/official.py` (`ArchivedIndexCloses`).
- **What is missing:** no Indian index is a Yahoo cue today (no NIFTY 50, Bank Nifty or India VIX symbol is in the cue list), and the
  comparison has no NSE side.

## Answers to the orchestrator's three questions

1. **Does P4 archive Yahoo closes to a Record? No new write path.** The existing global-cues collector already archives each Yahoo
   answer write-once and private in Drive with its own manifest (A17). Adding an Indian symbol there reuses that path unchanged. P4's
   new code is a **report** over data that is already archived, so it needs no new Record writer and no receipts of its own. One judge,
   not two, **provided the live cue list is not changed in this story** (below). If the cue list were changed, it would change what a
   LIVE scheduled workflow requests, which I would route to two judges.
2. **Same source, same pacing: yes.** The new symbols go through `YahooChartSource` and the shared `YahooGate`; nothing new in the
   request, headers or politeness.
3. **Report, not a block; NSE authoritative; counts only: yes.** A difference never changes or removes an NSE record. The run prints
   counts by kind (`differs`, `only_nse`, `only_yahoo`) and writes the dates and kinds to a private Drive checks folder as write-once
   parts. An alert goes to #fno-desk when a count is above zero, with counts only.

## Shape (one judged round)

- `nse_closes.py`: adapts the archived NSE index-close values to the `{value_date, close}` rows `pair_rows` takes.
- `yahoo_closes.py`: reads the archived Yahoo chart answers for the same indices into the same rows (the existing reader of the cue
  tables, not a new parser).
- `report.py` and `python -m fno cross-check nse-yahoo --from --to`: runs `pair_rows` per index, prints counts, writes the private rows,
  exit 1 and an alert when anything differs.
- `nse-yahoo-check.yml`: dispatch only, with the failure alert step and no schedule until the owner enables one.
- **Not changed here:** the live cue list. The three cue definitions are added as a named, unused tuple; wiring them into the scheduled
  `global-cues.yml` run is a one-line change that I list for the owner's go-live, because it starts real requests from a live job.

## What I cannot verify

- **The Yahoo symbols.** From memory only: `^NSEI` (NIFTY 50), `^NSEBANK` (Bank Nifty), `^INDIAVIX` (India VIX). Not checked against a
  real answer. Ask: may I make **one** plain chart request for each, the same kind the scheduled job already makes (outside the Groww
  window; it is not a Groww read), to see that the symbol exists and what its dates look like? Or hold until the cue list is enabled?
- **Whether 0.1 percent suits NSE against Yahoo.** The tolerance comes from other indices (rounding between publishers is far below
  it). NSE's own close and Yahoo's for Indian indices are not measured here; I would run the check, read the counts and adjust the
  number, not assume it.
- **Yahoo's quality for Indian indices** (timing, holes, a stale last bar) is unknown; the existing `may_hold_unfinished` and finality
  margin logic cover the known case.

## The limit that matters

NSE's index-close file is **not promotable** through the gate yet (Phase 1: the file's own date format was not confirmed against a real
archived file). So this cross-check is a **report after the fact** on files already archived, **not a gate check before promotion**: it
can tell the owner a recorded NSE close looks wrong; it cannot stop one entering the Record. Making it a true gate check needs the
index-close dataset to become promotable first, which is a separate, earlier decision.

## Gates

Full suite, ruff, imports, numbers, size, record scan; mutation plants for the tolerance edge, each kind, the authority rule (a
difference never writes to NSE's side), and the counts-only output (a marker value must not appear anywhere printed, committed or alerted).
