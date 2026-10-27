# Judge 98: NP6b corroboration (code), round 1 at e7ff690: PASS

**Lane 1; judge #1.** Branch `story/NP6b-corroboration`, frozen SHA e7ff690. Reviewed `git diff origin/main...e7ff690`: `news/corroboration/{model,origins,flags}.py` (109 lines) and `view.py` (adds `wire_via` and `outlet`). Plan: NP6 (judge 96 PASS).

## Gates (locked venv; strong evidence)
1930 passed; ruff is clean; contract plants all `ok`, W7 to W11b included.

## Review (strong evidence)
- **Pure and order-free.** The groups are sorted by label, the counts are sums over groups, and nothing is stored, so the count follows the rule files and the resolutions and reads of the day.
- **One origin per agency and per outlet.** The label is `wire:<agency>`, else `outlet:<outlet key>`. `outlet_key` folds `www.`, `m.` and `same_as` hosts into one outlet.
- **Countable** means listed, not promotional and not opinion. **Verified** means a countable article that was read, or whose agency was named by something other than the title (the title attribution is a heuristic, as NP0 says).
- **Unresolved articles** have host `""` (judge 94's fix), so they all fall into one `outlet:` group that is never countable. They cannot inflate the count.
- **Plants (each one undone; all fail tests):**

| Plant | Result |
|---|---|
| a wire named only by the title verifies | 1 failed |
| a promotional article countable | 2 failed |
| an unlisted article countable | 2 failed |
| wires not grouped | 2 failed |
| outlet taken as the raw host | 1 failed |
| `origins_unverified` flag removed | 1 failed |

- **Stated limit (plan, "Said plainly"; reasoning only):** two listed outlets that copy a non-agency story count twice, because no copy test is ported. `origins_unverified` and `reads_used` tell the reader how far to trust the number.

## Hard lines
No order path, no secret, no Groww call, no request, no write.

## Verdict: PASS round 1 at e7ff690.
