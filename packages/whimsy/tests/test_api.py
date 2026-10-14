"""Tests for the whimsy package boundary: public API and input safety."""
import random
import re

import whimsy
from whimsy import generate_name

NAME_RE = re.compile(r"^[a-z]+_[a-z_]+\d*$")


def test_public_api_is_only_generate_name():
    assert whimsy.__all__ == ["generate_name"]


def test_existing_is_not_mutated():
    existing = {"admiring_agnesi"}
    snapshot = set(existing)
    generate_name(existing, rng=random.Random(5))
    assert existing == snapshot


def test_always_returns_str_in_default_format():
    for seed in range(200):
        name = generate_name(rng=random.Random(seed))
        assert isinstance(name, str)
        assert NAME_RE.match(name)
