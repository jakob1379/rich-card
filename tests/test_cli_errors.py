from __future__ import annotations

from pathlib import Path

from rich_card.cli import app
from rich_card.config import ConfigError, load_config

from tests.cli_helpers import PNG_IMAGE, RichCardsCliTestCase


class RichCardsCliErrorsTest(RichCardsCliTestCase):
    def test_xdg_config_rejects_invalid_json(self) -> None:
        path = self.config_home / "rich-card" / "config.json"
        path.parent.mkdir(parents=True)
        path.write_text("{", encoding="utf-8")

        result = self.runner.invoke(
            app,
            [
                "--content",
                "x",
                "--output",
                str(self.output),
            ],
        )

        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("invalid", result.output)
        self.assertIn("JSON", result.output)
        self.assertIn(str(path), result.output)

    def test_xdg_config_rejects_invalid_utf8(self) -> None:
        path = self.config_home / "rich-card" / "config.json"
        path.parent.mkdir(parents=True)
        path.write_bytes(b"\xff")

        result = self.runner.invoke(
            app,
            [
                "--content",
                "x",
                "--output",
                str(self.output),
            ],
        )

        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("could not", result.output)
        self.assertIn("read config", result.output)
        self.assertIn(str(path), result.output)

    def test_xdg_config_rejects_unknown_keys(self) -> None:
        self.write_config({"card": {"caption": "not supported"}})

        result = self.runner.invoke(
            app,
            [
                "--content",
                "x",
                "--output",
                str(self.output),
            ],
        )

        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("unknown", result.output)
        self.assertIn("card key: caption", result.output)

    def test_xdg_config_rejects_out_of_range_values(self) -> None:
        self.write_config({"card": {"width": 10}})

        result = self.runner.invoke(
            app,
            [
                "--content",
                "x",
                "--output",
                str(self.output),
            ],
        )

        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("card.width", result.output)
        self.assertIn("must be in range 520..2400", result.output)

    def test_xdg_config_rejects_empty_card_strings(self) -> None:
        self.write_config({"card": {"lexer": "", "title": ""}})

        result = self.runner.invoke(
            app,
            [
                "--content",
                "x",
                "--output",
                str(self.output),
            ],
        )

        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("card.lexer", result.output)
        self.assertIn("must be a non-empty string", result.output)

    def test_xdg_config_rejects_non_string_card_strings(self) -> None:
        self.write_config({"card": {"lexer": 12}})

        result = self.runner.invoke(
            app,
            [
                "--content",
                "x",
                "--output",
                str(self.output),
            ],
        )

        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("card.lexer", result.output)
        self.assertIn("must be a string", result.output)

    def test_xdg_config_rejects_unknown_background(self) -> None:
        self.write_config({"card": {"background": "purple-haze"}})

        result = self.runner.invoke(
            app,
            [
                "--content",
                "x",
                "--output",
                str(self.output),
            ],
        )

        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("card.background", result.output)
        self.assertIn("must be one of", result.output)

    def test_load_config_rejects_unknown_background_before_rendering(self) -> None:
        path = self.write_config({"card": {"background": "purple-haze"}})

        with self.assertRaisesRegex(ConfigError, "card.background"):
            load_config(path)

    def test_output_write_failure_reports_cli_error(self) -> None:
        blocked_parent = Path(self.tmp.name) / "blocked"
        blocked_parent.write_text("not a directory", encoding="utf-8")
        output = blocked_parent / "card.svg"

        result = self.runner.invoke(
            app,
            [
                "--content",
                "x",
                "--output",
                str(output),
            ],
        )

        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("Could not write SVG file", result.output)
        self.assertIn(str(output), result.output)

    def test_caption_option_is_not_supported(self) -> None:
        result = self.runner.invoke(
            app,
            [
                "--content",
                "print('hello')",
                "--caption",
                "removed",
                "--output",
                str(self.output),
            ],
        )

        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("No such option", result.output)
        self.assertIn("--caption", result.output)

    def test_padding_alias_options_are_not_supported(self) -> None:
        for option in ("--background-padding", "--terminal-padding"):
            with self.subTest(option=option):
                result = self.runner.invoke(
                    app,
                    [
                        "--content",
                        "print('hello')",
                        option,
                        "20",
                        "--output",
                        str(self.output),
                    ],
                )

                self.assertNotEqual(result.exit_code, 0)
                self.assertIn("No such option", result.output)
                self.assertIn(option, result.output)

    def test_image_rejects_code_only_options(self) -> None:
        image = Path(self.tmp.name) / "sample.png"
        image.write_bytes(PNG_IMAGE)

        result = self.runner.invoke(
            app,
            [
                "--image",
                str(image),
                "--lexer",
                "python",
                "--output",
                str(self.output),
            ],
        )

        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("--image cannot be used with --lexer", result.output)

    def test_xdg_config_rejects_unknown_logo_placement(self) -> None:
        self.write_config({"card": {"logo_placement": "corner"}})

        result = self.runner.invoke(
            app,
            [
                "--content",
                "print('hello')",
                "--output",
                str(self.output),
            ],
        )

        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("card.logo_placement", result.output)
        self.assertIn("must be one of", result.output)

    def test_invalid_image_data_reports_cli_error(self) -> None:
        image = Path(self.tmp.name) / "sample.png"
        image.write_bytes(b"not a png")

        result = self.runner.invoke(
            app,
            [
                "--image",
                str(image),
                "--output",
                str(self.output),
            ],
        )

        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("Invalid PNG image", result.output)

    def test_nonfinite_svg_image_dimensions_report_cli_error(self) -> None:
        image = Path(self.tmp.name) / "sample.svg"
        image.write_bytes(
            b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 inf 2"></svg>'
        )

        result = self.runner.invoke(
            app,
            [
                "--image",
                str(image),
                "--output",
                str(self.output),
            ],
        )

        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("Could not load image file", result.output)
        self.assertIn("svg", result.output.lower())
        self.assertIn("image dimensions must be finite", result.output.lower())

    def test_invalid_logo_data_reports_cli_error(self) -> None:
        logo = Path(self.tmp.name) / "logo.png"
        logo.write_bytes(b"not a png")

        result = self.runner.invoke(
            app,
            [
                "--content",
                "print('hello')",
                "--logo",
                str(logo),
                "--output",
                str(self.output),
            ],
        )

        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("Invalid PNG image", result.output)

    def test_invalid_image_data_reports_before_invalid_logo_data(self) -> None:
        image = Path(self.tmp.name) / "sample.png"
        logo = Path(self.tmp.name) / "logo.svg"
        image.write_bytes(b"not a png")
        logo.write_bytes(b"<svg>")

        result = self.runner.invoke(
            app,
            [
                "--image",
                str(image),
                "--logo",
                str(logo),
                "--output",
                str(self.output),
            ],
        )

        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("Could not load image file", result.output)
        self.assertIn("Invalid PNG image", result.output)
        self.assertNotIn("Could not load logo image", result.output)
        self.assertNotIn("Invalid SVG image", result.output)

    def test_image_rejects_text_source(self) -> None:
        image = Path(self.tmp.name) / "sample.png"
        source = Path(self.tmp.name) / "sample.py"
        image.write_bytes(PNG_IMAGE)
        source.write_text("print('hello')\n", encoding="utf-8")

        result = self.runner.invoke(
            app,
            [
                str(source),
                "--image",
                str(image),
                "--output",
                str(self.output),
            ],
        )

        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("--image cannot be used with a SOURCE path", result.output)

    def test_image_mode_conflict_is_reported_before_logo_loading(self) -> None:
        image = Path(self.tmp.name) / "sample.png"
        logo = Path(self.tmp.name) / "logo.png"
        source = Path(self.tmp.name) / "sample.py"
        image.write_bytes(PNG_IMAGE)
        logo.write_bytes(b"not a png")
        source.write_text("print('hello')\n", encoding="utf-8")

        result = self.runner.invoke(
            app,
            [
                str(source),
                "--image",
                str(image),
                "--logo",
                str(logo),
                "--output",
                str(self.output),
            ],
        )

        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("--image cannot be used with a SOURCE path", result.output)
        self.assertNotIn("Invalid PNG image", result.output)

    def test_source_uses_typer_path_validation(self) -> None:
        result = self.runner.invoke(app, ["missing.py", "--output", str(self.output)])

        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("does not exist", result.output)

    def test_background_rejects_unknown_preset(self) -> None:
        result = self.runner.invoke(
            app,
            [
                "--content",
                "print('hello')",
                "--background",
                "purple-haze",
                "--output",
                str(self.output),
            ],
        )

        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("Unknown background option", result.output)
        self.assertIn("purple-haze", result.output)

    def test_unknown_theme_fails(self) -> None:
        result = self.runner.invoke(
            app,
            [
                "--content",
                "print('hello')",
                "--theme",
                "definitely-not-a-theme",
                "--output",
                str(self.output),
            ],
        )

        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("Unknown Pygments style", result.output)
