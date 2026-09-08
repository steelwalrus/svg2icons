# svg2icons

Generate a folder of PNG icons from one SVG, using Python and uv.
Inspired by the single-command workflow of [Tauri icons](https://v2.tauri.app/develop/icons/),
with web-friendly defaults for Django and other web apps. This MVP produces PNGs;
it does not generate ICO/ICNS files, platform asset catalogs, or web manifests.

```sh
uv run svg2icons icon.svg
uv run svg2icons icon.svg ./assets/icons
uv run -m svg2icons icon.svg ./assets/icons
```

## Setup

With [uv](https://docs.astral.sh/uv/getting-started/installation/) already installed,
the only additional system dependency is the native Cairo library used by
[CairoSVG](https://cairosvg.org/documentation/). uv manages Python 3.11+ and the
Python dependencies.

On macOS:

```sh
brew install cairo
export DYLD_FALLBACK_LIBRARY_PATH="$(brew --prefix)/lib"
```

The export lets uv-managed Python find Homebrew's Cairo library and applies to
the current terminal session. To make it persistent with zsh (the default macOS
shell), add this line once to `~/.zshrc`:

```sh
export DYLD_FALLBACK_LIBRARY_PATH="$(brew --prefix)/lib"
```

Then open a new terminal, or reload the configuration in the current one:

```sh
source ~/.zshrc
```

With another shell, use its corresponding startup file. This setting is only
needed when Python cannot already find Cairo; it is required by the macOS +
uv-managed Python setup verified for this project.

On Debian/Ubuntu:

```sh
sudo apt install libcairo2
```

On Windows, follow [CairoSVG's platform setup instructions](https://cairosvg.org/documentation/).

Then, from this repository:

```sh
uv sync
uv run svg2icons --help
```

`uv sync` installs CairoSVG and its Python dependencies from `pyproject.toml`;
there is no need to run `uv add cairosvg` separately. Neither command installs
the native Cairo library.

A separate `libffi` installation is normally unnecessary when uv installs a
prebuilt CFFI wheel. If your platform requires compiling CFFI from source,
follow its [build requirements](https://cffi.readthedocs.io/en/stable/installation.html).

## Usage

```text
svg2icons SVG [OUTPUT] [--sizes PX [PX ...]]
```

Without `OUTPUT`, icons go into `./icons` relative to the directory where you run
the command. An explicit relative output path is also relative to that directory.
Missing output directories are created automatically.

The default sizes are **16, 32, 48, 64, 128, 180, 192, 256, and 512** pixels.
Each square PNG is named after its dimensions:

```text
icons/
├── 16x16.png
├── 32x32.png
├── 48x48.png
├── 64x64.png
├── 128x128.png
├── 180x180.png
├── 192x192.png
├── 256x256.png
└── 512x512.png
```

Choose a different set with `--sizes` (place it after the input and output paths):

```sh
uv run svg2icons icon.svg ./assets/icons --sizes 32 180 192 512
```

Custom sizes replace the defaults. Sizes must be integers from 1 to 4096;
duplicates are generated once, in ascending order.

Use a self-contained SVG with a `viewBox` or explicit dimensions. Each size is
rendered directly from the vector source. Transparency is preserved. Rectangular
artwork is centered with transparent padding under SVG's default aspect-ratio
behavior; an explicit `preserveAspectRatio` in your SVG is honored. External linked
resources are not fetched; embed images and styles in the SVG. Rendering follows
[CairoSVG's SVG support](https://cairosvg.org/svg_support/), including its limits
around filters and fonts.

Running the command again replaces files with matching names and keeps unrelated
files, including previously generated sizes no longer requested. All PNGs render
before writing starts, so invalid SVGs leave existing icons alone. Each file is
replaced atomically; a filesystem failure can still leave a mix of old and new
sizes. Errors go to stderr with a nonzero exit code.

## Install in another project

From your Django project, add a local checkout as a development dependency:

```sh
uv add --dev /path/to/svg2icons
uv run svg2icons branding/icon.svg myapp/static/myapp/icons
```

Or install the standalone command from a local checkout:

```sh
uv tool install /path/to/svg2icons
svg2icons icon.svg ./assets/icons
```

This repository builds an installable Python package; these instructions do not
assume a release has been published to PyPI. Django is not a dependency and no
entry in `INSTALLED_APPS` is needed. Reference the resulting files normally:

```html
{% load static %}
<link rel="icon" type="image/png" sizes="32x32" href="{% static 'myapp/icons/32x32.png' %}">
<link rel="apple-touch-icon" sizes="180x180" href="{% static 'myapp/icons/180x180.png' %}">
```

## Development

```sh
uv run python -m unittest discover -s tests -v
uv build
```

The dependency flow stays small: `core.py` owns size validation, naming, and
generation. It receives a rendering function and imports only the standard
library. `renderer.py` adapts CairoSVG, `files.py` handles disk access, and `cli.py`
wires them together. There are no base classes, service containers, or framework
dependencies in the core.

Tests use standard-library `unittest` at the unit level, with doubles for the
renderer and CLI dependencies and temporary directories for file-writing units.
