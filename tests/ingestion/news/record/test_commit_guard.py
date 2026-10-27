"""P2b3: the commit guard of news-promote.yml. The workflow's own commit step runs in a throw-away git repository
against a bare origin (real git, the real `check-manifest` command), so what reaches `main` is what is tested."""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import date
from pathlib import Path

import yaml

from fno.ingestion.news import cli as news_cli
from fno.ingestion.news.record.manifest import NewsManifest

ROOT = Path(__file__).resolve().parents[4]
MANIFEST_DIR = "research/data/manifests/news"
MANIFEST, RECEIPTS = f"{MANIFEST_DIR}/articles.csv", "receipts/raw/news"
STEP = "Commit the news manifest and receipts (the manifest only when it is whole)"
SHA = "b" * 64


def step_script() -> str:
    flow = yaml.safe_load((ROOT / ".github/workflows/news-promote.yml").read_text())
    (job,) = flow["jobs"].values()
    return next(s for s in job["steps"] if s.get("name") == STEP)["run"]


def git(cwd, *args, check=True):
    return subprocess.run(["git", *args], cwd=cwd, check=check, capture_output=True, text=True).stdout


class Repo:
    def __init__(self, tmp_path):
        self.origin, self.work = tmp_path / "origin.git", tmp_path / "work"
        git(tmp_path, "init", "-q", "--bare", "-b", "main", str(self.origin))
        git(tmp_path, "clone", "-q", str(self.origin), str(self.work))
        for key, value in (("user.name", "t"), ("user.email", "t@example.com"), ("core.hooksPath", "/dev/null")):
            git(self.work, "config", key, value)
        (self.work / "README").write_text("x")
        git(self.work, "add", "README")
        git(self.work, "commit", "-q", "-m", "init")
        git(self.work, "push", "-q", "origin", "HEAD:main")
        self.bin = tmp_path / "bin"
        self.bin.mkdir()
        (self.bin / "python").symlink_to(sys.executable)

    def write(self, manifest_rows: int, torn: bool):
        folder = self.work / MANIFEST_DIR
        manifest = NewsManifest(folder)
        for n in range(manifest_rows):
            manifest.add(date(2026, 10, 27), f"{n:064x}", "recorded", SHA, 10)
        if torn:
            path = folder / "articles.csv"
            path.write_text(path.read_text().rstrip("\n")[:-30])
        receipt = self.work / RECEIPTS / "articles" / "ab" / "one.json.sha256"
        receipt.parent.mkdir(parents=True)
        receipt.write_text("receipt\n")

    def run_step(self):
        env = {**os.environ, "PATH": f"{self.bin}:{os.environ['PATH']}", "PYTHONPATH": str(ROOT),
               "MANIFEST": MANIFEST, "RECEIPTS": RECEIPTS, "FNO_SLACK_BOT_TOKEN": ""}  # fmt: skip
        return subprocess.run(
            ["bash", "-e", "-c", step_script()], cwd=self.work, env=env, capture_output=True, text=True
        )

    def on_main(self, path: str) -> str | None:
        shown = subprocess.run(
            ["git", "--git-dir", str(self.origin), "show", f"main:{path}"], capture_output=True, text=True
        )
        return shown.stdout if shown.returncode == 0 else None


def test_a_whole_manifest_and_its_receipts_are_committed_and_pushed(tmp_path):
    repo = Repo(tmp_path)
    repo.write(2, torn=False)
    done = repo.run_step()
    assert done.returncode == 0, done.stderr
    assert repo.on_main(MANIFEST).count("recorded") == 2 and repo.on_main(f"{RECEIPTS}/articles/ab/one.json.sha256")


def test_a_torn_manifest_never_reaches_main_but_the_receipts_do_and_the_run_is_red(tmp_path):
    repo = Repo(tmp_path)
    repo.write(2, torn=True)
    done = repo.run_step()
    assert done.returncode == 1 and "manifest_broken" in done.stdout
    assert repo.on_main(MANIFEST) is None  # nothing broken on main
    assert repo.on_main(f"{RECEIPTS}/articles/ab/one.json.sha256")  # the evidence time of the Drive file is kept
    assert not (repo.work / MANIFEST).exists()  # the torn file is discarded so the next pull is clean


def test_a_torn_manifest_over_a_good_committed_one_leaves_main_with_the_good_one(tmp_path):
    repo = Repo(tmp_path)
    repo.write(1, torn=False)
    git(repo.work, "add", "-A")
    git(repo.work, "commit", "-q", "-m", "good")
    git(repo.work, "push", "-q", "origin", "HEAD:main")
    good = repo.on_main(MANIFEST)
    path = repo.work / MANIFEST
    path.write_text(path.read_text() + f"2026-10-27,{'c' * 64},rec")  # a promote killed mid-row
    done = repo.run_step()
    assert done.returncode == 1 and repo.on_main(MANIFEST) == good


def test_the_guard_command_is_loud_and_names_the_range_bound_repair(tmp_path, monkeypatch):
    repo = Repo(tmp_path)
    repo.write(1, torn=True)
    sent, printed = [], []
    monkeypatch.setattr(
        "fno.ingestion.composition.build_alert_sender",
        lambda: type("A", (), {"send": lambda s, m: sent.append(m) or "sent"})(),
    )
    args = type("Args", (), {"folder": repo.work / MANIFEST_DIR})()
    assert news_cli.cmd_news_check_manifest(args, out=printed.append) == 1
    assert printed[0] == "news manifest: manifest_broken" and "same --from..--to range" in sent[0]
    assert "days its range covers" in sent[0]


def test_a_whole_manifest_passes_the_guard_command_and_sends_nothing(tmp_path, monkeypatch):
    repo = Repo(tmp_path)
    repo.write(1, torn=False)
    sent = []
    monkeypatch.setattr(
        "fno.ingestion.composition.build_alert_sender", lambda: type("A", (), {"send": lambda s, m: sent.append(m)})()
    )
    args = type("Args", (), {"folder": repo.work / MANIFEST_DIR})()
    assert news_cli.cmd_news_check_manifest(args, out=lambda line: None) == 0 and sent == []
