from pathlib import Path

from rename_movies import _generate_unique_target


def test_returns_same_path_when_no_conflict(tmp_path: Path) -> None:
    target = tmp_path / "movie.mp4"
    resolved = _generate_unique_target(target, planned_targets=set())
    assert resolved == target


def test_appends_suffix_when_file_exists(tmp_path: Path) -> None:
    target = tmp_path / "movie.mp4"
    target.write_text("existing")

    resolved = _generate_unique_target(target, planned_targets=set())
    assert resolved.name == "movie-1.mp4"
    assert resolved.parent == target.parent


def test_appends_suffix_when_planned_target_conflicts(tmp_path: Path) -> None:
    target = tmp_path / "movie.mp4"
    planned = {target}

    resolved = _generate_unique_target(target, planned_targets=planned)
    assert resolved.name == "movie-1.mp4"


def test_increments_suffix_until_available(tmp_path: Path) -> None:
    target = tmp_path / "movie.mp4"
    (tmp_path / "movie-1.mp4").write_text("taken")
    planned = {target, tmp_path / "movie-2.mp4"}

    resolved = _generate_unique_target(target, planned_targets=planned)
    assert resolved.name == "movie-3.mp4"
