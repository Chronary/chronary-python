from __future__ import annotations

from urllib.parse import quote

from ._exceptions import InvalidPathParameterError

_REFUSED = frozenset({"", ".", ".."})


def path_segment(value: str) -> str:
    """Encode one caller-supplied ID as a single URL path segment (#2519).

    ``quote(safe="")`` keeps ``/``, ``?``, ``#`` and ``%`` inside the segment,
    so an ID like ``"../agents/agt_1"`` or ``"evt_1?expand=all"`` can't reach
    another resource or add a query string. Quoting leaves dots alone, and a
    ``.`` / ``..`` segment would be resolved by URL normalisation, so those and
    the empty string are refused before any request is sent.
    """
    segment = str(value)
    if segment in _REFUSED:
        raise InvalidPathParameterError(
            f"Invalid ID {segment!r}: a path parameter must not be empty, '.' or '..'. "
            "No request was sent."
        )
    return quote(segment, safe="")
