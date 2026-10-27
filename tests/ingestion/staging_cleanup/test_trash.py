"""Story S1: the staging deleter is physically limited to `staging/`. It builds its own path from validated parts and
refuses everything else, twice (at the name, and at the last step before Drive). Offline: a fake Drive session."""

from __future__ import annotations

import pytest

from fno.ingestion.staging_cleanup.trash import DriveStagingTrash, NotStagingPath, inside_staging, staged_name

STAMP = "20261019T120000Z"


class Session:
    def __init__(self):
        self.requests = []

    def request(self, method, url, **kwargs):
        self.requests.append((method, url, kwargs))


class Drive:
    """The part of GoogleDriveUploadStore the deleter uses: a lookup by path and the signed-in session."""

    def __init__(self, present=("staging/nse/a.csv/" + STAMP,)):
        self.present, self.drive, self.looked_up = set(present), Session(), []

    def file_id(self, path):
        self.looked_up.append(path)
        return "id-" + path if path in self.present else None


def test_a_staged_copy_is_moved_to_the_trash_not_deleted():
    drive = Drive()
    assert DriveStagingTrash(drive).trash("nse", "a.csv", STAMP) is True
    ((method, url, kwargs),) = drive.drive.requests
    assert method == "patch" and url.endswith("/id-staging/nse/a.csv/" + STAMP) and kwargs["json"] == {"trashed": True}
    assert "delete" not in method


def test_a_copy_that_is_gone_is_not_an_error_and_sends_nothing():
    drive = Drive(present=())
    assert DriveStagingTrash(drive).trash("nse", "a.csv", STAMP) is False and drive.drive.requests == []


@pytest.mark.parametrize(
    "path",
    [
        "raw/nse/a.csv",
        "raw/news/articles/ab/key.json",
        "config/feeds/feeds-v1.json",
        "data/vix/x.csv",
        "revisions/x",
        "staging",  # the staging root itself
        "staging2/nse/a.csv",  # a look-alike
        "Staging/nse/a.csv",
        "staging/../raw/nse/a.csv",
        "/staging/nse/a.csv",
        "",
        "staging//a",
    ],
)
def test_a_deleter_handed_a_path_outside_staging_hard_refuses_before_any_drive_call(path):
    drive = Drive(present=(path,))
    with pytest.raises(NotStagingPath):
        DriveStagingTrash(drive)._trash_path(path)
    assert drive.looked_up == [] and drive.drive.requests == []


@pytest.mark.parametrize(
    ("source", "archive_path", "stamp"),
    [
        ("..", "x", STAMP),
        ("nse", "../raw/x", STAMP),
        ("nse/../..", "raw/x", STAMP),
        ("", "x", STAMP),
        ("nse", "", STAMP),
        ("nse", "/raw/x", STAMP),
        ("nse", "a.csv", "not-a-stamp"),
        ("nse", "a.csv", "../../raw/x"),
        ("nse", "a.csv", ""),
    ],
)
def test_the_parts_cannot_form_a_path_outside_staging(source, archive_path, stamp):
    drive = Drive(present=("x",))
    with pytest.raises(NotStagingPath):
        DriveStagingTrash(drive).trash(source, archive_path, stamp)
    assert drive.looked_up == [] and drive.drive.requests == []


def test_the_names_it_builds_are_always_inside_staging():
    assert staged_name("nse", "a/b.csv", STAMP) == f"staging/nse/a/b.csv/{STAMP}"
    assert inside_staging("staging/x") == "staging/x"
