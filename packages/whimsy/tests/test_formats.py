"""Tests for the generate_name `fmt` parameter."""
import random

import pytest

from whimsy import generate_name, generator

FORMATS = {"first_last": "_", "first-last": "-", "first last": " "}


def _pin_words(monkeypatch, adjectives, surnames):
    monkeypatch.setattr(generator, "ADJECTIVES", adjectives)
    monkeypatch.setattr(generator, "SURNAMES", surnames)


def test_default_is_first_last():
    assert generate_name(rng=random.Random(9)) == generate_name(
        rng=random.Random(9), fmt="first_last"
    )


@pytest.mark.parametrize("fmt,sep", FORMATS.items())
def test_each_format_uses_its_separator(monkeypatch, fmt, sep):
    _pin_words(monkeypatch, ("brave",), ("curie",))
    assert generate_name(fmt=fmt) == f"brave{sep}curie"


def test_same_seed_gives_same_words_in_every_format():
    base = generate_name(rng=random.Random(21))
    assert generate_name(rng=random.Random(21), fmt="first-last") == base.replace("_", "-")
    assert generate_name(rng=random.Random(21), fmt="first last") == base.replace("_", " ")


@pytest.mark.parametrize("fmt,sep", [("first-last", "-"), ("first last", " ")])
def test_multi_word_surname_uses_one_separator(monkeypatch, fmt, sep):
    _pin_words(monkeypatch, ("brave",), ("edvard_moser",))
    name = generate_name(fmt=fmt)
    assert name == f"brave{sep}edvard{sep}moser"
    assert "_" not in name


@pytest.mark.parametrize("fmt", ["first-last", "first last"])
def test_existing_is_compared_in_first_last_form(monkeypatch, fmt):
    _pin_words(monkeypatch, ("brave",), ("curie", "noether"))
    sep = FORMATS[fmt]
    for seed in range(20):
        name = generate_name({"brave_curie"}, rng=random.Random(seed), fmt=fmt)
        assert name == f"brave{sep}noether"


@pytest.mark.parametrize("fmt", ["first-last", "first last"])
def test_formatted_names_in_existing_do_not_count_as_taken(monkeypatch, fmt):
    # Documented rule: only the first_last form blocks a name.
    _pin_words(monkeypatch, ("brave",), ("curie",))
    sep = FORMATS[fmt]
    assert generate_name({f"brave{sep}curie"}, fmt=fmt) == f"brave{sep}curie"


@pytest.mark.parametrize("fmt,sep", FORMATS.items())
def test_suffix_fallback_keeps_separator(monkeypatch, fmt, sep):
    _pin_words(monkeypatch, ("brave",), ("curie",))
    existing = {"brave_curie", "brave_curie2"}
    assert generate_name(existing, fmt=fmt) == f"brave{sep}curie3"


def test_suffix_fallback_on_multi_word_surname(monkeypatch):
    _pin_words(monkeypatch, ("brave",), ("edvard_moser",))
    assert generate_name({"brave_edvard_moser"}, fmt="first-last") == "brave-edvard-moser2"


@pytest.mark.parametrize("bad", ["object", "FIRST_LAST", "first_name", "", None, ["first_last"], 3])
def test_invalid_fmt_raises_value_error(bad):
    with pytest.raises(ValueError) as excinfo:
        generate_name(fmt=bad)
    message = str(excinfo.value)
    for valid in FORMATS:
        assert valid in message
