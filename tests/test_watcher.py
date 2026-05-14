"""Tests for logpipe.watcher.DirectoryWatcher."""

import os
import pytest

from logpipe.watcher import DirectoryWatcher


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _touch(path: str) -> None:
    with open(path, "w") as fh:
        fh.write("")


# ---------------------------------------------------------------------------
# tests
# ---------------------------------------------------------------------------

def test_scan_discovers_existing_files(tmp_path):
    _touch(str(tmp_path / "app.log"))
    _touch(str(tmp_path / "worker.log"))

    found = []
    watcher = DirectoryWatcher(str(tmp_path / "*.log"), found.append)
    count = watcher.scan()

    assert count == 2
    assert sorted(found) == sorted([
        str(tmp_path / "app.log"),
        str(tmp_path / "worker.log"),
    ])


def test_scan_does_not_report_same_file_twice(tmp_path):
    _touch(str(tmp_path / "app.log"))

    found = []
    watcher = DirectoryWatcher(str(tmp_path / "*.log"), found.append)
    watcher.scan()
    count = watcher.scan()

    assert count == 0
    assert len(found) == 1


def test_scan_picks_up_files_added_later(tmp_path):
    found = []
    watcher = DirectoryWatcher(str(tmp_path / "*.log"), found.append)
    watcher.scan()
    assert found == []

    _touch(str(tmp_path / "late.log"))
    count = watcher.scan()

    assert count == 1
    assert found == [str(tmp_path / "late.log")]


def test_scan_ignores_directories(tmp_path):
    os.makedirs(str(tmp_path / "subdir.log"))

    found = []
    watcher = DirectoryWatcher(str(tmp_path / "*.log"), found.append)
    count = watcher.scan()

    assert count == 0
    assert found == []


def test_seen_property_returns_copy(tmp_path):
    _touch(str(tmp_path / "a.log"))
    watcher = DirectoryWatcher(str(tmp_path / "*.log"), lambda p: None)
    watcher.scan()

    seen = watcher.seen
    seen.add("/fake/path.log")
    assert "/fake/path.log" not in watcher.seen


def test_reset_allows_rediscovery(tmp_path):
    _touch(str(tmp_path / "app.log"))

    found = []
    watcher = DirectoryWatcher(str(tmp_path / "*.log"), found.append)
    watcher.scan()
    watcher.reset()
    count = watcher.scan()

    assert count == 1
    assert len(found) == 2


def test_no_match_returns_zero(tmp_path):
    found = []
    watcher = DirectoryWatcher(str(tmp_path / "*.log"), found.append)
    count = watcher.scan()

    assert count == 0
    assert found == []
