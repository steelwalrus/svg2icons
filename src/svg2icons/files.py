"""Local file input and atomic replacement of individual PNG files."""

from collections.abc import Mapping
from pathlib import Path
from tempfile import TemporaryDirectory


def read_svg(source: Path) -> bytes:
    """Read a local SVG file without changing its XML encoding."""
    if source.suffix.lower() != ".svg":
        raise ValueError("Input must be an .svg file.")
    return source.read_bytes()


def write_icons(icons: Mapping[str, bytes], output: Path) -> None:
    """Replace generated files atomically, leaving unrelated files untouched."""
    output.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=output) as staging:
        for name, png in icons.items():
            temporary = Path(staging) / name
            temporary.write_bytes(png)
            temporary.replace(output / name)
