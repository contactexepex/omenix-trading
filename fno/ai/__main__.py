"""What an AI book's routine runs (stories F1 and G5); standard library only, so no install is needed first:

python -m fno.ai brief '<the fired text>'   # checks it (a v2 or v4 pointer), prints the versioned prompt and the input
python -m fno.ai seal .ai_book/answer.json  # checks the answer, publishes the commitment before the run's deadline
python -m fno.ai reveal                     # at the reveal time (15:15:10, v4 15:10:10; at most 9 minutes' wait a
                                            # call, else "run reveal again"), publishes the answer and its salt
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .book import BookStepRefused
from .book_wiring import build_book_session
from .transport import PublishFailed

# every refusal of the pointer, prompt, export, answer or seal is a ValueError; a missing answer file is an OSError
REFUSALS = (BookStepRefused, PublishFailed, ValueError, OSError)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m fno.ai", description="an AI book's daily forecast steps")
    steps = parser.add_subparsers(dest="step", required=True)
    steps.add_parser("brief", help="check the fired text, print the prompt and the input").add_argument("text")
    steps.add_parser("seal", help="check the answer and publish its commitment").add_argument("answer", type=Path)
    steps.add_parser("reveal", help="at the reveal time, publish the answer and its salt (run again while early)")
    args = parser.parse_args(argv)
    session = build_book_session()
    try:
        if args.step == "brief":
            session.brief(args.text)
        elif args.step == "seal":
            session.seal(args.answer)
        else:
            session.reveal()
    except REFUSALS as refused:
        print(f"refused: {refused}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
