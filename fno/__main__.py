import sys

from .cli import main
from .env_file import load_env_file
from .rehearsal.process import install_process


def run(argv: list[str] | None = None) -> int:
    # Windows consoles default to a legacy code page; reports use symbols such as the rupee sign.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    load_env_file()
    install_process()  # story REH1: a rehearsing process's replay clock and HTTP guard; nothing in a real run
    return main(argv)


if __name__ == "__main__":
    sys.exit(run())
