"""The real committer's three lines are told apart by the one mark, and by nothing else."""

from tests.ingestion.commit_failure.real_lines import real_lines


def test_the_real_lines_are_what_the_committer_says(tmp_path):
    lines = real_lines(tmp_path)
    assert "committed and pushed" in lines.pushed and "nothing new to commit" in lines.nothing
    assert " NOT committed" in lines.failed and " NOT committed" not in lines.pushed + lines.nothing
