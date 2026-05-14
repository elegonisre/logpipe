"""Directory watcher that discovers new log files and registers them with a pipeline."""

import os
import glob
import logging
from typing import Callable, Set

logger = logging.getLogger(__name__)


class DirectoryWatcher:
    """Watches a directory (or glob pattern) for new files and triggers a callback."""

    def __init__(self, pattern: str, on_new_file: Callable[[str], None]) -> None:
        """
        Args:
            pattern: A glob pattern, e.g. '/var/log/app/*.log'
            on_new_file: Callback invoked with the path of each newly discovered file.
        """
        self._pattern = pattern
        self._on_new_file = on_new_file
        self._seen: Set[str] = set()

    def scan(self) -> int:
        """Scan for new files matching the pattern.

        Returns:
            Number of newly discovered files.
        """
        discovered = 0
        try:
            matched = set(glob.glob(self._pattern))
        except Exception as exc:  # pragma: no cover
            logger.warning("glob error for pattern %r: %s", self._pattern, exc)
            return 0

        for path in sorted(matched - self._seen):
            if not os.path.isfile(path):
                continue
            logger.debug("discovered new file: %s", path)
            self._seen.add(path)
            try:
                self._on_new_file(path)
            except Exception as exc:  # pragma: no cover
                logger.error("on_new_file callback failed for %r: %s", path, exc)
            discovered += 1

        return discovered

    @property
    def seen(self) -> Set[str]:
        """Return a copy of the set of already-seen file paths."""
        return set(self._seen)

    def reset(self) -> None:
        """Clear the seen-files cache so all matching files are treated as new."""
        self._seen.clear()
