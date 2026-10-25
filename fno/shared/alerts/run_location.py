"""Where the owner reads a run's own lines: its GitHub Actions page, else the command's output (alerts name it)."""

from __future__ import annotations

import os

RUN_URL = "{server}/{repository}/actions/runs/{run}"
NO_RUN_URL = "the command's output (not a GitHub Actions run)"


def run_location(env=os.environ) -> str:
    parts = (env.get("GITHUB_SERVER_URL"), env.get("GITHUB_REPOSITORY"), env.get("GITHUB_RUN_ID"))
    return RUN_URL.format(server=parts[0], repository=parts[1], run=parts[2]) if all(parts) else NO_RUN_URL
