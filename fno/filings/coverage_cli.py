"""`python -m fno data-coverage --filings`: the filings archive's coverage in Drive (story A12), read-only."""

from __future__ import annotations

from ..models import now_ist
from .coverage import HALF_YEAR_TARGET, KindCoverage, half_year_misses, half_year_shares, half_years

SHOWN = 20  # problem lines printed per kind and type of problem
TABLE_HEADER = (
    f"{'filing type':<20} {'companies':>12} {'files':>7} {'present':>7} {'damaged':>7} {'no sha':>6} {'gaps':>5} "
    f"{'no file for a quarter':>21} {'not fetched yet':>15}"
)


def filings_coverage_lines(results: list[KindCoverage], shares: dict) -> list[str]:
    """`shares`: half-year end -> (share with both statements, company -> why it lacks them)."""
    lines = [TABLE_HEADER]
    for r in results:
        lines.append(
            f"{r.kind:<20} {f'{r.covered} of {r.companies}':>12} {r.files:>7} {r.present:>7} {len(r.damaged):>7} "
            f"{len(r.unfingerprinted):>6} {len(r.gaps):>5} {len(r.missing_periods):>21} {len(r.pending):>15}"
        )
    for r in results:
        lines += [f"damaged {r.kind} {line}" for line in r.damaged[:SHOWN]]
        lines += [f"unfingerprinted {r.kind} {line}" for line in r.unfingerprinted[:SHOWN]]
        lines += [f"gap {g.kind} {g.symbol}: {g.reason}" for g in r.gaps]
        lines += [f"no file {line}" for line in r.missing_periods]
        if r.pending:
            lines.append(f"{r.kind}: {len(r.pending)} companies not fetched yet (the work queue has not reached them)")
        if r.outside_layout:
            lines.append(
                f"{r.kind}: {len(r.outside_layout)} files outside the year layout (trial run of 13 Oct 2026, before "
                "the owner's year folders; not used by any reader, safe for the owner to delete by hand)"
            )
    for end, (share, misses) in shares.items():
        below = "" if share >= HALF_YEAR_TARGET else f" (below {HALF_YEAR_TARGET:.0%})"
        lines.append(f"half-year {end}: balance sheet and cash flow for {share:.1%} of companies listed by then{below}")
        lines += [f"  {symbol}: {reason}" for symbol, reason in sorted(misses.items())] if below else []
    complete = all(r.ok for r in results)
    lines.append("result: " + ("every listed file present and fingerprinted" if complete else "INCOMPLETE: see above"))
    return lines


def cmd_filings_coverage(args) -> int:
    from .wiring import (
        build_companies,
        build_filings_coverage,
        build_filings_manifest,
        build_listing_dates,
        build_progress,
    )

    companies, today, manifest, listed = (
        build_companies(),
        now_ist().date(),
        build_filings_manifest(),
        build_listing_dates(),
    )
    results = build_filings_coverage().run(companies, today, build_progress().fetched())
    shares = half_year_shares(manifest, companies, half_years(today), listed)
    shares = {end: (share, half_year_misses(manifest, companies, end, listed)) for end, share in shares.items()}
    print("\n".join(filings_coverage_lines(results, shares)))
    return 0 if all(r.ok for r in results) else 1
