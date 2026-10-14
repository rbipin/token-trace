# Whimsy

A standalone docker-style whimsical name generator (`admiring_agnesi`,
`clever_ramanujan`, ...). Zero dependencies beyond the Python standard library.

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

## License

Word lists adapted from Docker's Apache-2.0-licensed `names-generator.go`;
see `NOTICE`.

whimsy is licensed under Apache-2.0; see `LICENSE`.
