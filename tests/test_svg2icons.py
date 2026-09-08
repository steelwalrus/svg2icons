import io
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import Mock, call, patch

from svg2icons.cli import build_parser, main
from svg2icons.core import DEFAULT_SIZES, MAX_SIZE, generate_icons
from svg2icons.files import read_svg, write_icons
from svg2icons.renderer import render_png

SVG = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"/>'


class GenerationTests(unittest.TestCase):
    def test_defaults_produce_named_icons(self):
        render = Mock(side_effect=lambda svg, size: str(size).encode())
        icons = generate_icons(SVG, render=render)
        self.assertEqual(
            tuple(icons), (*[f"{s}x{s}.png" for s in DEFAULT_SIZES], "favicon.png"),
        )
        self.assertEqual(icons["32x32.png"], b"32")
        self.assertEqual(icons["favicon.png"], icons["32x32.png"])
        self.assertEqual(render.call_args_list, [call(SVG, s) for s in DEFAULT_SIZES])

    def test_custom_sizes_replace_defaults_and_remove_duplicates(self):
        render = Mock(return_value=b"png")
        icons = generate_icons(SVG, iter([192, 32, 192]), render=render)
        self.assertEqual(list(icons), ["32x32.png", "192x192.png", "favicon.png"])
        self.assertEqual(render.call_count, 2)

    def test_favicon_is_rendered_when_custom_sizes_omit_32(self):
        render = Mock(side_effect=lambda svg, size: str(size).encode())
        icons = generate_icons(SVG, [512], render=render)
        self.assertEqual(icons, {"512x512.png": b"512", "favicon.png": b"32"})
        self.assertEqual(render.call_args_list, [call(SVG, 512), call(SVG, 32)])

    def test_invalid_sizes_fail_before_any_rendering(self):
        for sizes in ([], [32, 0], [-1], [MAX_SIZE + 1], [1.5], [True], ["32"]):
            with self.subTest(sizes=sizes):
                render = Mock()
                with self.assertRaises(ValueError):
                    generate_icons(SVG, sizes, render=render)
                render.assert_not_called()

    def test_size_boundaries_are_allowed(self):
        icons = generate_icons(SVG, [1, MAX_SIZE], render=Mock(return_value=b"png"))
        self.assertEqual(
            list(icons), ["1x1.png", f"{MAX_SIZE}x{MAX_SIZE}.png", "favicon.png"],
        )


class FileTests(unittest.TestCase):
    def test_read_svg_preserves_bytes_and_accepts_uppercase_extension(self):
        with TemporaryDirectory() as directory:
            source = Path(directory) / "icon.SVG"
            source.write_bytes(SVG)
            self.assertEqual(read_svg(source), SVG)

    def test_wrong_extension_is_rejected(self):
        with self.assertRaisesRegex(ValueError, r"\.svg"):
            read_svg(Path("icon.png"))

    def test_missing_source_reports_the_path(self):
        with TemporaryDirectory() as directory:
            with self.assertRaises(FileNotFoundError):
                read_svg(Path(directory) / "missing.svg")

    def test_write_creates_directories_and_preserves_unrelated_files(self):
        with TemporaryDirectory() as directory:
            output = Path(directory) / "static" / "icons"
            write_icons({"32x32.png": b"old"}, output)
            unrelated = output / "keep.txt"
            unrelated.write_text("keep")
            write_icons({"32x32.png": b"new", "192x192.png": b"large"}, output)
            self.assertEqual((output / "32x32.png").read_bytes(), b"new")
            self.assertEqual((output / "192x192.png").read_bytes(), b"large")
            self.assertEqual(
                (output / "32x32.png").stat().st_mode & 0o777,
                unrelated.stat().st_mode & 0o777,
            )
            self.assertEqual(unrelated.read_text(), "keep")
            self.assertEqual(len(list(output.iterdir())), 3)

    def test_failed_replace_keeps_old_file_and_cleans_temporary_file(self):
        with TemporaryDirectory() as directory:
            output = Path(directory)
            target = output / "32x32.png"
            target.write_bytes(b"old")
            with patch.object(Path, "replace", side_effect=PermissionError("denied")):
                with self.assertRaises(PermissionError):
                    write_icons({"32x32.png": b"new"}, output)
            self.assertEqual(target.read_bytes(), b"old")
            self.assertEqual(list(output.iterdir()), [target])

    def test_failed_write_keeps_old_file_and_cleans_temporary_file(self):
        def fail_write(path, png):
            with path.open("wb") as file:
                file.write(b"partial")
            raise OSError("disk full")

        with TemporaryDirectory() as directory:
            output = Path(directory)
            target = output / "32x32.png"
            target.write_bytes(b"old")
            with patch.object(Path, "write_bytes", autospec=True, side_effect=fail_write):
                with self.assertRaisesRegex(OSError, "disk full"):
                    write_icons({"32x32.png": b"new"}, output)
            self.assertEqual(target.read_bytes(), b"old")
            self.assertEqual(list(output.iterdir()), [target])


class RendererTests(unittest.TestCase):
    def test_uses_square_dimensions_and_safe_rendering(self):
        convert = Mock(return_value=b"png")
        with patch.dict("sys.modules", cairosvg=SimpleNamespace(svg2png=convert)):
            self.assertEqual(render_png(SVG, 32), b"png")
        convert.assert_called_once_with(
            bytestring=SVG, output_width=32, output_height=32, unsafe=False,
        )

    def test_rejects_malformed_non_svg_and_entity_documents(self):
        documents = [
            b"", b"not XML", b"<svg>", b"<html/>",
            b'<svg xmlns="https://example.com/not-svg"/>',
            b'<!DOCTYPE svg [<!ENTITY x "entity">]><svg>&x;</svg>',
        ]
        for svg in documents:
            with self.subTest(svg=svg):
                convert = Mock()
                with patch.dict("sys.modules", cairosvg=SimpleNamespace(svg2png=convert)):
                    with self.assertRaisesRegex(ValueError, "Could not render SVG"):
                        render_png(svg, 32)
                convert.assert_not_called()

    def test_renderer_errors_have_context(self):
        convert = Mock(side_effect=ValueError("undefined size"))
        with patch.dict("sys.modules", cairosvg=SimpleNamespace(svg2png=convert)):
            with self.assertRaisesRegex(ValueError, "Could not render SVG: undefined size"):
                render_png(SVG, 32)

    def test_missing_cairo_reports_setup_instructions(self):
        with patch.dict("sys.modules", cairosvg=None):
            with self.assertRaisesRegex(RuntimeError, "Install Cairo"):
                render_png(SVG, 32)


class CliTests(unittest.TestCase):
    def test_default_arguments(self):
        args = build_parser().parse_args(["branding/icon.svg"])
        self.assertEqual(args.source, Path("branding/icon.svg"))
        self.assertEqual(args.output, Path("icons"))
        self.assertEqual(args.sizes, DEFAULT_SIZES)

    def test_explicit_directory_and_sizes(self):
        args = build_parser().parse_args(
            ["icon.svg", "assets/my icons", "--sizes", "32", "192"],
        )
        self.assertEqual(args.output, Path("assets/my icons"))
        self.assertEqual(args.sizes, [32, 192])

    def test_missing_source_and_invalid_size_syntax_show_usage(self):
        for argv in ([], ["icon.svg", "--sizes"], ["icon.svg", "--sizes", "tiny"]):
            with self.subTest(argv=argv), redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as error:
                    main(argv)
                self.assertEqual(error.exception.code, 2)

    def test_main_connects_generation_to_requested_output(self):
        icons = {"32x32.png": b"png"}
        stdout = io.StringIO()
        with (
            patch("svg2icons.cli.read_svg", return_value=SVG) as read,
            patch("svg2icons.cli.generate_icons", return_value=icons) as generate,
            patch("svg2icons.cli.write_icons") as write,
            redirect_stdout(stdout),
        ):
            main(["icon.svg", "assets/icons", "--sizes", "32"])
        read.assert_called_once_with(Path("icon.svg"))
        generate.assert_called_once_with(SVG, [32], render=render_png)
        write.assert_called_once_with(icons, Path("assets/icons"))
        self.assertIn("Created 1 PNG icons", stdout.getvalue())

    def test_generation_failure_never_writes_files(self):
        stderr = io.StringIO()
        with (
            patch("svg2icons.cli.read_svg", return_value=SVG),
            patch("svg2icons.cli.generate_icons", side_effect=ValueError("invalid SVG")),
            patch("svg2icons.cli.write_icons") as write,
            redirect_stderr(stderr),
        ):
            with self.assertRaises(SystemExit) as error:
                main(["icon.svg"])
        self.assertEqual(error.exception.code, 1)
        self.assertEqual(stderr.getvalue(), "svg2icons: error: invalid SVG\n")
        write.assert_not_called()

    def test_filesystem_errors_are_reported_without_tracebacks(self):
        stderr = io.StringIO()
        with (
            patch("svg2icons.cli.read_svg", side_effect=PermissionError("denied")),
            redirect_stderr(stderr),
        ):
            with self.assertRaises(SystemExit) as error:
                main(["icon.svg"])
        self.assertEqual(error.exception.code, 1)
        self.assertEqual(stderr.getvalue(), "svg2icons: error: denied\n")


if __name__ == "__main__":
    unittest.main()
