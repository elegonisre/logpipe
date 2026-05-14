"""Tests for logpipe.tailer.FileTailer."""

import os
import threading
import time

import pytest

from logpipe.tailer import FileTailer


def _collect_lines(tailer: FileTailer, count: int, timeout: float = 2.0) -> list[str]:
    """Run tailer in a thread and collect *count* lines or stop after timeout."""
    results: list[str] = []

    def _run() -> None:
        for line in tailer.tail():
            results.append(line)
            if len(results) >= count:
                break

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    t.join(timeout=timeout)
    return results


def test_tail_yields_new_lines(tmp_path):
    log_file = tmp_path / "app.log"
    log_file.write_text("")  # create empty file

    tailer = FileTailer(str(log_file), poll_interval=0.05)

    def _write_lines():
        time.sleep(0.1)
        with log_file.open("a") as f:
            f.write("line one\n")
            f.write("line two\n")

    writer = threading.Thread(target=_write_lines, daemon=True)
    writer.start()

    lines = _collect_lines(tailer, count=2)
    assert lines == ["line one", "line two"]


def test_tail_waits_for_file_to_appear(tmp_path):
    log_file = tmp_path / "late.log"
    tailer = FileTailer(str(log_file), poll_interval=0.05)

    def _create_and_write():
        time.sleep(0.15)
        log_file.write_text("hello\n")

    threading.Thread(target=_create_and_write, daemon=True).start()
    lines = _collect_lines(tailer, count=1, timeout=2.0)
    assert lines == ["hello"]


def test_repr_contains_path(tmp_path):
    path = str(tmp_path / "x.log")
    tailer = FileTailer(path, poll_interval=0.2)
    assert path in repr(tailer)
    assert "0.2" in repr(tailer)
