# Judge 29: story W9 re-judged (round 2)

**Verdict: FAIL** (changed from PASS on 13 Oct 2026, after this file was first written). There is 1 should-fix
finding: apply the owner's "Claude" decision.

**Why it changed:** I wrote below that "Claude" on screens "stays the owner's decision and is not counted". That was
wrong when I wrote it. The owner had already decided, at 09:55 UTC: "Screens never show 'Claude' either (owner:
'remove')", recorded in trading `docs/DESK_DECISIONS.md` by 13986d0, before this verdict (10:09 UTC). At 1c026c4
the screens still say "the Claude app" (companies help, the conversation channel label) and "the Claude API"
(assistant Spend card and messages), and `lib/ui/model-names.ts` leaves "Claude" unmatched on purpose.
- **Criterion 5 is therefore PARTLY met.**
- The builder could not have known: 1c026c4 predates the decision.
- **The fix is small:** "Claude" becomes a model name in the detector (the builder's "one entry"), and the copy
  names the channel and the cost source without it (e.g. "the AI assistant app", "the AI provider's API").
- Everything else below stands.

**Earlier verdict text, kept:** PASS. Both of judge 24's should-fix findings are ACCEPTED as fixed at their root
cause. Three minor findings remain:
- free-text forms the generic detector still misses, or over-matches;
- the builder's partial disagreement (rule and baseline names not allowlisted), which I accept only once minor 1 is
  closed;
- a residual of the source check.

"Claude" on screens stays the owner's decision and is not counted.

**What I judged**
- **Repository:** `exepex/omenix-dashboard` at 1c026c4, cloned read-only to `/tmp`.
- **Answers:** `reviews/claude/response_9_w9_home.md`.
- **CI:** run 38376159002 on 1c026c4, both jobs green. The orchestrator confirmed this through the GitHub API; I did
  not see it.

## Checks run by the judge

```
$ node tools/check_code_size.mjs                    every file within 350 lines or its listed size
$ cd web && npm ci --ignore-scripts && npm run typecheck && npm test      tsc clean; # tests 363 # pass 363 # fail 0
$ npm run build && node tests/ui/harness.mjs        148 cases, 0 failed
```

### Criterion 4: my own plants in `components/home/who-trades.tsx`, built into the app (reverted; tree clean)

| # | Plant | Result |
|---|---|---|
| P1 | The AI team card shows AI team + Rule-based (**−₹8,293.55**, judge 24's plant), keeping its own `data-src` | **Caught**: `home-india` (1680, 1280, 1024 …), `frame-page-home-india` (4 widths) and `dark-home-india` all fail with "groups:groups[2].total.net: shows −₹8,293.55, the field holds 1015.81" |
| P2 | The same sum, but labelled `data-src="groups:baselines.total.net"`, whose field holds exactly −8,293.55 | Not caught (4 cases pass). See minor 3. |

### Criterion 5: new forms through `applyDisplayNames`

Inside free text:

| Text | Shown |
|---|---|
| `opus-4-8 picked it` | AI team picked it ✓ |
| `o4-mini says buy` / `Gemini 2.5 Pro view` / `Grok-4 heavy` / `deepseek r1` / `gpt4o` / `Llama3.1-70B` / `SONNET 4.5` / `Sonnet5` / `picked by Fable5` | each replaced ✓ |
| **`picked by fable-5`** | unchanged: the lower-case id form of a current family |
| **`FABLE 5.1 view`** | unchanged |
| **`claude_opus_4`** | unchanged: the underscore joins the tokens, so the whole-token guard never fires |
| `anthropic/claude-3.5-sonnet` | unchanged: it is treated as an identifier (no space, contains ".") |
| `a sonnet about markets` / `the opus of the year` | **over-matched**: "a AI team about markets", "the AI team of the year" |
| `Claude Opus 5.5 agreed` | "Claude AI team agreed" (bare "Claude": the owner's open question) |

As strategy names (`ai.`, `rule.` and `base.` ids):

| Id and backend name | Shown |
|---|---|
| `ai.combined.opus.v1` "AI combined (Opus)" | AI team · combined ✓ (allowlist) |
| `ai.weird.v1` "AI with fable-5" | AI team ✓ (the allowlist hides the unknown role) |
| `rule.model_news_scored.v1` "Model + news, scored by claude-3.5-sonnet" | Rule-based ✓ |
| **`base.llm_only.v1` "claude_opus_4 only"** | **"claude_opus_4 only", shown unchanged** |

## Judge 24's findings: decisions

| # | Finding | Builder's fix | Judge's evidence | Decision |
|---|---|---|---|---|
| 1 | Should fix: the money check was set membership | Every money figure carries a required `data-src="<block>:<path>"`, and the check compares it with exactly that field from the app's own adapters (sign, currency, decimals). Money text without a source fails. 4 plants are injected on every run. | Code read (`home-checks.mjs`, `sources.ts`); my P1 is caught at every width with the exact field and value; full harness 148/0 | ACCEPTED |
| 2 | Should fix: the model-name rule was a blocklist | Strategy labels come from an allowlist (family approach plus a known role; an unknown role shows the approach only). Free text goes through a generic detector by family and id shape, matching whole tokens. The harness gate uses the same detector on every page. | AI-family labels can no longer show a model, whatever the backend publishes (my Fable, o3 and odd-role cases). The garbling is gone (`claude-sonnet-5` becomes "AI team"). Remaining free-text gaps and over-matches are in minor 1. | ACCEPTED |
| 3 | Owner: "Claude" on screens | Unchanged; one entry when the owner decides | **The owner decided "remove" (13986d0, 13 Oct 09:55 UTC)**; still shown at 1c026c4 | **Should fix (new)** |
| 4 | Minor: notes.md row 5 "Hybrid (India)" | Left frozen; listed among the differences | As judge 24 | Stays with the owner |
| 5 | Minor: three empty states not shown by any fixture | Proposal: W10 adds empty examples (`getAttention_india_empty` and similar), giving one harness case per state without an app change | Sound: Home reads W10's examples server-side, which W9 may not edit | ACCEPTED as a proposal; stays open until W10's examples exist |

### The builder's partial disagreement: rule and baseline names are not allowlisted

The reasoning is sound: rule names are human-written and name no model by design, and a strict list would hide every
new rule's name until someone edits it. But it is only as safe as the detector. My `base.llm_only.v1` "claude_opus_4
only" reaches the screen. **Accepted on condition that minor 1 is closed.** If the owner wants zero dependence on the
detector, the alternative is the strict list the builder offers ("one line").

## Criteria

5 of 6 are MET; criterion 5 is PARTLY met:
- **Criterion 4:** MET: the exact-field check; P1 caught.
- **Criterion 5:** PARTLY. Every fixture state is clean of the models the detector knows, and the gate runs on every page; but "Claude", which the owner ruled a model name to remove, is still shown (see the top).
- **Criterion 6:** 363 tests, typecheck, build and code size.
- **Criteria 1 to 3:** unchanged since judge 24, and the harness is 148/0 again.

## Engineering standards

- `sources.ts` (21 lines) and `model-names.ts` (44 lines) are small and single-purpose.
- `Money` and `MoneyDelta` require a source, so the compiler enforces the rule.
- No breach.

## Findings (minor)

1. **The detector misses some free-text forms and over-matches ordinary words.**
   - **Missed:** `fable-5` (lower-case id form), `FABLE 5.1`, `claude_opus_4` (an underscore inside the token), and a
     model id inside a no-space string with a dot (`anthropic/claude-3.5-sonnet` is skipped as an identifier).
   - **Over-matched:** "sonnet", "opus" and "haiku" as ordinary English words are rewritten. A news headline saying
     "magnum opus" would be changed, and the harness gate would fail it.
   - **Expected:**
     - treat `_` as a separator;
     - match Fable's id form (`fable-<digits>`) in any case;
     - scan identifiers for model tokens before skipping them;
     - for "sonnet", "opus" and "haiku", require a version or a `claude-` prefix (or capitals with a version), so an
       ordinary word is left alone.

     Add a test for each form.
2. **The partial disagreement depends on minor 1:** see above.
3. **The source check proves a figure equals the field it names, not that it is the right field for its place.** A
   figure labelled with another field's source passes (P2). An accidental cross-group sum is caught (P1), so this
   needs a deliberate wrong label; the risk is low. Expected, at the next touch: the group card's sources are
   derived only from its own group index (one helper), with a test that a card's `data-src` paths all start with
   its own `groups[<at>]` (plus its own book).
