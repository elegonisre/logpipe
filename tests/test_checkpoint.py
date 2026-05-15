"""Tests for logpipe.checkpoint."""

import json
import pytest
from pathlib import Path

from logpipe.checkpoint import Checkpoint


@pytest.fixture()
def cp_path(tmp_path: Path) -> Path:
    return tmp_path / "checkpoint.json"


def test_get_returns_none_for_unknown_file(cp_path):
    cp = Checkpoint(str(cp_path))
    assert cp.get("/var/log/app.log") is None


def test_set_and_get_offset(cp_path):
    cp = Checkpoint(str(cp_path))
    cp.set("/var/log/app.log", 1024)
    assert cp.get("/var/log/app.log") == 1024


def test_save_persists_to_disk(cp_path):
    cp = Checkpoint(str(cp_path))
    cp.set("/var/log/app.log", 512)
    cp.save()
    assert cp_path.exists()
    data = json.loads(cp_path.read_text())
    assert data["/var/log/app.log"] == 512


def test_load_restores_offsets(cp_path):
    cp_path.write_text(json.dumps({"/var/log/app.log": 256}))
    cp = Checkpoint(str(cp_path))
    assert cp.get("/var/log/app.log") == 256


def test_load_handles_corrupt_file(cp_path):
    cp_path.write_text("not json{{{")
    cp = Checkpoint(str(cp_path))  # should not raise
    assert cp.get("/var/log/app.log") is None


def test_delete_removes_entry(cp_path):
    cp = Checkpoint(str(cp_path))
    cp.set("/var/log/a.log", 100)
    cp.delete("/var/log/a.log")
    assert cp.get("/var/log/a.log") is None


def test_delete_nonexistent_is_safe(cp_path):
    cp = Checkpoint(str(cp_path))
    cp.delete("/does/not/exist.log")  # must not raise


def test_all_returns_snapshot(cp_path):
    cp = Checkpoint(str(cp_path))
    cp.set("/a", 1)
    cp.set("/b", 2)
    snapshot = cp.all
    assert snapshot == {"/a": 1, "/b": 2}
    # mutating snapshot must not affect internal state
    snapshot["/c"] = 3
    assert cp.get("/c") is None


def test_save_is_atomic_on_success(cp_path):
    cp = Checkpoint(str(cp_path))
    cp.set("/var/log/app.log", 999)
    cp.save()
    # tmp file must be gone after successful save
    assert not cp_path.with_suffix(".tmp").exists()


def test_round_trip_multiple_files(cp_path):
    cp = Checkpoint(str(cp_path))
    cp.set("/a.log", 10)
    cp.set("/b.log", 20)
    cp.save()

    cp2 = Checkpoint(str(cp_path))
    assert cp2.get("/a.log") == 10
    assert cp2.get("/b.log") == 20
