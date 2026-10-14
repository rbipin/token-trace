"""Docker-style whimsical name generation with collision avoidance."""
from __future__ import annotations

import random

from .wordlists import ADJECTIVES, SURNAMES

_MAX_ATTEMPTS = 20
_SEPARATORS = {"first_last": "_", "first-last": "-", "first last": " "}


def generate_name(
    existing: set[str] | None = None,
    rng: random.Random | None = None,
    fmt: str = "first_last",
) -> str:
    """Return a unique adjective-plus-surname name not present in *existing*.

    Tries up to ``_MAX_ATTEMPTS`` random combos; if all collide, appends an
    incrementing numeric suffix (Docker's fallback behavior) until unique.

    Args:
        existing: Names already taken. Write them in the ``first_last`` form
            (``admiring_agnesi``) whatever *fmt* is; a name written in another
            form does not count as taken. The set is never modified. Defaults
            to no exclusions (any random name qualifies).
        rng: Optional random source for deterministic tests. Defaults to a
            new ``random.Random()``.
        fmt: Output format, one of ``"first_last"`` (default,
            ``admiring_agnesi``), ``"first-last"`` (``admiring-agnesi``) or
            ``"first last"`` (``admiring agnesi``). In the last two formats,
            underscores inside a surname (``edvard_moser``) are replaced too,
            so the name has one kind of separator. A numeric suffix, if
            needed, is added at the end of the name (``admiring-agnesi2``).

    Returns:
        The name as a ``str``.

    Raises:
        ValueError: If *fmt* is not one of the values above.
    """
    if not isinstance(fmt, str) or fmt not in _SEPARATORS:
        valid = ", ".join(repr(f) for f in _SEPARATORS)
        raise ValueError(f"fmt must be one of {valid}; got {fmt!r}")
    sep = _SEPARATORS[fmt]
    existing = existing if existing is not None else set()
    rng = rng if rng is not None else random.Random()
    for _ in range(_MAX_ATTEMPTS):
        name = f"{rng.choice(ADJECTIVES)}_{rng.choice(SURNAMES)}"
        if name not in existing:
            return name.replace("_", sep)
    suffix = 2
    while f"{name}{suffix}" in existing:
        suffix += 1
    return f"{name}{suffix}".replace("_", sep)
