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
BOTH_RECEIPTS = f"{RECEIPTS} receipts/_batches"  # the articles run adds both folders to its commit


SCRIPT = ROOT / "ops" / "commit_news_record.sh"


def step_script() -> str:
    """The guard is one script that both news workflows call; the workflow step must be exactly that call."""
    flow = yaml.safe_load((ROOT / ".github/workflows/news-promote.yml").read_text())
    (job,) = flow["jobs"].values()
    assert next(s for s in job["steps"] if s.get("name") == STEP)["run"] == "bash ops/commit_news_record.sh"
    return SCRIPT.read_text()


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

    def run_step(self, extra: str = ""):
        env = {**os.environ, "PATH": f"{self.bin}:{os.environ['PATH']}", "PYTHONPATH": str(ROOT),
               "MANIFEST": MANIFEST, "RECEIPTS": BOTH_RECEIPTS, "FNO_SLACK_BOT_TOKEN": "",
               "EXTRA_MANIFESTS": extra}  # fmt: skip
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
    args = type("Args", (), {"folder": repo.work / MANIFEST_DIR, "file": None})()
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
    args = type("Args", (), {"folder": repo.work / MANIFEST_DIR, "file": None})()
    assert news_cli.cmd_news_check_manifest(args, out=lambda line: None) == 0 and sent == []


def _manifest_file(tmp_path, text):
    folder = tmp_path / "m"
    folder.mkdir(parents=True)
    (folder / "articles.csv").write_text(text)
    return folder


WHOLE_ROW = f"2026-10-27,{'a' * 64},recorded,{SHA},10"
HEADER = "date,article_id,status,sha256,size_bytes\n"


def test_a_complete_last_row_with_no_new_line_is_still_a_broken_file(tmp_path):
    """judge 49 T1: a row that looks whole but ends the file without a new line is a crash signature."""
    folder = _manifest_file(tmp_path, HEADER + WHOLE_ROW)  # no trailing new line
    manifest = NewsManifest(folder)
    assert manifest.skipped == 0 and manifest.problem() == "manifest_broken" and not manifest.well_formed()
    assert NewsManifest(_manifest_file(tmp_path / "ok", HEADER + WHOLE_ROW + "\n")).well_formed()


def _alert_for(tmp_path, monkeypatch, text):
    sent, printed = [], []
    monkeypatch.setattr(
        "fno.ingestion.composition.build_alert_sender",
        lambda: type("A", (), {"send": lambda s, m: sent.append(m) or ""})(),
    )
    args = type("Args", (), {"folder": _manifest_file(tmp_path, text), "file": None})()
    return news_cli.cmd_news_check_manifest(args, out=printed.append), printed, sent


def test_the_alert_text_is_fixed_and_says_what_to_do_for_each_cause(tmp_path, monkeypatch):
    """judge 49 A1: a torn file heals by re-running the range; a not-whole row in a complete file needs a hand fix."""
    code, printed, sent = _alert_for(tmp_path / "a", monkeypatch, HEADER + WHOLE_ROW)
    assert (code, printed[0]) == (1, "news manifest: manifest_broken")
    assert sent == [news_cli.GUARD_ALERTS["manifest_broken"]] and "re-run the same --from..--to range" in sent[0]
    code, printed, sent = _alert_for(tmp_path / "b", monkeypatch, HEADER + "2026-10-27,abc,reco\n")
    assert (code, printed[0]) == (1, "news manifest: manifest_row_skipped")
    assert sent == [news_cli.GUARD_ALERTS["manifest_row_skipped"]] and "fix by hand" in sent[0]
    assert WHOLE_ROW not in "".join(sent) and "abc" not in "".join(sent)  # codes only, never a row


def test_the_broken_branch_of_the_step_never_adds_the_manifest():
    """judge 49 T2, for this design: the broken branch commits receipts but must not `git add` the manifest."""
    run = step_script()
    broken = run[run.index("\n  else") : run.index("\n  fi")]
    assert "git add" not in broken and 'git checkout -- "$manifest"' in broken  # the receipts are added after the loop
    assert run.index('git add -- "$folder"') > run.index("\ndone")  # for both outcomes


def test_a_failed_job_always_alerts_the_desk_channel_even_when_promote_was_killed():
    """judge 50 G2: the repo-standard failure step; a killed promote cannot alert by itself, this step can."""
    flow = yaml.safe_load((ROOT / ".github/workflows/news-promote.yml").read_text())
    (job,) = flow["jobs"].values()
    last = job["steps"][-1]
    assert last["if"] == "${{ failure() && !inputs.dry_run }}" and "continue-on-error" not in last
    assert "build_alert_sender" in last["run"] and "actions/runs/${{ github.run_id }}" in last["run"]
    assert "${{ secrets." not in last["run"]  # the token reaches the command through the job's env only


def test_a_row_torn_inside_the_size_field_with_no_new_line_is_caught_by_the_newline_check_alone(tmp_path):
    """judge 50 G1: `…,recorded,<64 hex>,12` is a whole row to the row check; only the missing new line shows it."""
    manifest = NewsManifest(_manifest_file(tmp_path, HEADER + WHOLE_ROW.rsplit(",", 1)[0] + ",12"))
    assert manifest.skipped == 0 and manifest.problem() == "manifest_broken"


def test_check_manifest_exits_1_for_a_final_row_torn_inside_the_size_field(tmp_path, monkeypatch):
    """judge 50 G1, at the command: the exit code, the printed code and the alert for `…,recorded,<64 hex>,12`."""
    code, printed, sent = _alert_for(tmp_path, monkeypatch, HEADER + WHOLE_ROW.rsplit(",", 1)[0] + ",12")
    assert (code, printed[0]) == (1, "news manifest: manifest_broken") and len(sent) == 1


def test_the_same_script_guards_the_cluster_manifest_and_commits_its_receipts(tmp_path):
    """P2d: news-cluster.yml calls this script too; a torn clusters.csv never reaches main, its receipts do."""
    repo = Repo(tmp_path)
    folder = repo.work / MANIFEST_DIR
    NewsManifest(folder, "clusters.csv").add(date(2026, 10, 27), "a" * 64, "recorded", SHA, 10)
    path = folder / "clusters.csv"
    path.write_text(path.read_text().rstrip("\n")[:-30])  # a run killed mid-row
    receipt = repo.work / "receipts/raw/news/clusters/1/x.json.sha256"
    receipt.parent.mkdir(parents=True)
    receipt.write_text("receipt\n")
    env = {
        **os.environ,
        "PATH": f"{repo.bin}:{os.environ['PATH']}",
        "PYTHONPATH": str(ROOT),
        "COMMIT_MESSAGE": "test: clusters",
        "MANIFEST": f"{MANIFEST_DIR}/clusters.csv",
        "RECEIPTS": "receipts/raw/news/clusters",
        "FNO_SLACK_BOT_TOKEN": "",
    }
    done = subprocess.run(["bash", "-e", str(SCRIPT)], cwd=repo.work, env=env, capture_output=True, text=True)
    assert done.returncode == 1 and "manifest_broken" in done.stdout
    assert repo.on_main(f"{MANIFEST_DIR}/clusters.csv") is None
    assert repo.on_main("receipts/raw/news/clusters/1/x.json.sha256")


def test_a_pull_that_fails_makes_the_step_fail_instead_of_ending_green(tmp_path):
    """judge 54 F1: `git pull && git push` under `set -e` used to exit 0 with nothing pushed."""
    repo = Repo(tmp_path)
    repo.write(2, torn=False)
    git(repo.work, "remote", "set-url", "origin", str(tmp_path / "nowhere.git"))
    done = repo.run_step()
    assert done.returncode != 0 and repo.on_main(MANIFEST) is None


def test_a_push_that_fails_makes_the_step_fail_even_when_the_pull_worked(tmp_path):
    repo = Repo(tmp_path)
    repo.write(2, torn=False)
    git(repo.work, "remote", "set-url", "--push", "origin", str(tmp_path / "nowhere.git"))
    done = repo.run_step()
    assert done.returncode != 0 and repo.on_main(MANIFEST) is None


# ---- the receipt batches (story R2): a half line last never reaches main ---------------------------------------

BATCH = "receipts/_batches/2026/10/20261027T120000Z-aaaaaa.tsv"
WHOLE = "raw/news/articles/ab/one.json\t" + "a" * 64 + "\t1\t2026-10-27T12:00:00+00:00\tw\tr\n"


def write_batch(repo, tail: str) -> None:
    repo.write(1, torn=False)
    batch = repo.work / BATCH
    batch.parent.mkdir(parents=True)
    batch.write_text(WHOLE + WHOLE.replace("one", "two") + tail)


def test_a_batch_file_with_a_half_line_last_is_cut_back_to_its_whole_lines_and_the_run_is_red(tmp_path):
    repo = Repo(tmp_path)
    write_batch(repo, "raw/news/articles/ab/three.json\t" + "b" * 20)
    done = repo.run_step()
    assert done.returncode == 1 and "batch_torn" in done.stdout
    on_main = repo.on_main(BATCH)
    assert on_main == WHOLE + WHOLE.replace("one", "two")  # every whole line kept, the fragment not published
    assert repo.on_main(MANIFEST).count("recorded") == 1  # the rest of the step still ran


def test_a_whole_batch_file_is_committed_unchanged_and_the_run_is_green(tmp_path):
    repo = Repo(tmp_path)
    write_batch(repo, "")
    done = repo.run_step()
    assert done.returncode == 0, done.stderr
    assert repo.on_main(BATCH) == WHOLE + WHOLE.replace("one", "two")


def test_the_repair_cuts_only_a_fragment_and_never_a_whole_line(tmp_path):
    from fno.ingestion.storage.batch_receipts import cut_torn_tails

    folder = tmp_path / "b" / "2026" / "10"
    folder.mkdir(parents=True)
    (folder / "whole.tsv").write_text(WHOLE)
    (folder / "torn.tsv").write_text(WHOLE + "half")
    (folder / "nothing_whole.tsv").write_text("half")
    cut = cut_torn_tails(tmp_path / "b")
    assert [f.name for f in cut] == ["nothing_whole.tsv", "torn.tsv"]
    assert (folder / "whole.tsv").read_text() == WHOLE and (folder / "torn.tsv").read_text() == WHOLE
    assert (folder / "nothing_whole.tsv").read_text() == "" and cut_torn_tails(tmp_path / "absent") == []


def test_the_repair_command_is_loud_with_a_fixed_text_and_quiet_when_every_batch_is_whole(tmp_path, monkeypatch):
    folder = tmp_path / "b" / "2026" / "10"
    folder.mkdir(parents=True)
    (folder / "x.tsv").write_text(WHOLE)
    sent, printed = [], []
    monkeypatch.setattr(
        "fno.ingestion.composition.build_alert_sender",
        lambda: type("A", (), {"send": lambda s, m: sent.append(m) or "sent"})(),
    )
    args = type("Args", (), {"folder": tmp_path / "b"})()
    assert news_cli.cmd_news_repair_batches(args, out=printed.append) == 0 and sent == []
    (folder / "x.tsv").write_text(WHOLE + "fragment-marker")
    assert news_cli.cmd_news_repair_batches(args, out=printed.append) == 1
    assert (
        any("batch_torn" in line for line in printed) and "batch_torn" in sent[0] and "fragment-marker" not in sent[0]
    )


# ---- NP2d: the wrapper index is guarded like the articles manifest ---------------------------------------------------

INDEX = f"{MANIFEST_DIR}/wrappers.csv"


def write_index(repo: Repo, torn: bool) -> None:
    index = NewsManifest(repo.work / MANIFEST_DIR, "wrappers.csv")
    index.add(date(2026, 10, 27), "a" * 64, "recorded", SHA, 10)
    if torn:
        path = repo.work / INDEX
        path.write_text(path.read_text().rstrip("\n")[:-30])


def test_a_whole_wrapper_index_is_committed_with_the_articles_manifest(tmp_path):
    repo = Repo(tmp_path)
    repo.write(1, torn=False)
    write_index(repo, torn=False)
    done = repo.run_step(INDEX)
    assert done.returncode == 0, done.stderr
    assert repo.on_main(MANIFEST) and repo.on_main(INDEX).count("recorded") == 1


def test_a_torn_wrapper_index_never_reaches_main_the_good_articles_manifest_does_and_the_run_is_red(tmp_path):
    repo = Repo(tmp_path)
    repo.write(1, torn=False)
    write_index(repo, torn=True)
    done = repo.run_step(INDEX)
    assert done.returncode == 1 and "manifest_broken" in done.stdout
    assert repo.on_main(INDEX) is None and repo.on_main(MANIFEST).count("recorded") == 1
    assert not (repo.work / INDEX).exists()


def test_the_promote_workflow_names_the_index_as_an_extra_manifest():
    flow = yaml.safe_load((ROOT / ".github/workflows/news-promote.yml").read_text())
    (job,) = flow["jobs"].values()
    assert job["env"]["EXTRA_MANIFESTS"].split("#")[0].strip() == INDEX
