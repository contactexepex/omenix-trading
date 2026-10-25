"""`python -m fno.school.instructor`: the instructor's command until MS-P1j's `fno school` group registers it."""

import sys

from ...config import load_app_config
from . import wiring
from .outputs.command import run
from .review_wiring import build_review_sources


def main(argv=None) -> int:
    for line in run(sys.argv[1:] if argv is None else argv, load_app_config(), wiring, build_review_sources):
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
