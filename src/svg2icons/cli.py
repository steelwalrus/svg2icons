"""Argument parsing and composition of the application with its adapters."""

import argparse
from collections.abc import Sequence
from importlib.metadata import version
from pathlib import Path

from .core import DEFAULT_SIZES, generate_icons
from .files import read_svg, write_icons
from .renderer import render_png


def build_parser() -> argparse.ArgumentParser:
    """Describe the command without performing any conversion."""
    parser = argparse.ArgumentParser(
        prog="svg2icons",
        description="Generate PNG icons and a 32x32 favicon.png from one SVG.",
    )
    parser.add_argument("source", type=Path, metavar="SVG", help="source SVG file")
    parser.add_argument(
        "output", type=Path, nargs="?", default=Path("icons"), metavar="OUTPUT",
        help="output directory (default: ./icons in the current directory)",
    )
    parser.add_argument(
        "--sizes", type=int, nargs="+", default=DEFAULT_SIZES, metavar="PX",
        help="replace the default sizes: " + ", ".join(map(str, DEFAULT_SIZES))
        + "; favicon.png is always generated at 32x32",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {version('svg2icons')}",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    """Generate icons, reporting expected input and environment errors succinctly."""
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        svg = read_svg(args.source)
        icons = generate_icons(svg, args.sizes, render=render_png)
        write_icons(icons, args.output)
    except (OSError, ValueError, RuntimeError) as exc:
        parser.exit(1, f"{parser.prog}: error: {exc}\n")
    print(f"Created {len(icons)} PNG icons in {args.output.resolve()}")
