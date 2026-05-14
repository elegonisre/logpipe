"""Structured log line parser — converts raw lines into event dicts."""

import json
import re
from datetime import datetime, timezone
from typing import Any

# Simple key=value pattern used for logfmt-style lines
_LOGFMT_PAIR = re.compile(r'(\w+)=("[^"]*"|\S+)')


def _strip_quotes(value: str) -> str:
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    return value


def parse_json(line: str) -> dict[str, Any] | None:
    """Try to parse *line* as JSON.  Returns None on failure."""
    try:
        obj = json.loads(line)
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        pass
    return None


def parse_logfmt(line: str) -> dict[str, Any] | None:
    """Try to parse *line* as logfmt (key=value pairs).

    Returns None when no pairs are found.
    """
    pairs = _LOGFMT_PAIR.findall(line)
    if not pairs:
        return None
    return {k: _strip_quotes(v) for k, v in pairs}


def parse_line(line: str, source: str = "") -> dict[str, Any]:
    """Parse a single log line into a structured event dict.

    Attempts JSON first, then logfmt.  Falls back to a plain-text event.
    Always injects ``_source`` and ``_ts`` metadata fields.
    """
    line = line.rstrip("\n")

    event: dict[str, Any] = (
        parse_json(line)
        or parse_logfmt(line)
        or {"message": line}
    )

    event.setdefault("_source", source)
    event.setdefault("_ts", datetime.now(timezone.utc).isoformat())
    return event
