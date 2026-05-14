"""Structured log line parser — converts raw lines into event dicts."""

import json
import re
from datetime import datetime, timezone
from typing import Any

# Simple key=value pattern used for logfmt-style lines
_LOGFMT_PAIR = re.compile(r'(\w+)=("[^"]*"|\S+)')

# Common timestamp field names to promote to the normalised ``_ts`` field
_TS_FIELD_NAMES = ("timestamp", "time", "ts", "@timestamp")


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


def _extract_ts(event: dict[str, Any]) -> str | None:
    """Return the first recognised timestamp value found in *event*, or None.

    Checks a list of common field names so that structured logs which already
    carry a timestamp are not given a second, slightly-later ``_ts`` value.
    """
    for field in _TS_FIELD_NAMES:
        if field in event:
            return str(event[field])
    return None


def parse_line(line: str, source: str = "") -> dict[str, Any]:
    """Parse a single log line into a structured event dict.

    Attempts JSON first, then logfmt.  Falls back to a plain-text event.
    Always injects ``_source`` and ``_ts`` metadata fields.

    If the parsed event already contains a recognised timestamp field
    (e.g. ``timestamp``, ``time``, ``ts``, ``@timestamp``) its value is
    reused for ``_ts`` instead of generating a new wall-clock time.
    """
    line = line.rstrip("\n")

    event: dict[str, Any] = (
        parse_json(line)
        or parse_logfmt(line)
        or {"message": line}
    )

    event.setdefault("_source", source)
    event.setdefault(
        "_ts",
        _extract_ts(event) or datetime.now(timezone.utc).isoformat(),
    )
    return event
