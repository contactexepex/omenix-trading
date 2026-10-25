"""`python -m fno data-repair ...` (story DR1-0): repairs of the Drive data folder that a race left behind.

- `merge-folders <path>`: prints the plan (which copy is kept, every move, every refusal); `--apply` carries it out
  and reads every receipt under the path back. Exit 1 on a refusal or a problem.
- `receipt <path> --writer W --run-id R`: prints the receipt a saved but unreceipted file's bytes prove; `--apply`
  writes it and commits it to main. Exit 1 when refused.
Nothing is ever deleted."""

from __future__ import annotations

from ..models import now_utc

KEPT = "{path}: keep the copy created {created} ({verified}); {count} other copy(ies) emptied and renamed"
MOVE = "  move {path}"
NOTHING = "{path}: one folder, nothing to merge"
MERGED = "{path}: merged; every receipt under it reads back"
RECEIPT = "{path}: receipt sha256 {sha256}, {size} bytes, written {written_at}, writer {writer}, run {run_id}"
NOT_COMMITTED_MARK = "NOT committed"  # the committer's refusal line (manifest_commit.NOT_COMMITTED)
RECEIPT_WHAT = "DR1-0 repair of {path}"  # the receipts committer's message names it


def add_repair_parser(subparsers) -> None:
    repair = subparsers.add_parser("data-repair", help="repair the Drive data folder after a race (DR1-0)")
    actions = repair.add_subparsers(dest="repair_action", required=True)
    merge = actions.add_parser("merge-folders", help="merge Drive folders that share one name")
    merge.add_argument("path", help="the Drive path of the doubled folder, e.g. data/daily_runs/full")
    merge.add_argument("--apply", action="store_true", help="carry out the plan (default: print it only)")
    merge.set_defaults(func=cmd_merge_folders)
    receipt = actions.add_parser("receipt", help="receipt a saved Drive file that has none")
    receipt.add_argument("path", help="the Drive path of the file, area included")
    receipt.add_argument("--writer", required=True, help="the job that saved the file")
    receipt.add_argument("--run-id", required=True, help="the run that saved the file")
    receipt.add_argument("--apply", action="store_true", help="write and commit the receipt (default: print it)")
    receipt.set_defaults(func=cmd_receipt)


def cmd_merge_folders(args, out=print, merge=None) -> int:

    from .drive_items import PathAmbiguous, PathNotFound
    from .repair_wiring import build_folder_merge

    merge = merge or build_folder_merge()
    try:
        plan = merge.plan(args.path)
    except (PathNotFound, PathAmbiguous) as refusal:
        out(str(refusal))
        return 1
    if plan.kept is None and not plan.refusals:
        out(NOTHING.format(path=args.path))
        return 0
    if plan.kept is not None:
        verified = "holds the most files matching their receipts"
        out(KEPT.format(path=args.path, created=plan.kept.created, verified=verified, count=len(plan.emptied)))
        for move in plan.moves:
            out(MOVE.format(path=move.path))
    for refusal in plan.refusals:
        out(refusal)
    if plan.refusals or not args.apply:
        return 1 if plan.refusals else 0
    problems = merge.apply(plan, now_utc().date())
    for problem in problems:
        out(problem)
    if not problems:
        out(MERGED.format(path=args.path))
    return 1 if problems else 0


def cmd_receipt(args, out=print, repair=None, committer=None) -> int:
    from .receipt_repair import ReceiptRefused
    from .repair_wiring import build_receipt_repair

    repair = repair or build_receipt_repair()
    try:
        receipt = repair.receipt_for(args.path, args.writer, args.run_id)
        out(RECEIPT.format(**receipt.__dict__))
        if not args.apply:
            return 0
        repair.write(receipt)
    except ReceiptRefused as refusal:
        out(str(refusal))
        return 1
    if committer is None:
        from .data_wiring import build_receipt_committer

        committer = build_receipt_committer()
    line = committer.commit(RECEIPT_WHAT.format(path=args.path))
    out(line)
    return 1 if NOT_COMMITTED_MARK in line else 0
