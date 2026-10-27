# P3: BSE announcements — a second, cross-check source into Staging (PLAN)

PLAN for the orchestrator's check before any code. Lane 1 (a new outside service, a new Record area, a new workflow). Role per
[PIPELINE_DESIGN.md](../PIPELINE_DESIGN.md): BSE is **cross-check / secondary**, never the primary record where NSE holds the same
fact ("scraped source is a cross-check, never the primary record when an authoritative one exists"). Pattern: P1 staging/record
split, P2a fetcher, P2b gate. Built and tested offline; the first real fetch is the owner's go-live step.

## What I do NOT know (so the plan is conditional)

- **The BSE endpoint contract is not verified.** From memory (reasoning only, not checked): BSE serves company announcements as JSON
  from `api.bseindia.com` by date range, paginated, and refuses requests that lack browser-like `Origin`/`Referer` headers. I have
  not seen a real response in this repository. Nothing below is built on a guessed format: the parser is written against a real
  sample or not at all.
- **Whether BSE permits automated reads.** The site's terms and robots rules have not been read. NSE's pacing and refusal rules
  (a block is a stop, never retried another way) are the model; BSE gets the same, behind its own pacer.
- **The join key between BSE and NSE.** BSE lists companies by a numeric scrip code, NSE by symbol. A cross-check needs a mapping
  (ISIN is the usual bridge). Whether the BSE announcement rows carry an ISIN or only the scrip code is unknown.

## Proposed shape (each its own judged round, one in flight)

1. **P3a, the source and the sample (no gate):** `BseAnnouncementsSource` behind `RawFileSource`, one day's list as write-once
   raw JSON in Staging under `bse/...`, its own `Pacer` (never the NSE or news pacer), the block rule, fixed reason codes, no URL or
   header in any committed file. Tests against a recorded sample I would need from you or from one polite read.
2. **P3b, the gate:** a `PromotionCheck` set for the BSE day list (it parses, the rows are for the day it claims, no truncation),
   promotion to a `bse/` Record area, a manifest and receipts (the P2b2 discipline: file first, one definition of the guard).
3. **P3c, the cross-check (a report, not a block):** compare the BSE and NSE announcement lists for a day on the join key. A BSE
   row with no NSE counterpart (or the reverse) is a **note** in the run log with counts only; it never stops or alters an NSE
   record (NSE is authoritative). Without a reliable join key this stage is count-level only and says so.

## Decisions needed before P3a

1. May I make **one polite, read-only request** to BSE's public announcements endpoint (outside the Groww window; it is not a Groww
   read) to see the real response, or will you supply a sample? Without a real sample I will not write the parser.
2. Is BSE's **terms of use** acceptable to the owner for automated reads? This is the owner's call, not mine.
3. Priority: the design lists BSE, Yahoo and more news as open decision 3. Is BSE next, or Yahoo (Phase 4)? Yahoo is thinner (it
   cross-checks closes only) but its shape is already known from `global_cues`.

## Risks, said plainly

- A scraped, unofficial source can change without notice; the gate's job is to refuse what no longer parses, loudly.
- A cross-check that cannot join on a key is a count comparison and proves little. I will say so in the report text, not hide it.
- Every outside service added is one more way a workflow can fail; BSE gets its own workflow, dispatch-only until go-live.

## Gates

Full suite, ruff, imports, numbers, size (350), record scan, mutation plants for every invariant, two judges for the Record writer
(P3b) and one for the source (P3a).
