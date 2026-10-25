# Judge 426: IL Innovation Lab design text (story/il-innovation-lab at 59d77f50)

**Verdict: FAIL on the story text: 2 should-fix findings and 2 minor.** Both fixes are text only. The design is sound,
honest and reuses the existing pieces. The faults are one honesty hole (stage 2 for methods that have already seen
all of history) and one clash with an owner decision (the board, while the UI is paused).

## Checked myself (strong evidence)
- **Owner decision.** 93e01804 exists on `main`: design now, build later, three outputs, strict pharma-style gates, no
  AI cap. The text keeps to it and adds no code.
- **Map paths.** Every path in section 2 exists on `main` (I checked each one).
- **Ledger seam bug: real.**
  - `fno/factory/registration.py:42` computes `max(int(row["trial_id"])) + 1` over `research/ledger.csv`.
  - `fno/book3/registry.py:95` writes `book3:<id>` into the same ledger. Both go through
    `research_engine.ledger.Ledger` (`fno/factory/wiring.py:48`, `fno/book3/wiring.py:16`).
  - Today the ledger holds trials 1-9 only, so nothing is broken yet. D5 is off. The first Book 3 registration would
    make every later R1 registration raise `ValueError`.
- **RM1's quote.** `REAL_MONEY_GATE.md` condition 5 says "There is no multiplicity route (no 0.05 ÷ m level)", owner,
  15 Oct. The text follows it and asks the owner (Q1) rather than overriding either decision. That is right: the
  21 Oct row asks for "a luck correction for the trial count", the 15 Oct one rejects it for real money, and only the
  owner can settle it.
- **Q1's number.** G4 uses B = 10,000 resamples (`block_bootstrap.py:4`). 0.05 ÷ 50 = 0.001 is about 10 resamples in
  the tail, as stated.
- **The false-pass arithmetic.** 0.05 × 0.05 × K, so about 0.25 at K = 100. It is correct under its stated
  independence assumption, and it is labelled reasoning only.

## Findings

**Should-fix 1. Stage 2 (held-out history) cannot be passed by methods whose back-fill has already seen all of
history, and the text must say so.**
- G13's back-fill covers 2019-01-01 to 2026-10-20 (Drive receipts on `main`). G13b's back-fill and the v4 back-fill
  are scored and reported over their whole range. Judge 416 and response 290 quote their headline results.
- "The last 25% of history, named before stage 1 runs" is already spent for every method that exists today. Calling
  it "held out" later would be the peeking the gate is meant to stop.
- Fix: state that existing methods (G13, G13b, v4, M1 and anything else with a full back-fill) enter with stage 2
  recorded as **spent**, not passed. Their only honest evidence is forward: stages 3 and 4. Stage 2 applies only to
  candidates registered before their held-out window is ever scored.
- Add to gap c's audit: "held-out window never read before the freeze", checked from the scorer's input range in its
  record. Strong evidence: the receipts.

**Should-fix 2. Gap f's board clashes with the owner's UI pause.**
- DESK_DECISIONS row 262 (21 Oct): "Focus: ... with daily Slack reports; UI paused".
- Gap f proposes "one read-only page" listing every candidate.
- Fix: make it a generated text report (a Markdown file or a weekly #fno-forecast line, read from the ledger, the gate
  log and the score files), or put the page to the owner as a question. Strong evidence: the decision row.

**Minor.**
1. **The ledger seam bug needs an owner row, not only a report.** Name its owner in `docs/WORK_REGISTER.md`; R1's and
   D5's builders must agree who fixes it. Make it a condition before D5 or Book 3 goes live. The second issue, that
   K counts retrospective rows and measurements, is a design question for R1. List it under Q1, because it changes
   the K stated on every verdict.
2. **20 warned events (Q3) is a thin sample; state its width.** At a 50% hit rate, the 95% interval on 20 events is
   about ±22 points. For a 2% NIFTY move, which happens on a few percent of sessions, 20 events also takes about a
   year. Say both, so the owner answers Q3 knowing them. Reasoning only.

## Over-engineering check
No new store, scorer or freeze. Seven gaps, each mapped to an existing owner, and the selector deferred until two
members are proven. Proportionate to the owner's request. Accepted (reasoning only).

## Note: 4550232c (two lines since 59d77f50)
The change is 3 lines in `docs/stories/IL-innovation-lab.md`:
- Gap d now says LR3's code was never started and needs a new builder, named by the orchestrator.
- The seam note records D5's confirmation, and its proposal that B4's `Ledger` alone allocates numeric IDs, with R1's
  owner deciding.

Both are accurate and partly answer minor 1. **The FAIL stands:** should-fix 1 (stage 2 spent for every existing
method) and should-fix 2 (the board versus the UI pause) are unchanged. The orchestrator has parked both behind
FL1-1c.
