# Whimsy as a standalone Python package — design

Date: 2026-10-14

## Goal

Make `whimsy` (the docker-style name generator in `src/whimsy/`) an installable
Python package that anyone can use with `pip install whimsy` and
`from whimsy import generate_name`. It lives in this repo but ships as its own
distribution, with its own version, license, and release.

## Decisions

| Topic | Decision |
|---|---|
| Distribution | Separate distribution `whimsy`, same repo (`packages/whimsy/`) |
| Name | `whimsy` (404 on PyPI on 2026-10-14; the name is not reserved until the first upload) |
| License | Apache-2.0 (matches the Docker word lists the data is adapted from) |
| `tokentracer` dependency | Declared PyPI dependency `whimsy>=0.1,<1`; dev and CI install the in-repo copy |
| Publishing | Separate workflow, PyPI Trusted Publishing, tag prefix `whimsy-v` |

## Layout

Moves use `git mv` so history is kept.

```text
packages/whimsy/
  pyproject.toml      name=whimsy, version=0.1.0, license=Apache-2.0, requires-python>=3.11
  LICENSE             Apache-2.0 full text
  NOTICE              from src/whimsy/LICENSE-NOTICE.md (Docker attribution + modifications)
  README.md           from src/whimsy/README.md (install line added, in-tree import note removed)
  src/whimsy/         __init__.py, generator.py, wordlists.py (unchanged code)
  tests/              from tests/whimsy/ (imports change to `from whimsy import ...`)
```

`src/whimsy/` and `tests/whimsy/` no longer exist after the move. The public
API stays one function, `generate_name`, with the new `fmt` parameter (see
"Name formats"). The README documents `fmt`.

`requires-python >=3.11` only matches `tokentracer`. The code probably works on
older Python, but this is untested. Lowering it later is not a breaking change.

## Name formats

`generate_name` gets a new optional parameter, `fmt`:

```python
generate_name(existing=None, rng=None, fmt="first_last") -> str
```

| `fmt` | Example |
|---|---|
| `"first_last"` (default) | `admiring_agnesi` |
| `"first-last"` | `admiring-agnesi` |
| `"first last"` | `admiring agnesi` |

- The return type is always `str`. There is no object/dict format.
- Any other `fmt` value raises `ValueError` that lists the valid values.
- `existing` is always compared in the `first_last` form, whatever `fmt` is.
  A name therefore counts as taken however it is written.
- The numeric suffix fallback is appended to the last word in the chosen
  format (`admiring-agnesi2`, `admiring agnesi2`).
- The default keeps today's behavior, so `tokentracer` needs no change for it.
- The surname list contains underscores (for example `bose_jc`, `edvard_moser`).
  In `"first-last"` and `"first last"` formats, those underscores are also
  replaced, so the output has only one kind of separator
  (`admiring-edvard-moser`, `admiring edvard moser`).

Assumption to confirm in review: `first` and `last` mean the adjective and the
surname. The literal words are not part of the output.

### Documentation of `fmt`

The same content appears in two places and must agree:

- **Docstring of `generate_name`** (Google style, like the existing one). The
  `Args:` block gets a `fmt` entry that lists the three values with one example
  each, states the default, and says that an invalid value raises `ValueError`.
  A `Raises:` block lists `ValueError`. The text also says that `existing`
  always uses the `first_last` form.
- **`packages/whimsy/README.md`**. The Usage section shows one call per format
  with its output, notes that the return type is always `str`, and gives the
  `existing` rule and the suffix rule. The signature line shows
  `generate_name(existing=None, rng=None, fmt="first_last")`.

The docstring and README change in the same commit as the code, so they never
describe a parameter that does not exist yet.

## `tokentracer` changes

- `src/project_identity.py:19`: `from .whimsy import generate_name` becomes
  `from whimsy import generate_name`.
- `pyproject.toml`: add `dependencies = ["whimsy>=0.1,<1"]`.
- `requirements.txt`: add `-e packages/whimsy`, so local dev and CI use the
  in-repo copy and do not wait for PyPI.
- `[tool.setuptools.packages.find] include = ["src*"]` needs no change; the
  `tokentracer` wheel stops bundling `whimsy`.

## CI

`ci.yml` runs `python -m pytest -q` from the repo root. After the
`requirements.txt` change it installs `whimsy` and collects
`packages/whimsy/tests/`. Expected: no workflow edit. This is verified during
implementation.

## Release

New workflow `.github/workflows/release-whimsy.yml`:

- Trigger: `release: published`, job-level condition on a tag that starts with
  `whimsy-v` and has the form `whimsy-vMAJOR.MINOR.PATCH`.
- Steps: run the whimsy tests, set the version in `packages/whimsy/pyproject.toml`
  from the tag, build the sdist and wheel, publish with
  `pypa/gh-action-pypi-publish` using OIDC (`id-token: write`, no stored token).
- The existing `.github/scripts/set_version.py` is hard-coded to the `v` tag form
  and to the root `pyproject.toml`. Implementation either adds optional path and
  prefix arguments to it or adds a small whimsy-specific script. Decide in the plan.

Existing `release.yml` also fires on every published release. It gets a guard so
it skips tags that start with `whimsy-v`. Without it, a whimsy release would
build and attach a `tokentracer` wheel and run `bump-version` with a bad tag.

### One-time manual setup (PyPI)

Create a pending Trusted Publisher at pypi.org before the first release:

- PyPI project name: `whimsy`
- Owner / repository: this GitHub repository
- Workflow filename: `release-whimsy.yml`
- Environment: none (or a named one, if the workflow uses it)

### Release order

1. Publish `whimsy` 0.1.0 (tag `whimsy-v0.1.0`).
2. Then release the next `tokentracer` version, which depends on it.

## Tests

Existing tests (`test_generator.py`, `test_wordlists.py`) move with the package
and import the installed `whimsy`. New tests for the package boundary:

- Public API: `whimsy.__all__ == ["generate_name"]`.
- Suffix fallback: if `base` and `base2` are both taken, the result is `base3`.
- `existing` is not mutated by `generate_name`.
- Result is always a `str` matching `^[a-z]+_[a-z_]+\d*$`, over many seeded runs.
- Formats: each of the three `fmt` values gives the expected separator, and the
  same seed gives the same words in every format.
- Default: calling without `fmt` equals `fmt="first_last"`.
- Multi-word surnames (`edvard_moser`) use one separator only in the hyphen and
  space formats.
- `existing` holds `first_last` names; a name taken in that form is avoided
  when `fmt` is `"first-last"` or `"first last"`.
- Suffix fallback keeps the chosen separator (`...-agnesi2`).
- Invalid `fmt` (for example `"object"` or `"FIRST_LAST"`) raises `ValueError`.
- Packaging smoke test (not a pytest test; part of verification): build the
  wheel in a scratch directory, install into a clean venv, import
  `generate_name`, and check that `LICENSE` and `NOTICE` are inside the wheel.

Tests use seeded `random.Random` and no live user data.

## Docs

After the implementation is verified, update `README.md` (layout tree),
`CLAUDE.md` (architecture block and its "extractable" wording),
`docs/ARCHITECTURE.md` (lines 91 and ~493). `docs/DESIGN-HISTORY.md` is
history and stays unchanged.

## Out of scope

- `py.typed` marker
- a command-line interface for `whimsy`
- extracting git history into a separate repo
- publishing `tokentracer` itself to PyPI

## Risks

- PyPI may reject or lose the name before the first upload. Mitigation: do the
  release soon after merge; fall back to `whimsy-names`.
- `tokentracer` installed from a GitHub-release wheel needs `whimsy` on PyPI at
  install time. This is why `whimsy` must be released first.
