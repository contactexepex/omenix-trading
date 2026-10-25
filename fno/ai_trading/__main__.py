"""What an AI book's decision routine runs (story F1t); standard library only, so no install is needed first:

python -m fno.ai_trading brief '<the fired text>'       # checks it, prints the model rule, the prompt and the input
python -m fno.ai_trading seal .ai_decision/answer.json  # checks the answer, publishes the sealed commitment
python -m fno.ai_trading reveal                         # from the pointer's reveal time, publishes answer and salt
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ..ai.sealed_publish import SealRefused
from ..ai.transport import PublishFailed
from .book_wiring import build_decision_session
from .session import StepRefused

# every refusal of the pointer, prompt, pack, answer or seal is a ValueError or one of these; a missing file an OSError
REFUSALS = (StepRefused, SealRefused, PublishFailed, ValueError, OSError)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m fno.ai_trading", description="an AI book's daily decision steps")
    steps = parser.add_subparsers(dest="step", required=True)
    steps.add_parser("brief", help="check the fired text, print the rules, prompt and input").add_argument("text")
    steps.add_parser("seal", help="check the answer and publish its commitment").add_argument("answer", type=Path)
    steps.add_parser("reveal", help="from the reveal time, publish the answer and its salt")
    args = parser.parse_args(argv)
    session = build_decision_session()
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
