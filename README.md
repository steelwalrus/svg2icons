# svg2icons

Generate PNG icons and a favicon from one SVG.

```sh
uv run svg2icons icon.svg                 # -> ./icons
uv run svg2icons icon.svg ./assets/icons
```

## Setup

Needs [uv](https://docs.astral.sh/uv/getting-started/installation/) and the native Cairo library
used by [CairoSVG](https://cairosvg.org/documentation/).

```sh
brew install cairo                                    # macOS
sudo apt install libcairo2                            # Debian/Ubuntu
```

On macOS, uv-managed Python needs a hint to find Homebrew's Cairo. Add to `~/.zshrc`:

```sh
export DYLD_FALLBACK_LIBRARY_PATH="$(brew --prefix)/lib"
```

On Windows, see [CairoSVG's setup instructions](https://cairosvg.org/documentation/).

Then:

```sh
uv sync
uv run svg2icons --help
```

## Usage

```text
svg2icons SVG [OUTPUT] [--sizes PX [PX ...]]
```

Default sizes are 16, 32, 48, 64, 128, 180, 192, 256, and 512. Output directories are
created as needed.

```text
icons/
├── 16x16.png
├── ...
├── 512x512.png
└── favicon.png
```

`favicon.png` is always 32×32, even with custom sizes.

Custom sizes replace the defaults (integers 1–4096, deduped, ascending):

```sh
uv run svg2icons icon.svg ./assets/icons --sizes 32 180 192 512
```

Use a self-contained SVG with a `viewBox` or explicit dimensions — external linked
resources are not fetched. Transparency is preserved; rectangular artwork is centered
with transparent padding unless the SVG sets `preserveAspectRatio`. See
[CairoSVG's SVG support](https://cairosvg.org/svg_support/) for limits around filters
and fonts.

Re-running replaces matching filenames and leaves other files alone. All PNGs render
before any are written, so an invalid SVG won't clobber existing icons.

## Install in another project

```sh
uv add --dev /path/to/svg2icons     # as a dev dependency
uv tool install /path/to/svg2icons  # or as a standalone command
```

Not published to PyPI.

## Development

```sh
uv run python -m unittest discover -s tests -v
uv build
```

`core.py` owns size validation, naming, and generation (stdlib only, takes a render
function). `renderer.py` wraps CairoSVG, `files.py` writes to disk, `cli.py` wires it up.
