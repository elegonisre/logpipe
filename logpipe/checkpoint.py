"""Checkpoint: persists file read positions so tailing can resume after restart."""

import json
import os
from pathlib import Path
from typing import Dict, Optional


class Checkpoint:
    """Stores and retrieves byte offsets for tailed files."""

    def __init__(self, path: str) -> None:
        self._path = Path(path)
        self._offsets: Dict[str, int] = {}
        self._load()

    def _load(self) -> None:
        """Load existing checkpoint data from disk, if present."""
        if self._path.exists():
            try:
                with self._path.open("r") as fh:
                    data = json.load(fh)
                if isinstance(data, dict):
                    self._offsets = {k: int(v) for k, v in data.items()}
            except (json.JSONDecodeError, ValueError, OSError):
                self._offsets = {}

    def save(self) -> None:
        """Flush current offsets to disk atomically."""
        tmp = self._path.with_suffix(".tmp")
        try:
            with tmp.open("w") as fh:
                json.dump(self._offsets, fh)
            os.replace(tmp, self._path)
        except OSError:
            tmp.unlink(missing_ok=True)
            raise

    def get(self, file_path: str) -> Optional[int]:
        """Return the last saved offset for *file_path*, or None."""
        return self._offsets.get(file_path)

    def set(self, file_path: str, offset: int) -> None:
        """Update the in-memory offset for *file_path*."""
        self._offsets[file_path] = offset

    def delete(self, file_path: str) -> None:
        """Remove the offset entry for *file_path*."""
        self._offsets.pop(file_path, None)

    @property
    def all(self) -> Dict[str, int]:
        """Return a snapshot of all tracked offsets."""
        return dict(self._offsets)
