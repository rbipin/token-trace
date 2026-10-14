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
