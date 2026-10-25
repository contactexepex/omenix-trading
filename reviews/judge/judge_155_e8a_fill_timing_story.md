# Judge 155: story E8a text, the fill-timing study (quality rule 1; judge C)

Date: 15 Oct 2026 (UTC). Branch `story/e8a-fill-timing` at **ec326cf15dbdf2d4886c76235f322cfc404a6548**
(`docs/stories/E-paper-desk.md` E8a; claims `reviews/claude/response_149_e8a-judge-153-answer.md`).
- Earlier verdicts 153 and 154 on this branch came from same-session judges. The orchestrator counts them as builder
  self-review, so this is the first independent check.
- Judged under the owner's "keep the design simple" rule and the 15 Oct coordination rule (`docs/WORK_REGISTER.md`).

## Verdict: PASS (text); 3 notes

| Check | Status | Evidence |
|---|---|---|
| It answers the owner's ask | MET | `docs/DESK_DECISIONS.md:179` (owner: "History + live"; "15:00 vs 10:15 entry per strategy family"; credit/debit change and win at both). E8a measures the entry move `C` (credit/debit change) and the flip share (win at both) per family, and fixes the live rule for the follow-up. "Range still holds" needs an entry range that does not exist yet (`fno/cards/card.py`, no trade fields), so the 5/10/20% stand-ins are labelled reasoning only. That is a fair stand-in, said plainly |
| The reading of the mean is right | MET | A later fill changes one structure's P&L by exactly `C`, and the families mirror (SF = CCS + PCS, BF its reverse, all ATM-anchored in STR1), so the mean of `C` is mostly drift and theta, not a cost. The story leads with the size of the move and the flip share, and computes the time part apart: the right design |
| Look-ahead and data spend | MET | The decision prices are the 15:00 or 14:00 candle closes; VIX is taken at the decision day's open; the expiry is the nearest monthly more than 7 sessions away. The 2024-26 candles become `spent` with ledger row 54, and the 2019-23 candles stay `fresh`. Ledger trial 54 is free on `main` (last row 53) |
| Read-only, raw only in Drive | MET | Groww is reached only through A16's `ReadOnlyGroww`, at most 2 calls a second, outside market hours. Raw answers go to Drive through `RawFileStore` with manifests. Criterion 10 tests the import closure |
| Freeze before the fetch | MET | The probe records counts only, never a price. Protocol, code hash and ledger row are frozen first (criterion 1) |
| Duplicates and contradictions | none | The register lists E8a under the project thread. E8 itself is unbuilt; no other study or story measures fill timing (my grep of `research/`, `docs/stories/` and `fno/`). It touches no file of E2c, E4c or E5b: it is research only, in its own folder, with no `fno/desk` change |

## Notes (none changes a trade)

1. **The 15:15 label.** "E4's 15:15 execution snapshot ... is the same price as the 15:00 decision's R = 5 fill" is the
   same *time*, not the same price. E4 fills at the bid or ask; the study uses candle closes (last trades). Say "the
   same time" and let the existing spread caveat cover the difference.
2. **Ledger row 54 is free today.** Another study could take 54 first. Check it again when the study commits its
   freeze.
3. **Simplicity.** The design is large for a measurement study: three R values, two decision times, three widths,
   four splits, a Black-76 time part, a paired difference and two bootstraps. Each piece has a stated reason, and the
   owner's choice of decision time is a real trade decision, so I do not ask for cuts. If the build grows past one
   small package, drop the 100- and 300-point width sensitivity first.

**Verdict: PASS for ec326cf15dbdf2d4886c76235f322cfc404a6548** (story text). Code may start. It is research only, so
rule 9 applies only if the orchestrator classes it as touching trade decisions.
