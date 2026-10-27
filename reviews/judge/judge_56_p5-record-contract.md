# Judge 56: P5, the Record contract (`docs/RECORD_CONTRACT.md`), judge #1, single judge

**SHA:** `57e28e27ff6fa39959f5dbd9a1c45c839b60d581` (`story/P5-record-contract`). Lane 1 by subject; the change is
docs and tests only, with no behaviour change.
**Verdict: FAIL, round 1 of 2, on one omission.** The "Not guaranteed" list is silent about which readers verify
against receipts, and the contract's "receipts detect a changed file" overstates it. The 28 rows themselves hold.

## Gates

- Suite: 889 passed.
- ruff and imports (477 files): clean.
- The document is 127 lines.

## 1. The 28 rows (strong evidence: re-run)

I ran `tools/contract_plants.py` with no bytecode written. All 28 come out as the document says: 26 plants caught, and
W2 and W4 survive as "stated only".

I also broke parts of claims that the stated plants do not cover:

| My break | Result |
|---|---|
| W6, the heal half: `FingerprintingStore.put` records the row only for a new file | caught |
| P1, "never prints the value": `Finding.__str__` made to include file text | caught, by `test_finding_str_has_no_value` |

P1's row does not list `test_finding_str_has_no_value`, which is the test that pins its "never prints the value" half.
Adding it is a nit.

I found no vacuous "tested" row.

## 2. The two "stated only" rows

Both are honestly weak.
- **W2:** a direct write leaves no temporary file, so the only test passes either way.
- **W4:** W0 refuses the second file first, so the receipt-level refusal is never reached.

A cheap biting test for W4 obviously exists: call `ReceiptFolder.write` directly with the same path and a different
digest. I recommend it as a follow-up.

## 3. "Not guaranteed": one real gap is missing

**Required.** The document says "Receipts detect a changed file" (under "Recovery is limited") and W5 says "a reader
that goes through the verified cache detects…". The verified cache (`DriveCache.sync`) is run routinely only by
`data-checks.yml`, and only for `MOVED: data/vix` (`data-checks.yml:41, 56`).

Every Record reader named in this document reads Drive **directly**, not through the cache:
- the promotion gate's held-file reads;
- the news writer's held-file compare;
- the cluster run's article reads and its earlier-file read (`cluster_record/wiring.py`: `AreaStore(drive, RAW_AREA)`);
- the feed list.

So today a Drive file in the NSE raw Record, or in `raw/news/`, that is changed behind its receipt is **not detected**
by any scheduled check. The changed bytes are used as they are: clustered, or compared as a revision.

A reader of the contract would take "receipts detect a changed file" as a property of the Record. It is a property only
of the verified-cache readers, and those cover `data/vix` today. That is overstatement by omission, which is the
direction that matters for a contract.

Fix (text only): add a bullet to "Not guaranteed", for example:

> **Receipts are checked only where a reader goes through the verified cache.** Today the scheduled check
> (`data-checks.yml`) verifies only `data/vix`. The gate, the news writer, the cluster run and the feed-list read go
> straight to Drive, so a file changed in Drive behind its receipt is used as it is, not detected.

Narrow the Recovery bullet's sentence to match.

**Nit (text): "only" for the news writers.** "Only" is enforced per package: `cluster_record` has an AST test that only
`writer.py` calls `put`, and the news-record wiring test covers the wiring. It is not enforced repository-wide. Say
"within their packages", as G7 does for promotion.

## 4. `data` tests disclosed

Yes. "How to read a row" says that tests marked `data` (W4, W5) run with `pytest -m data` (`data-checks.yml`), not in the
default suite.

## 5. The keeping-it-true machinery is not vacuous

`tests/test_record_contract.py` failed under each of my six breaks:

| Break | Result |
|---|---|
| A test id renamed in the document | caught |
| A plant id with no row | caught |
| A stated-only row re-marked "tested" | caught |
| A row's test removed | caught |
| A test listed in the document but not in the plants file | caught |
| `EXPECT_SURVIVE` drifting from the stated-only rows | caught |

## 6. Hard lines

None is narrowed. The document only describes. "No credential separation" and "format, not authenticity" are stated
plainly.

## Addendum 1: round 2, 31796d7: PASS

Reviewed `31796d7495a15a9a5f9f5d8bf56d5ca3640ff6c5`, which changes text and the plant list only
(`RECORD_CONTRACT.md` +6/-4, `contract_plants.json` +2/-1).

**The required item is closed.** A new "Not guaranteed" bullet says receipts are verified only through `DriveCache`,
that `data-checks.yml` syncs only `data/vix`, and that the gate, the news writer, the cluster run and the feed list read
Drive directly, so a file changed behind its receipt is not detected there. The Recovery sentence is narrowed to "only
where they are checked". Both statements are accurate against the code (Addendum 0, section 3).

**Nits are closed:** P1 now lists `test_finding_str_has_no_value` (re-running P1's plant gives ok), and the news writers'
"only" now reads "within their packages".

**Gates:** `test_record_contract.py` and `test_code_size.py` pass (9). The record scan applies to the commit.

**A wording nit, not blocking:** the Recovery bullet says "(next bullet)", but the receipts bullet comes *before* it.
It should say "previous bullet". Fix it whenever the document is next touched.

**Verdict: PASS.** P5 can merge.
