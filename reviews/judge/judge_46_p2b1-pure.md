# Judge 46: P2b1 (the pure article gate functions), judge #1, single judge

**SHA:** `93d4b895eb8942193934f3051b7e4dfb68455d28` (`story/P2b1-pure`, base 8d41029). Lane 1 by stakes: it is the
foundation of the write-once article Record.
**Verdict: FAIL, round 1 of 2.** The XML defence holds up under an exhaustive attack. The key's separator claim holds.
But one hostile item can crash a whole poll, and the Google News fallback key is barely tested.

## Gates

- Suite: 693 passed, 2 runs out of 2.
- ruff and imports (430 files): clean.
- Size: 3 passed, and every new file is under 80 lines.
- **No new dependency:** the requirements, locks and `pyproject.toml` diffs are empty.

## 1. XML safety: no bypass found (strong evidence: an exhaustive scan)

- **The common encodings.** I built a billion-laughs document under utf-7, utf-16-be, utf-32-le, shift_jis,
  iso-2022-jp, utf_16 and EBCDIC (cp037, cp500, cp1026):
  - every ASCII-compatible or NUL-padded form is refused `unsafe_xml` on the raw bytes;
  - the EBCDIC forms escape the byte scan, but expat refuses them as an "unknown encoding", so they never parse.
- **Every codec, systematically.** Of all Python codecs, the ones expat accepts in a declaration all map each ASCII
  byte to itself, and none maps a byte of 0x80 or above to an ASCII letter. So no accepted encoding can hide
  `<!DOCTYPE` or `<!ENTITY` from a case-folded, NUL-stripped scan.
- **No declaration, no attack.** Entity expansion and external entities both need a DOCTYPE. An undeclared `&x;` is
  a `ParseError`, which becomes `not_a_feed`.

| Plant | Result |
|---|---|
| NUL-strip removed | caught |
| Case-sensitive scan | caught |
| DOCTYPE dropped from the forbidden list | caught |
| Size cap raised to 6 MiB | caught |

## 2. The key

**The separator claim holds.**
- `\x1f` counts as white space for `str.split()`, so `normalise` removes it from title, summary and source.
- The guid and URL forms have only one variable part, so a separator in them cannot shift a boundary.
- XML 1.0 forbids U+001F anyway.

**Plants caught:** wrapper guid ignored; publisher keyed on the guid instead of the URL; publisher keyed on the raw
URL; date-only time; no separator; the tracking filter over-broad (`id` prefix), and stripping everything.

**K2 (required): the Google News fallback key's text parts are not pinned.** Each of these plants passes all 693
tests:

| Plant | Result |
|---|---|
| Title removed from the fallback key | survives |
| Summary removed | survives |
| Source removed | survives |

The only fallback test ("two same-title items a minute apart give two keys") varies the time. So a refactor could drop
the title from the key unnoticed. Two different headlines from one outlet in the same second would then share a key,
and the second would be hidden as a revision. That is exactly the R2-2 failure the design closed.

Fix: three tests, each with the same time and two of the three text parts the same, that the third part alone
separates into two keys. Each must fail under its plant.

## 3. Privacy at this layer, and K1 (required): one hostile item crashes the whole poll

The returned structures are clean: `PollRejected` carries a code, and `PollReading.rejected` maps codes to counts. But
`read_poll` lets item-level exceptions escape:

| Input | Result |
|---|---|
| `<link>https://x.example:abc/MARKERPATH?q=MARKERQ</link>` | `ValueError: Port could not be cast to integer value as 'abc'`, from `canonical_url` and `urlsplit().port` |
| `<link>https://[::1/MARKERPATH</link>` | `ValueError: Invalid IPv6 URL` |
| `<pubDate>0001-01-01T00:00:00+05:00</pubDate>` or `9999-12-31T23:59:59-05:00` | `OverflowError: date value out of range`, because `times.py` calls `astimezone` outside the `try` |

In each case the good items in the same poll are lost too, because the whole `read_poll` raises. That breaks
invariant 3 ("nothing fetched is lost at the gate") for one bad item. The exception text also carries part of the URL
(`'abc'`), which a later caller might log.

Fix:
- An unreadable item is a counted item refusal (for example `item_unreadable`), so the reconciliation still holds:
  `items = articles + rejected`.
- `parse_time` catches `OverflowError` around `astimezone` and returns `SEEN`.
- Add tests with my three inputs. Each poll keeps its good item, and nothing raises.

## 4. The tautological plants: fixed for real

Both tests now pin the literal (`MAX_POLL_BYTES == 5 * 1024 * 1024` and `MAX_FIELD_CHARS == 20_000`), so raising
either constant fails: my plants of 6 MiB and 30,000 are caught. The boundary inputs are still built from the constant,
but the pin makes that harmless. No other test imports a guarded constant (`TRACKING_*`, `SEPARATOR`, `FORBIDDEN` and
`FORMAT` are not imported by the tests), so the pattern does not recur.

## 5. Standards and behaviour

- Small single-purpose modules, with constants at the top of their modules.
- The D3 allow-list is exactly `utm_*`, `fbclid`, `gclid`, `igshid`, `mc_cid` and `mc_eid`. That is as designed, and
  the over-broad plant is caught.
- Times:
  - RFC 822 is read first, then RFC 3339;
  - a time with no zone is read as UTC and flagged `assumed_utc` (the plant is caught);
  - an unreadable time becomes `seen`;
  - a future time is kept, and there is no age check.
- `first_seen_at` is out of the fixed fields (the plant is caught). The article file is deterministic sorted JSON.

## Required to PASS

- **K1:** item-level failures become counted refusals and never crash the poll, plus `OverflowError` in `parse_time`.
- **K2:** three tests pinning the title, summary and source in the fallback key.

## Hard lines

Pure functions: no I/O, no network, nothing committed. No secrets. No new dependency.
