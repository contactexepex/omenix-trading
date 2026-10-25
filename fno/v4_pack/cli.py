"""`python -m fno v4-pack release` (story G10 part 2; G10 completion, criterion 4): the catch-up and today's v4 release.
`python -m fno v4-pack deadline` (criteria 7 and 11): the 15:10 verdicts and the 14:30 overlap watch. In the daily run
each step commits the receipts with the run's one committer; by hand, `--commit` commits and pushes them with this
run's own credentials (the release's push starts `.github/workflows/v4-fire.yml` once G11 lands it). Exit 1 when the
run failed: a refused write, no ended capture yet, a `system_late` today (decision D3), or an unknown receipt time.
Research only."""

from __future__ import annotations


def add_v4_pack_parser(subparsers) -> None:
    parser = subparsers.add_parser("v4-pack", help="protocol v4's daily pack and release record (G10)")
    actions = parser.add_subparsers(dest="v4_pack_cmd", required=True)
    release = actions.add_parser(
        "release", help="catch up missed sessions, then release today's pack (after its capture)"
    )
    release.add_argument("--commit", action="store_true", help="commit and push the receipts (by hand only)")
    deadline = actions.add_parser("deadline", help="the 15:10 verdicts of every live commitment, and the 14:30 watch")
    deadline.add_argument("--commit", action="store_true", help="commit and push the receipts (by hand only)")
    parser.set_defaults(func=cmd_v4_pack)


def cmd_v4_pack(args) -> int:
    from ..config import load_config
    from ..models import now_ist

    cfg, today = load_config(), now_ist().date()
    run = _release(cfg, today) if args.v4_pack_cmd == "release" else _deadline(cfg, today)
    if args.commit:
        from ..storage.data_wiring import build_receipt_committer

        print(build_receipt_committer().commit(f"v4 {args.v4_pack_cmd} {today}"))
    return 1 if run.failed else 0


def _release(cfg: dict, today):
    from ..composition import build_alert_sender
    from .wiring import build_release_run

    run = build_release_run(cfg)
    lines = run.run(today)
    for note in run.notes:  # a V4 expiry the capture could not choose: alerted, never a silent skip
        print(note)
        print(build_alert_sender().send(note))
    print("\n".join(lines))  # last: the step's reason is the release's own line
    return run


def _deadline(cfg: dict, today):
    """The overlap watch's line (posted to #fno-desk; a watch line is no failure of the check), then the verdicts."""
    from ..composition import build_alert_sender
    from .wiring import build_deadline_run, build_overlap_watch

    overlap = build_overlap_watch(cfg).line(today)
    if overlap:
        print(overlap)
        print(build_alert_sender().send(overlap))
    run = build_deadline_run(cfg)
    print("\n".join(run.run(today)))  # last: the step's reason is the check's own line
    return run
