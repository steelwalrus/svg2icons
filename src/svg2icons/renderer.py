"""CairoSVG adapter. Native dependencies are loaded only when rendering."""

from defusedxml.ElementTree import fromstring


def render_png(svg: bytes, size: int) -> bytes:
    """Render an SVG onto a square canvas, honoring its preserveAspectRatio."""
    try:
        from cairosvg import svg2png
    except (ImportError, OSError) as exc:
        raise RuntimeError(
            "CairoSVG could not load. Install Cairo (macOS: brew install cairo; "
            "Debian/Ubuntu: sudo apt install libcairo2). On macOS, also set "
            'DYLD_FALLBACK_LIBRARY_PATH="$(brew --prefix)/lib". See README.md for setup.'
        ) from exc

    try:
        root = fromstring(svg)
        if root.tag not in ("svg", "{http://www.w3.org/2000/svg}svg"):
            raise ValueError("The document must have an <svg> root element.")
        return svg2png(
            bytestring=svg,
            output_width=size,
            output_height=size,
            unsafe=False,
        )
    except Exception as exc:
        raise ValueError(f"Could not render SVG: {exc}") from exc
