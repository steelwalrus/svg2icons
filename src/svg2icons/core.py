"""Icon generation policy, independent of the CLI, filesystem, and renderer."""

from collections.abc import Callable, Iterable

DEFAULT_SIZES = (16, 32, 48, 64, 128, 180, 192, 256, 512)
MAX_SIZE = 4096


def generate_icons(
    svg: bytes,
    sizes: Iterable[int] = DEFAULT_SIZES,
    *,
    render: Callable[[bytes, int], bytes],
) -> dict[str, bytes]:
    """Render unique sizes in ascending order; validate before rendering any."""
    sizes = tuple(sizes)
    if not sizes:
        raise ValueError("Choose at least one icon size.")
    if any(type(size) is not int or not 1 <= size <= MAX_SIZE for size in sizes):
        raise ValueError(f"Icon sizes must be whole numbers between 1 and {MAX_SIZE}.")
    return {
        f"{size}x{size}.png": render(svg, size)
        for size in sorted(set(sizes))
    }
