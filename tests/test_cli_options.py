from __future__ import annotations

from rich_card.cli import app
from rich_card.options import BACKGROUND_CHOICES, BACKGROUND_PRESETS, BackgroundPreset

from tests.cli_helpers import RichCardsCliTestCase


class RichCardsCliOptionsTest(RichCardsCliTestCase):
    def test_render_has_no_stderr_output(self) -> None:
        result = self.runner.invoke(
            app,
            [
                "--output",
                str(self.output),
            ],
            input="print('hello')\n",
        )

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual(result.stdout, f"{self.output}\n")
        self.assertEqual(result.stderr, "")

    def test_short_title_option_renders_title(self) -> None:
        result = self.runner.invoke(
            app,
            [
                "-t",
                "demo.py",
                "--output",
                str(self.output),
            ],
            input="print('hello')\n",
        )

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("demo.py", self.output.read_text(encoding="utf-8"))

    def test_common_short_options_render_card(self) -> None:
        result = self.runner.invoke(
            app,
            [
                "-s",
                "monokai-extended",
                "-b",
                "electric-twilight",
                "-w",
                "640",
                "-p",
                "48",
                "-r",
                "44",
                "-n",
                "-W",
                "-T",
                "2",
                "-o",
                str(self.output),
            ],
            input="print('hello')\n",
        )

        self.assertEqual(result.exit_code, 0, result.output)
        svg = self.output.read_text(encoding="utf-8")
        self.assertIn('width="640"', svg)
        self.assertIn("print", svg)

    def test_padding_options_adjust_background_and_terminal_padding(self) -> None:
        result = self.runner.invoke(
            app,
            [
                "--width",
                "640",
                "--padding",
                "40",
                "--inner-padding",
                "20",
                "--output",
                str(self.output),
            ],
            input="print('hello')\n",
        )

        self.assertEqual(result.exit_code, 0, result.output)
        svg = self.output.read_text(encoding="utf-8")
        self.assertIn("print", svg)

    def test_list_themes_lists_custom_and_pygments_styles(self) -> None:
        result = self.runner.invoke(app, ["--list-themes"])

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("monokai-extended", result.output)
        self.assertIn("monokai", result.output)

    def test_list_backgrounds_lists_background_options(self) -> None:
        result = self.runner.invoke(app, ["--list-backgrounds"])

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual(result.output.splitlines(), list(BACKGROUND_CHOICES))

    def test_cli_background_choices_match_renderer_presets(self) -> None:
        self.assertEqual(
            {preset.value for preset in BackgroundPreset},
            set(BACKGROUND_PRESETS),
        )

    def test_new_background_gradient_preset_renders(self) -> None:
        result = self.runner.invoke(
            app,
            [
                "--background",
                "electric-twilight",
                "--output",
                str(self.output),
            ],
            input="print('hello')\n",
        )

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("print", self.output.read_text(encoding="utf-8"))

    def test_additional_popular_background_preset_renders(self) -> None:
        result = self.runner.invoke(
            app,
            [
                "--background",
                "winter-neva",
                "--output",
                str(self.output),
            ],
            input="print('hello')\n",
        )

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("print", self.output.read_text(encoding="utf-8"))

    def test_background_off_renders_tight_transparent_canvas(self) -> None:
        result = self.runner.invoke(
            app,
            [
                "--background",
                "off",
                "--output",
                str(self.output),
            ],
            input="print('hello')\n",
        )

        self.assertEqual(result.exit_code, 0, result.output)
        svg = self.output.read_text(encoding="utf-8")
        self.assertIn('<rect x="0" y="0"', svg)
        self.assertNotIn('id="card-bg"', svg)
        self.assertNotIn('fill="url(#card-bg)"', svg)
        self.assertNotIn('filter="url(#soft-shadow)"', svg)
