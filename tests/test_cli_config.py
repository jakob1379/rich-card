from __future__ import annotations

from pathlib import Path

from rich_card.cli import app
from rich_card.config import default_config_path

from tests.cli_helpers import PNG_IMAGE, SVG_IMAGE, RichCardsCliTestCase


class RichCardsCliConfigTest(RichCardsCliTestCase):
    def test_blank_xdg_config_home_falls_back_to_home_config(self) -> None:
        self.assertEqual(
            default_config_path({"XDG_CONFIG_HOME": "  "}),
            Path.home() / ".config" / "rich-card" / "config.json",
        )

    def test_relative_xdg_config_home_falls_back_to_home_config(self) -> None:
        self.assertEqual(
            default_config_path({"XDG_CONFIG_HOME": "relative/config"}),
            Path.home() / ".config" / "rich-card" / "config.json",
        )

    def test_xdg_config_supplies_cli_defaults(self) -> None:
        configured_output = Path(self.tmp.name) / "configured.svg"
        self.write_config(
            {
                "output": str(configured_output),
                "card": {
                    "background": "ember",
                    "width": 640,
                    "height": 320,
                    "inner_padding": 16,
                    "radius": 40,
                    "line_numbers": True,
                    "tab_size": 4,
                    "title": "Configured",
                },
            }
        )

        result = self.runner.invoke(
            app,
            [
                "--lexer",
                "text",
            ],
            input="\tfoo\n",
        )

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual(result.stdout, f"{configured_output}\n")
        svg = configured_output.read_text(encoding="utf-8")
        self.assertIn('width="640"', svg)
        self.assertIn('height="320"', svg)
        self.assertIn("foo", svg)
        self.assertIn("Configured", svg)

    def test_cli_options_override_xdg_config_defaults(self) -> None:
        configured_output = Path(self.tmp.name) / "configured.svg"
        self.write_config(
            {
                "output": str(configured_output),
                "card": {
                    "background": "ember",
                    "width": 640,
                    "height": 320,
                    "inner_padding_x": 60,
                    "inner_padding_y": 60,
                    "radius": 40,
                    "line_numbers": True,
                },
            }
        )

        result = self.runner.invoke(
            app,
            [
                "--background",
                "electric-twilight",
                "--width",
                "800",
                "--height",
                "360",
                "--inner-padding",
                "20",
                "--radius",
                "12",
                "--no-line-numbers",
                "--output",
                str(self.output),
            ],
            input="print('hello')\n",
        )

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual(result.stdout, f"{self.output}\n")
        self.assertFalse(configured_output.exists())
        svg = self.output.read_text(encoding="utf-8")
        self.assertIn('width="800"', svg)
        self.assertIn('height="360"', svg)
        self.assertIn("print", svg)

    def test_xdg_config_preserves_zero_inner_padding(self) -> None:
        self.write_config({"card": {"inner_padding_x": 0, "inner_padding_y": 0}})

        result = self.runner.invoke(
            app,
            [
                "--output",
                str(self.output),
            ],
            input="x\n",
        )

        self.assertEqual(result.exit_code, 0, result.output)
        svg = self.output.read_text(encoding="utf-8")
        self.assertIn("x", svg)

    def test_xdg_config_supplies_background_off(self) -> None:
        self.write_config({"card": {"background": "off"}})

        result = self.runner.invoke(
            app,
            [
                "--output",
                str(self.output),
            ],
            input="x\n",
        )

        self.assertEqual(result.exit_code, 0, result.output)
        svg = self.output.read_text(encoding="utf-8")
        self.assertIn('<rect x="0" y="0"', svg)
        self.assertNotIn('fill="url(#card-bg)"', svg)

    def test_xdg_config_supplies_hidden_renderer_defaults(self) -> None:
        self.write_config(
            {
                "card": {"line_numbers": True},
                "renderer": {
                    "card_fill": "#111111",
                    "card_stroke": "#222222",
                    "muted_text": "#abcdef",
                    "code_font_stack": "Configured Mono, monospace",
                    "font_size": 17,
                    "min_card_width": 300,
                },
            }
        )

        result = self.runner.invoke(
            app,
            [
                "--lexer",
                "text",
                "--output",
                str(self.output),
            ],
            input="x\n",
        )

        self.assertEqual(result.exit_code, 0, result.output)
        svg = self.output.read_text(encoding="utf-8")
        self.assertIn("x", svg)
        self.assertIn("#111111", svg)
        self.assertIn("#222222", svg)
        self.assertIn("#abcdef", svg)
        self.assertIn("Configured Mono", svg)
        self.assertIn('font-size="17"', svg)
        self.assertIn('width="300"', svg)

    def test_xdg_config_rejects_invalid_renderer_color(self) -> None:
        self.write_config({"renderer": {"card_fill": '#111111" data-x="1'}})

        result = self.runner.invoke(
            app,
            [
                "--output",
                str(self.output),
            ],
            input="x\n",
        )

        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("renderer.card_fill must be a #rrggbb hex color", result.output)
        self.assertFalse(self.output.exists())

    def test_xdg_config_supplies_logo_defaults_and_renderer_tuning(self) -> None:
        logo = Path(self.tmp.name) / "logo.png"
        logo.write_bytes(PNG_IMAGE)
        self.write_config(
            {
                "card": {
                    "logo": str(logo),
                    "watermark": True,
                },
                "renderer": {
                    "logo_watermark_opacity": 0.5,
                    "logo_watermark_width_ratio": 0.75,
                },
            }
        )

        result = self.runner.invoke(
            app,
            [
                "--width",
                "640",
                "--output",
                str(self.output),
            ],
            input="print('hello')\n",
        )

        self.assertEqual(result.exit_code, 0, result.output)
        svg = self.output.read_text(encoding="utf-8")
        self.assertIn("rich-card-logo-watermark", svg)
        self.assertIn("rich-card-logo-bar", svg)
        self.assertEqual(svg.count("data:image/png;base64,"), 2)
        self.assertIn('opacity="0.5"', svg)

    def test_xdg_config_supplies_distinct_watermark_image(self) -> None:
        watermark = Path(self.tmp.name) / "watermark.png"
        watermark.write_bytes(PNG_IMAGE)
        self.write_config(
            {
                "card": {
                    "watermark": str(watermark),
                },
            }
        )

        result = self.runner.invoke(
            app,
            [
                "--width",
                "640",
                "--output",
                str(self.output),
            ],
            input="print('hello')\n",
        )

        self.assertEqual(result.exit_code, 0, result.output)
        svg = self.output.read_text(encoding="utf-8")
        self.assertIn("rich-card-logo-watermark", svg)
        self.assertNotIn("rich-card-logo-bar", svg)

    def test_cli_watermark_overrides_xdg_config_default(self) -> None:
        logo = Path(self.tmp.name) / "logo.png"
        watermark = Path(self.tmp.name) / "watermark.svg"
        logo.write_bytes(PNG_IMAGE)
        watermark.write_bytes(SVG_IMAGE)
        self.write_config(
            {
                "card": {
                    "logo": str(logo),
                    "watermark": True,
                },
            }
        )

        result = self.runner.invoke(
            app,
            [
                "--watermark",
                str(watermark),
                "--width",
                "640",
                "--output",
                str(self.output),
            ],
            input="print('hello')\n",
        )

        self.assertEqual(result.exit_code, 0, result.output)
        svg = self.output.read_text(encoding="utf-8")
        self.assertIn("rich-card-logo-bar", svg)
        self.assertIn("rich-card-logo-watermark", svg)
        self.assertIn("data:image/svg+xml;base64,", svg)
