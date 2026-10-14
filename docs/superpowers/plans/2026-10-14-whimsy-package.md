# Whimsy Package Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn `src/whimsy/` into a separately published `whimsy` PyPI distribution (Apache-2.0) with a new `fmt` name-format parameter, and make `tokentracer` depend on it.

**Architecture:** `whimsy` moves to `packages/whimsy/` (src layout, own `pyproject.toml`, own tests, own release workflow). `tokentracer` declares `whimsy>=0.1,<1` as a dependency and imports it as `from whimsy import generate_name`; dev and CI install the in-repo copy with `-e packages/whimsy`. `generate_name` gains `fmt` (`"first_last"` default, `"first-last"`, `"first last"`), always returns `str`.

**Tech Stack:** Python 3.11+, setuptools (src layout), pytest, GitHub Actions, PyPI Trusted Publishing.

**Spec:** `docs/superpowers/specs/2026-10-14-whimsy-package-design.md`

## Global Constraints

- `whimsy` runtime: Python standard library only.
- `whimsy`: `requires-python >=3.11`, license `Apache-2.0`, first version `0.1.0`, distribution and import name `whimsy`.
- `tokentracer` dependency string: `whimsy>=0.1,<1`.
- Public API stays one function: `generate_name(existing=None, rng=None, fmt="first_last") -> str`. The return type is always `str`; there is no object/dict format.
- `fmt` values: `"first_last"` (default), `"first-last"`, `"first last"`. Any other value raises `ValueError`.
- `existing` is always compared in the `first_last` form, whatever `fmt` is.
- In the hyphen and space formats, underscores inside a surname are replaced too (`admiring-edvard-moser`).
- Release tag prefix: `whimsy-v` (form `whimsy-vMAJOR.MINOR.PATCH`). Publishing uses PyPI Trusted Publishing (OIDC, no stored token).
- Tests use synthetic data and seeded `random.Random`; never collect live user data or touch a remote store.
- Docstring and README for `fmt` change in the same commit as the code.
- **Commits:** every "Commit" step below is a checkpoint. Run it only when the user has asked for commits (global rule: never commit unless asked). Use Conventional Commits, imperative mood, ~50-char summary, no `Co-authored-by` trailer.
- Work from the repo root `/Users/bipin/repo/TokenTracer`. Scratch files go in `/private/tmp/claude-501/-Users-bipin-repo-TokenTracer/c2908bb6-3618-43d6-9fa9-6c6d66c8a102/scratchpad` (called `$SCRATCH` below).

## Review Focus

Input classes the spec implies, most likely to bite first. Each has a test in the task named.

1. `fmt` that is not a valid string: wrong case (`"FIRST_LAST"`), `"object"`, `None`, a list. Must raise `ValueError`, never `TypeError`/`KeyError`. (Task 3)
2. A caller passes already-formatted names back in `existing` (`"admiring-agnesi"`). The documented rule says only the `first_last` form counts. Pin the rule so it cannot change by accident. (Task 3)
3. Multi-word surnames (`bose_jc`, `ray_pc`, `yash_pal`, `edvard_moser`) in the hyphen and space formats: one separator only. (Task 3)
4. Pool exhausted with a non-default `fmt`: suffix goes on the end and keeps the separator. (Task 3)
5. Malformed or foreign release tags: `v1.2.3`, `whimsy-v1.2`, `whimsy-1.2.3`. The version script must exit non-zero and leave `pyproject.toml` unchanged. (Task 4)

---

### Task 1: Move whimsy into `packages/whimsy` and wire `tokentracer` to it

**Files:**
- Move: `src/whimsy/{__init__,generator,wordlists}.py` → `packages/whimsy/src/whimsy/`
- Move: `src/whimsy/README.md` → `packages/whimsy/README.md`
- Move: `src/whimsy/LICENSE-NOTICE.md` → `packages/whimsy/NOTICE`
- Move: `tests/whimsy/test_generator.py`, `tests/whimsy/test_wordlists.py` → `packages/whimsy/tests/`
- Delete: `tests/whimsy/__init__.py`, the empty `src/whimsy/` and `tests/whimsy/` directories
- Create: `packages/whimsy/pyproject.toml`, `packages/whimsy/LICENSE`
- Modify: `requirements.txt`, `pyproject.toml`, `src/project_identity.py:19`

**Interfaces:**
- Produces: importable `whimsy` package exposing `generate_name(existing=None, rng=None)` (unchanged behavior; `fmt` comes in Task 3). Tasks 2 and 3 import `from whimsy import generate_name` and `whimsy.generator` / `whimsy.wordlists`.

- [ ] **Step 1: Move the files with history**

```bash
mkdir -p packages/whimsy/src packages/whimsy/tests
git mv src/whimsy packages/whimsy/src/whimsy
git mv packages/whimsy/src/whimsy/README.md packages/whimsy/README.md
git mv packages/whimsy/src/whimsy/LICENSE-NOTICE.md packages/whimsy/NOTICE
git mv tests/whimsy/test_generator.py tests/whimsy/test_wordlists.py packages/whimsy/tests/
git rm -q tests/whimsy/__init__.py
find packages/whimsy tests/whimsy src/whimsy -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null
rmdir tests/whimsy 2>/dev/null; ls src/whimsy tests/whimsy 2>&1 | head
```

Expected: the last `ls` reports both directories do not exist. `git status --short` shows renames (`R`), not delete+add pairs, for the moved files.

- [ ] **Step 2: Point the moved tests at the installed package**

In `packages/whimsy/tests/test_generator.py` replace the two imports and the docstring:

```python
"""Tests for the whimsy name generator. Imports only from whimsy."""
import random
import re

from whimsy import generate_name
from whimsy.wordlists import ADJECTIVES, SURNAMES
```

In `packages/whimsy/tests/test_wordlists.py`:

```python
"""Tests for the whimsy word lists. Imports only from whimsy (standalone component)."""
from whimsy.wordlists import ADJECTIVES, SURNAMES
```

Leave every test body unchanged.

- [ ] **Step 3: Run the moved tests and verify the expected failure**

Run: `python3 -m pytest packages/whimsy/tests -q`
Expected: collection ERROR, `ModuleNotFoundError: No module named 'whimsy'` (the package is not installed yet).

- [ ] **Step 4: Create the package metadata**

Create `packages/whimsy/pyproject.toml`:

```toml
[build-system]
requires = ["setuptools>=77", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "whimsy"
version = "0.1.0"
description = "Docker-style whimsical name generator (admiring_agnesi, clever_ramanujan, ...)"
readme = "README.md"
license = "Apache-2.0"
license-files = ["LICENSE", "NOTICE"]
requires-python = ">=3.11"
keywords = ["names", "generator", "docker", "random", "whimsical"]

[tool.setuptools.packages.find]
where = ["src"]
```

Fetch the verbatim Apache-2.0 text:

```bash
curl -fsSL https://www.apache.org/licenses/LICENSE-2.0.txt -o packages/whimsy/LICENSE
head -n 3 packages/whimsy/LICENSE; wc -l packages/whimsy/LICENSE
```

Expected: first lines read `Apache License` / `Version 2.0, January 2004`; about 200 lines. If the download fails, stop and tell the user; do not hand-type the license.

- [ ] **Step 5: Add the in-repo install to `requirements.txt`**

Append to `requirements.txt` (keep the existing lines):

```text
# In-repo whimsy package (declared dependency of tokentracer; PyPI copy is used when installed)
-e packages/whimsy
```

- [ ] **Step 6: Install and verify the moved tests pass**

Run: `python3 -m pip install -r requirements.txt && python3 -m pytest packages/whimsy/tests -q`
Expected: all moved tests PASS (`test_generator.py` and `test_wordlists.py`), zero failures.

- [ ] **Step 7: Switch `tokentracer` to the installed package**

Show the import block first: `sed -n 1,30p src/project_identity.py`. Replace line 19 `from .whimsy import generate_name` with `from whimsy import generate_name`, and keep it grouped with the file's other absolute (stdlib/third-party) imports, before the relative imports, matching the file's existing order.

In the root `pyproject.toml`, add under `[project]` (after `requires-python`):

```toml
dependencies = ["whimsy>=0.1,<1"]
```

- [ ] **Step 8: Run the full suite**

Run: `python3 -m pytest -q`
Expected: all tests PASS, including `tests/test_project_identity.py` and `tests/test_project_resolver.py`. If any test still imports `src.whimsy`, run `grep -rn "src.whimsy\|\.whimsy" src tests` and fix only that import.

- [ ] **Step 9: Commit**

```bash
git add -A packages/whimsy tests src requirements.txt pyproject.toml
git commit -m "refactor(whimsy): move to packages/whimsy distribution"
```

---

### Task 2: Pin the package boundary

**Files:**
- Create: `packages/whimsy/tests/test_api.py`

**Interfaces:**
- Consumes: `whimsy.generate_name(existing=None, rng=None)`, `whimsy.__all__` from Task 1.

These tests pin behavior that already exists, so they PASS on the first run. That is intended (characterization tests for the new package boundary).

- [ ] **Step 1: Write the tests**

```python
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
```

- [ ] **Step 2: Run them**

Run: `python3 -m pytest packages/whimsy/tests/test_api.py -q`
Expected: 3 passed.

- [ ] **Step 3: Commit**

```bash
git add packages/whimsy/tests/test_api.py
git commit -m "test(whimsy): pin public API and input safety"
```

---

### Task 3: Add the `fmt` parameter (code, docstring, README together)

**Files:**
- Modify: `packages/whimsy/src/whimsy/generator.py`
- Modify: `packages/whimsy/README.md`
- Create: `packages/whimsy/tests/test_formats.py`

**Interfaces:**
- Consumes: `ADJECTIVES`, `SURNAMES` from `whimsy.wordlists`; `generate_name` from Task 1.
- Produces: `generate_name(existing: set[str] | None = None, rng: random.Random | None = None, fmt: str = "first_last") -> str`. Module constant `whimsy.generator._SEPARATORS`.

- [ ] **Step 1: Write the failing tests**

Create `packages/whimsy/tests/test_formats.py`:

```python
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
```

- [ ] **Step 2: Run the tests and verify the expected failure**

Run: `python3 -m pytest packages/whimsy/tests/test_formats.py -q`
Expected: FAIL. The parametrized cases that pass `fmt=` fail with `TypeError: generate_name() got an unexpected keyword argument 'fmt'`. `test_default_is_first_last` also fails the same way.

- [ ] **Step 3: Implement `fmt`**

Replace the contents of `packages/whimsy/src/whimsy/generator.py` with:

```python
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
```

- [ ] **Step 4: Run the new tests and the whole package suite**

Run: `python3 -m pytest packages/whimsy/tests -q`
Expected: all PASS (`test_formats.py`, `test_api.py`, and the moved tests).

- [ ] **Step 5: Document `fmt` in the README**

Replace the "Usage" and following paragraph of `packages/whimsy/README.md` (everything between `## Usage` and `## License`) with:

````markdown
## Install

```bash
pip install whimsy
```

## Usage

```python
from whimsy import generate_name

generate_name()                                      # 'admiring_agnesi'
generate_name(fmt="first-last")                      # 'admiring-agnesi'
generate_name(fmt="first last")                      # 'admiring agnesi'
generate_name(existing={"admiring_agnesi"})          # avoid taken names
```

`generate_name(existing=None, rng=None, fmt="first_last")` always returns a
`str`: an adjective followed by a surname.

| `fmt` | Example |
|---|---|
| `"first_last"` (default) | `admiring_agnesi` |
| `"first-last"` | `admiring-agnesi` |
| `"first last"` | `admiring agnesi` |

- Any other `fmt` raises `ValueError`.
- `existing` is always written in the `first_last` form, whatever `fmt` is.
  A name written in another form does not count as taken.
- Some surnames have two words (`edvard_moser`). In the hyphen and space
  formats those are joined with the same separator (`admiring-edvard-moser`).
- After 20 colliding attempts it appends a numeric suffix to the end of the
  name (`admiring-agnesi2`), like Docker's container namer.
- Pass `rng=random.Random(seed)` for repeatable output.

````

In the `## License` section, change `LICENSE-NOTICE.md` to `NOTICE`, and add: `whimsy is licensed under Apache-2.0; see LICENSE.`

- [ ] **Step 6: Run the full suite**

Run: `python3 -m pytest -q`
Expected: all PASS.

- [ ] **Step 7: Commit**

```bash
git add packages/whimsy
git commit -m "feat(whimsy): add fmt parameter for name format"
```

---

### Task 4: Release workflow for `whimsy`

**Files:**
- Create: `.github/scripts/set_whimsy_version.py`
- Create: `tests/test_set_whimsy_version.py`
- Create: `.github/workflows/release-whimsy.yml`
- Modify: `.github/workflows/release.yml` (the `test` job)

**Interfaces:**
- Produces: script CLI `python .github/scripts/set_whimsy_version.py <tag>` run from the repo root; it rewrites `version = "..."` in `packages/whimsy/pyproject.toml`, exits non-zero on a bad tag or missing file/line. The existing `.github/scripts/set_version.py` stays untouched.

- [ ] **Step 1: Write the failing test**

Create `tests/test_set_whimsy_version.py`:

```python
"""Tests for .github/scripts/set_whimsy_version.py (run in a temp copy of the layout)."""
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / ".github" / "scripts" / "set_whimsy_version.py"
PYPROJECT = 'name = "whimsy"\nversion = "0.1.0"\nrequires-python = ">=3.11"\n'


def _run(tmp_path: Path, tag: str) -> subprocess.CompletedProcess:
    target = tmp_path / "packages" / "whimsy" / "pyproject.toml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(PYPROJECT)
    return subprocess.run(
        [sys.executable, str(SCRIPT), tag], cwd=tmp_path, capture_output=True, text=True
    )


def test_sets_version_from_tag(tmp_path):
    result = _run(tmp_path, "whimsy-v1.2.3")
    assert result.returncode == 0, result.stderr
    text = (tmp_path / "packages" / "whimsy" / "pyproject.toml").read_text()
    assert 'version = "1.2.3"' in text
    assert 'requires-python = ">=3.11"' in text


@pytest.mark.parametrize("tag", ["v1.2.3", "whimsy-v1.2", "whimsy-1.2.3", "whimsy-v1.2.3-rc1", ""])
def test_bad_tag_exits_nonzero_and_leaves_file_unchanged(tmp_path, tag):
    result = _run(tmp_path, tag)
    assert result.returncode != 0
    assert (tmp_path / "packages" / "whimsy" / "pyproject.toml").read_text() == PYPROJECT


def test_missing_version_line_exits_nonzero(tmp_path):
    target = tmp_path / "packages" / "whimsy"
    target.mkdir(parents=True)
    (target / "pyproject.toml").write_text('name = "whimsy"\n')
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "whimsy-v1.0.0"], cwd=tmp_path, capture_output=True, text=True
    )
    assert result.returncode != 0
```

- [ ] **Step 2: Run it and verify it fails**

Run: `python3 -m pytest tests/test_set_whimsy_version.py -q`
Expected: FAIL (the script does not exist, so `returncode` is 2 and `test_sets_version_from_tag` fails; the bad-tag cases may pass by accident, which is fine).

- [ ] **Step 3: Write the script**

Create `.github/scripts/set_whimsy_version.py`:

```python
"""Set [project].version in packages/whimsy/pyproject.toml from a release tag like whimsy-v1.2.3."""
import pathlib
import re
import sys

tag = sys.argv[1] if len(sys.argv) > 1 else ""
match = re.fullmatch(r"whimsy-v(\d+\.\d+\.\d+)", tag)
if not match:
    sys.exit(f"Tag {tag!r} is not of the form whimsy-vMAJOR.MINOR.PATCH.")
version = match.group(1)

path = pathlib.Path("packages/whimsy/pyproject.toml")
if not path.is_file():
    sys.exit(f"{path} not found; run from the repository root.")
text, count = re.subn(r'(?m)^version = ".*"$', f'version = "{version}"', path.read_text(), count=1)
if count != 1:
    sys.exit("No top-level version line found in packages/whimsy/pyproject.toml.")
path.write_text(text)
print(f"packages/whimsy/pyproject.toml version set to {version}")
```

- [ ] **Step 4: Run the test and verify it passes**

Run: `python3 -m pytest tests/test_set_whimsy_version.py -q`
Expected: all PASS.

- [ ] **Step 5: Create the release workflow**

Create `.github/workflows/release-whimsy.yml`:

```yaml
name: Release whimsy

on:
  release:
    types: [published]

jobs:
  build:
    if: startsWith(github.event.release.tag_name, 'whimsy-v')
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Set version from tag
        env:
          TAG: ${{ github.event.release.tag_name }}
        run: python .github/scripts/set_whimsy_version.py "$TAG"
      - name: Run whimsy tests
        run: |
          pip install pytest -e packages/whimsy
          python -m pytest packages/whimsy/tests -q
      - name: Build sdist and wheel
        run: |
          pip install build
          python -m build packages/whimsy
      - uses: actions/upload-artifact@v4
        with:
          name: whimsy-dist
          path: packages/whimsy/dist/

  publish:
    needs: build
    runs-on: ubuntu-latest
    permissions:
      id-token: write
    steps:
      - uses: actions/download-artifact@v4
        with:
          name: whimsy-dist
          path: dist/
      - uses: pypa/gh-action-pypi-publish@release/v1
```

- [ ] **Step 6: Guard the existing `tokentracer` release**

In `.github/workflows/release.yml`, add an `if` to the `test` job so a `whimsy-v*` release does not build a `tokentracer` wheel. `release` and `bump-version` depend on `test` through `needs`, so GitHub skips them when `test` is skipped.

```yaml
  test:
    if: ${{ !startsWith(github.event.release.tag_name, 'whimsy-v') }}
    uses: ./.github/workflows/ci.yml
```

- [ ] **Step 7: Check the YAML parses**

`pyyaml` is not installed here; use Ruby (ships with macOS):

```bash
for f in .github/workflows/release.yml .github/workflows/release-whimsy.yml; do
  ruby -ryaml -e 'YAML.load_file(ARGV[0]); puts "ok #{ARGV[0]}"' "$f"
done
```

Expected: `ok` for both files. If Ruby is missing, say that the workflows were not parse-checked; do not claim they were. The job conditions cannot be run locally, so report them as unverified until the first real release.

- [ ] **Step 8: Run the full suite**

Run: `python3 -m pytest -q`
Expected: all PASS.

- [ ] **Step 9: Commit**

```bash
git add .github tests/test_set_whimsy_version.py
git commit -m "ci(whimsy): add PyPI release workflow"
```

---

### Task 5: Update project docs

Run this task after Tasks 1-4 are verified (the spec says docs follow verified implementation).

**Files:**
- Modify: `README.md` (tree, line ~190)
- Modify: `CLAUDE.md` (architecture block, line ~108)
- Modify: `docs/ARCHITECTURE.md` (line ~91 table row, lines ~493-496 paragraph)
- Unchanged on purpose: `docs/DESIGN-HISTORY.md` (history)

- [ ] **Step 1: `README.md` project tree**

Delete the line `│  ├─ whimsy/                # Standalone docker-style masked-name generator (extractable, stdlib-only)`. Insert before the `├─ tests/` line:

```text
├─ packages/
│  └─ whimsy/                # Standalone docker-style name generator — own PyPI distribution (Apache-2.0)
```

- [ ] **Step 2: `CLAUDE.md`**

Delete the `  whimsy/ ... only public API is generate_name)` line (line ~108) from the `src/` tree. After the architecture tree, add this paragraph:

```markdown
`packages/whimsy/` is a separate distribution (`whimsy` on PyPI, Apache-2.0, src layout, own `pyproject.toml`, own tests, released with tags `whimsy-vX.Y.Z` through `.github/workflows/release-whimsy.yml`). Its only public API is `generate_name(existing=None, rng=None, fmt="first_last") -> str`. `tokentracer` depends on `whimsy>=0.1,<1`; `requirements.txt` installs the in-repo copy with `-e packages/whimsy`. `src/project_identity.py` is its only in-tree consumer. Publish `whimsy` before releasing a `tokentracer` version that needs a newer one.
```

- [ ] **Step 3: `docs/ARCHITECTURE.md`**

Replace the table row at line ~91:

```text
| `packages/whimsy/` | Separate `whimsy` distribution: stdlib-only `generate_name()` for masked project names |
```

Replace the paragraph at lines ~493-496 with:

```markdown
The whimsical-name implementation lives in `packages/whimsy/`, a separate
stdlib-only distribution (`whimsy`, Apache-2.0) with one public function,
`generate_name(existing=None, rng=None, fmt="first_last")`. `fmt` selects
`first_last`, `first-last` or `first last`; the result is always a `str`.
`tokentracer` declares `whimsy>=0.1,<1` as a dependency, and
`src/project_identity.py` is its only in-tree consumer. Releases use the
`whimsy-vX.Y.Z` tag prefix and a separate PyPI Trusted Publishing workflow.
```

- [ ] **Step 4: Check for stale references**

Run: `grep -rn "src/whimsy\|src\.whimsy\|LICENSE-NOTICE" --include="*.md" --include="*.py" --include="*.toml" --include="*.yml" . | grep -v node_modules | grep -v "docs/superpowers" | grep -v DESIGN-HISTORY`
Expected: no output.

- [ ] **Step 5: Commit**

```bash
git add README.md CLAUDE.md docs/ARCHITECTURE.md
git commit -m "docs: document whimsy as a separate package"
```

---

### Task 6: End-to-end verification

**Files:** none modified.

- [ ] **Step 1: Build the `whimsy` wheel in a scratch directory**

```bash
SCRATCH=/private/tmp/claude-501/-Users-bipin-repo-TokenTracer/c2908bb6-3618-43d6-9fa9-6c6d66c8a102/scratchpad
rm -rf "$SCRATCH/whimsy-build" && mkdir -p "$SCRATCH/whimsy-build"
python3 -m pip install build
python3 -m build --outdir "$SCRATCH/whimsy-build" packages/whimsy
ls "$SCRATCH/whimsy-build"
```

Expected: `whimsy-0.1.0-py3-none-any.whl` and `whimsy-0.1.0.tar.gz`.

- [ ] **Step 2: Check the wheel contents**

```bash
python3 -m zipfile -l "$SCRATCH"/whimsy-build/whimsy-0.1.0-py3-none-any.whl
```

Expected: `whimsy/__init__.py`, `whimsy/generator.py`, `whimsy/wordlists.py`, and under `whimsy-0.1.0.dist-info/` the files `LICENSE` and `NOTICE` (setuptools may place them in `licenses/`). No `tests/` or `src/` entries.

- [ ] **Step 3: Install into a clean venv and use it**

```bash
python3 -m venv "$SCRATCH/whimsy-venv"
"$SCRATCH/whimsy-venv/bin/pip" install -q "$SCRATCH"/whimsy-build/whimsy-0.1.0-py3-none-any.whl
"$SCRATCH/whimsy-venv/bin/python" -c "
from whimsy import generate_name
print(generate_name(), '|', generate_name(fmt='first-last'), '|', generate_name(fmt='first last'))
try:
    generate_name(fmt='object')
except ValueError as e:
    print('ValueError:', e)
"
```

Expected: three names in the three styles, then `ValueError: fmt must be one of 'first_last', 'first-last', 'first last'; got 'object'`.

- [ ] **Step 4: Confirm the `tokentracer` wheel no longer bundles whimsy**

```bash
rm -rf "$SCRATCH/tt-build" && mkdir -p "$SCRATCH/tt-build"
python3 -m build --wheel --outdir "$SCRATCH/tt-build" .
python3 -m zipfile -l "$SCRATCH"/tt-build/tokentracer-*.whl | grep -i whimsy || echo "no whimsy files in tokentracer wheel"
unzip -p "$SCRATCH"/tt-build/tokentracer-*.whl '*/METADATA' | grep -i "Requires-Dist: whimsy"
```

Expected: `no whimsy files in tokentracer wheel`, then `Requires-Dist: whimsy<1,>=0.1`. Note: building the frontend is not needed for this check; if the build fails on missing frontend assets, report that and verify with `python3 -m pytest -q` only.

- [ ] **Step 5: Final full run**

Run: `python3 -m pytest -q`
Expected: all PASS. Report the exact counts. Clean up: `rm -rf "$SCRATCH"/whimsy-build "$SCRATCH"/whimsy-venv "$SCRATCH"/tt-build`.

---

## Manual steps for the user (not automated)

1. **Before the first release,** create a pending Trusted Publisher on PyPI (https://pypi.org/manage/account/publishing/): project `whimsy`, this repository's owner and name, workflow `release-whimsy.yml`, environment left empty.
2. **Check the name is still free** at https://pypi.org/project/whimsy/ right before step 3. If it is taken, the fallback is `whimsy-names` (change `name` in `packages/whimsy/pyproject.toml`, the dependency string, and the docs).
3. **Publish `whimsy` first:** create a GitHub release with tag `whimsy-v0.1.0`. Confirm the `Release whimsy` workflow ran and `tokentracer`'s `Release` workflow was skipped.
4. **Then release `tokentracer`** as usual. Until step 3 is done, `pip install` of a `tokentracer` build from a checkout fails to resolve `whimsy`; use `pip install -r requirements.txt` for development.

## Follow-ups to consider (not in this plan)

- The `whimsy` version in the repo stays at `0.1.0` after a release because the release workflow does not commit a bump back (the `tokentracer` workflow does). Add a bump job later if you want parity.
- `requirements.txt` line 1 says "Runtime: standard library only"; `whimsy` is now a declared dependency (itself stdlib-only). Leave the wording or reword it as its own change.
- `docs/superpowers/specs/` and `docs/superpowers/plans/` hold untracked files from this work; commit them when you decide to.
