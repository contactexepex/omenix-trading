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

## Addendum 1: round 2, 6ee9b6b: FAIL, two small gaps in the new year check

Reviewed `6ee9b6b1be2436cb7f506c3bb2d8ac06b5bef583`. The branch tip `3707faf` adds one test-only commit, which I also
ran.

**Gates:** 704 passed, 2 runs out of 2. ruff, imports and size are clean.

**K1 is closed (strong evidence: experiment).**
- My three inputs now each become one counted `item_unreadable`, and the poll keeps its good items.
- A wrapper item with a broken link and a valid guid still yields its article (1 article, nothing rejected): a
  wrapper never uses its link.
- I fuzzed 200,000 random `https://` strings through `canonical_url`. It never raised anything but `ValueError`, which
  is caught, so I found no fourth item shape that escapes or aborts the poll.
- The plant that removes the item catch is caught.

**K2 is closed.** The title, summary and source drop plants are each now caught.

**The year band is not an age check.** 1990 and 2100 keep their time; 1989 and 2101 become `seen` with the item kept; a
real 2015 item is unaffected in both RFC 3339 and RFC 822 form; `Mon, 01 Jan 0001` becomes `seen` (no longer 2001).
Nothing is rejected for its time.

### E1 (required): the "equivalent plant" is not equivalent

There *is* an input that passes the year pre-check and overflows: the compact ISO form `00010101T000000+0500`
(also `99991231T235959-0500`).
- `YEAR_WORDS` finds no year in it, because the year is not a standalone 4-digit run.
- `datetime.fromisoformat` accepts it (Python 3.11 and later).
- `astimezone(UTC)` then raises `OverflowError: date value out of range`. I reproduced it.

So the `OverflowError` clause in `times._read` is load-bearing. The plant removing it **survives all 704 tests** only
because no test uses this input. Without the clause, the item would be lost as `item_unreadable` instead of kept as
`seen`.

Fix: a test with `00010101T000000+0500` asserting `(None, "seen")`, and the item kept in `read_poll`. The plant must
then fail. Correct the story's equivalence note too.

### E2 (required, small): a valid time with 4-digit fractional seconds loses its time

`2026-10-26T10:00:00.1234Z` and `2026-10-26T10:00:00.5000+05:30` are valid RFC 3339, and Python reads both. But
`YEAR_WORDS` matches `1234` and `5000` as "years". They fall outside the band, so the item gets `time_source=seen`
and its real published time is dropped from a write-once Record file.

Fix: add `.` to the look-behind (`(?<![+\-:.\d])`), or apply the text scan only to the RFC 822 path, where the
`0001` → 2001 accident lives. Add a test with `.1234`.

**Verdict at 6ee9b6b: FAIL (round 2).** Both fixes are about a line plus a test each. Under the two-round rule this goes
to the orchestrator.

## Addendum 2: the routed SHA is 3707faf; how narrow the catch is

The orchestrator routed `3707faf56798ec983be4c9bf95e5a980ac545a57`. I had already run it in Addendum 1: 704 passed, and
E1 and E2 apply unchanged. Its one added test, the hostile-item privacy test, passes, and the reconciliation balances
(4 items = 1 article + 3 `item_unreadable`).

**Narrow catch: passes, with one caveat (code read).** `read_poll` catches `(ValueError, OverflowError)` only, not
`Exception`. So a `KeyError`, `AttributeError` or `TypeError` from our own article-building code still raises loudly.

The caveat: `ValueError` is also a type our own code could raise by mistake. Today, nothing in `build_article`,
`canonical_url`, `item_key` or `normalise` raises one except through the standard library (`urlsplit().port`, IPv6
parsing), so this is acceptable as it stands. If a later change adds its own `ValueError`, it would be counted as
`item_unreadable`. Recommended, not required: catch only around `canonical_url(item.link)`, which is the one call that
can raise.

**Verdict at 3707faf: FAIL** for E1 and E2 (Addendum 1). The narrow-catch check passes.

## Addendum 3: bounded re-verify (authorised past round 2), be857dc: PASS

Reviewed `be857dcc02efb5e398e3e2ba375a41026c5f60c3` (`story/P2b1-pure-r3`), which is 3707faf plus 62b33f9, 40e19b5 and
be857dc. The branch tip `ff08a7a` adds one test-only commit (edge pins) on top.

**Gates:** 712 passed, 2 runs out of 2. ruff, imports and size are clean.

**The order, checked in the code: convert first, then check the year.** `_read` calls `astimezone(UTC)` inside its
`try`; `parse_time` checks `found[0].year` afterwards. So the `OverflowError` clause *is* load-bearing, and its
docstring says so, naming `00010101T000000+0500`. Removing the clause is caught by 4 tests. The note matches the code.

**Each scoped item (strong evidence: experiment):**

| Item | Result |
|---|---|
| E1 | `00010101T000000+0500` and `99991231T235959-0500` give `seen`; in `read_poll` the item is kept (`seen`, nothing rejected). |
| E2 | `.1234Z`, the comma form `,1234Z`, `.5000+05:30` and basic `20261026T1234Z` all keep their real time (`published`). The article file holds `2026-10-26T10:00:00+00:00`: real to the second, which is the file's stated precision. The written-year scan runs in `_rfc822` only. |
| Compact implausible year | `18500101T000000+0500` gives `seen`. |
| Not an age check | 2015 keeps its time in RFC 3339 and RFC 822 form. 1989 and 2101 give `seen`; 1990 and 2100 are kept; `Mon, 01 Jan 0001` and an 1850 RFC 822 date give `seen`. Items are always kept. |
| Narrow catch at the source | `canonical_url` raises `UnreadableLink` `from None`, and `read_poll` catches only that. A `ValueError` from our own build propagates: I checked it directly, and a test pins it. |

**Plants, all caught:**

| Plant | Result |
|---|---|
| Overflow clause removed | caught |
| Parsed-year check removed | caught |
| RFC 822 scan removed | caught |
| Scan applied to every path | caught (this is what brings E2 back) |
| `except Exception` | caught |
| URL in the exception | caught |
| Item catch removed | caught |
| Wrapper title removed (K2) | caught |

The hostile-item privacy test is green.

A note, not a finding: the band is applied after UTC conversion. So `1990-01-01T00:00+05:00` (which is 1989 in UTC)
gives `seen`. That edge is a few hours wide and harmless.

**Verdict: PASS (strong evidence).** P2b1 is clear to merge at be857dc. The tip ff08a7a adds tests only.
