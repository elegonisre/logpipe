"""CheckpointedTailer: wraps FileTailer and saves read positions via Checkpoint."""

from typing import Generator

from logpipe.checkpoint import Checkpoint
from logpipe.tailer import FileTailer

_SAVE_EVERY = 50  # persist checkpoint every N lines


class CheckpointedTailer:
    """Tails a file and keeps a durable record of the current read offset.

    On the first run the tailer seeks to the last saved offset so that lines
    already processed are not re-emitted after a process restart.
    """

    def __init__(
        self,
        file_path: str,
        checkpoint: Checkpoint,
        poll_interval: float = 0.1,
        save_every: int = _SAVE_EVERY,
    ) -> None:
        self._file_path = file_path
        self._checkpoint = checkpoint
        self._poll_interval = poll_interval
        self._save_every = save_every
        self._tailer = FileTailer(file_path, poll_interval=poll_interval)

    def tail(self, max_lines: int = 0) -> Generator[str, None, None]:
        """Yield lines from the tailed file, checkpointing progress.

        Parameters
        ----------
        max_lines:
            Stop after yielding this many lines (0 = run forever).
        """
        saved_offset = self._checkpoint.get(self._file_path)
        if saved_offset is not None:
            self._tailer.seek(saved_offset)

        count = 0
        for line in self._tailer.tail(max_lines=max_lines):
            yield line
            count += 1
            self._checkpoint.set(self._file_path, self._tailer.offset)
            if count % self._save_every == 0:
                self._checkpoint.save()

        # Final save when the generator is exhausted (max_lines reached).
        self._checkpoint.save()
