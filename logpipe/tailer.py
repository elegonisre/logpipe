"""File tailer: follows a log file and yields new lines as they appear."""

import os
import time
from collections.abc import Generator


class FileTailer:
    """Tail a single file, yielding new lines as they are written."""

    def __init__(self, path: str, poll_interval: float = 0.1) -> None:
        self.path = path
        self.poll_interval = poll_interval
        self._file = None
        self._inode: int | None = None

    def _open(self) -> None:
        self._file = open(self.path, "r", encoding="utf-8")
        self._inode = os.fstat(self._file.fileno()).st_ino
        self._file.seek(0, 2)  # seek to end on first open

    def _reopen_if_rotated(self) -> bool:
        """Return True and reopen if the file has been rotated."""
        try:
            current_inode = os.stat(self.path).st_ino
        except FileNotFoundError:
            return False
        if current_inode != self._inode:
            self._file.close()
            self._open()
            self._file.seek(0)  # read from beginning of new file
            return True
        return False

    def tail(self) -> Generator[str, None, None]:
        """Yield lines from the tailed file indefinitely."""
        while not os.path.exists(self.path):
            time.sleep(self.poll_interval)

        self._open()
        try:
            while True:
                self._reopen_if_rotated()
                line = self._file.readline()
                if line:
                    yield line.rstrip("\n")
                else:
                    time.sleep(self.poll_interval)
        finally:
            if self._file and not self._file.closed:
                self._file.close()

    def __repr__(self) -> str:
        return f"FileTailer(path={self.path!r}, poll_interval={self.poll_interval})"
