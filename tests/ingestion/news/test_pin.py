"""NP7b/NP8: the pin of a private versioned file against the version the last good run used."""

from __future__ import annotations

from fno.ingestion.news.pin import pin_violation

OLD, NEW = "rolled_back", "damaged"


def test_an_older_version_is_a_rollback_and_the_same_version_with_other_bytes_an_edit_in_place():
    assert pin_violation(2, "a", 3, "a", OLD, NEW) == OLD
    assert pin_violation(3, "b", 3, "a", OLD, NEW) == NEW


def test_the_same_version_with_the_same_bytes_and_any_newer_version_are_fine():
    assert pin_violation(3, "a", 3, "a", OLD, NEW) == ""
    assert pin_violation(4, "z", 3, "a", OLD, NEW) == ""


def test_before_the_first_run_there_is_nothing_to_compare_with():
    assert pin_violation(1, "a", 0, "", OLD, NEW) == "" and pin_violation(0, "", 0, "", OLD, NEW) == ""
