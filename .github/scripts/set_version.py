"""Set [project].version in pyproject.toml from a release tag like v1.2.3."""
import pathlib
import re
import sys

tag = sys.argv[1]
if not re.fullmatch(r"v\d+\.\d+\.\d+", tag):
    sys.exit(f"Tag {tag!r} is not of the form vMAJOR.MINOR.PATCH.")

path = pathlib.Path("pyproject.toml")
text, count = re.subn(
    r'(?m)^version = ".*"$', f'version = "{tag.removeprefix("v")}"', path.read_text(), count=1
)
if count != 1:
    sys.exit("No top-level version line found in pyproject.toml.")
path.write_text(text)
print(f"pyproject.toml version set to {tag.removeprefix('v')}")
