from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from typer.testing import CliRunner

from rich_cards.cli import BackgroundPreset, app
from rich_cards.svg import BACKGROUND_PRESETS, Fragment, _wrap_fragments


class RichCardsCliTest(unittest.TestCase):
    def setUp(self) -> None:
        self.runner = CliRunner()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.output = Path(self.tmp.name) / "card.svg"

    def test_content_writes_svg(self) -> None:
        result = self.runner.invoke(
            app,
            [
                "--content",
                "print('hello')",
                "--lexer",
                "python",
                "--theme",
                "monokai-extended",
                "--output",
                str(self.output),
            ],
        )

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual(result.stdout, f"{self.output}\n")
        svg = self.output.read_text(encoding="utf-8")
        self.assertIn("<svg", svg)
        self.assertIn("print", svg)
        self.assertIn("card-bg", svg)
        self.assertIn("#a6e22e", svg)
        self.assertIn('stroke-width="3"', svg)
        self.assertIn('rx="30"', svg)
        self.assertIn('xml:space="preserve"', svg)
        self.assertIn("#48c7df", svg)

    def test_render_has_no_stderr_output(self) -> None:
        result = self.runner.invoke(
            app,
            [
                "--content",
                "print('hello')",
                "--output",
                str(self.output),
            ],
        )

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual(result.stdout, f"{self.output}\n")
        self.assertEqual(result.stderr, "")

    def test_svg_preserves_source_spacing(self) -> None:
        result = self.runner.invoke(
            app,
            [
                "--content",
                "def f():\n    return 1",
                "--lexer",
                "python",
                "--output",
                str(self.output),
            ],
        )

        self.assertEqual(result.exit_code, 0, result.output)
        svg = self.output.read_text(encoding="utf-8")
        self.assertIn(">    </tspan>", svg)
        self.assertNotIn("</tspan>\n", svg)

    def test_line_numbers_are_rendered_when_enabled(self) -> None:
        result = self.runner.invoke(
            app,
            [
                "--content",
                "a = 1\nb = 2",
                "--lexer",
                "python",
                "--line-numbers",
                "--output",
                str(self.output),
            ],
        )

        self.assertEqual(result.exit_code, 0, result.output)
        svg = self.output.read_text(encoding="utf-8")
        self.assertIn(">1 │ </tspan>", svg)
        self.assertIn(">2 │ </tspan>", svg)

    def test_short_title_option_renders_title(self) -> None:
        result = self.runner.invoke(
            app,
            [
                "--content",
                "print('hello')",
                "-t",
                "demo.py",
                "--output",
                str(self.output),
            ],
        )

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn(">demo.py</tspan></text>", self.output.read_text(encoding="utf-8"))

    def test_common_short_options_render_card(self) -> None:
        result = self.runner.invoke(
            app,
            [
                "--content",
                "print('hello')",
                "-s",
                "monokai-extended",
                "-C",
                "sample caption",
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
        )

        self.assertEqual(result.exit_code, 0, result.output)
        svg = self.output.read_text(encoding="utf-8")
        self.assertIn('width="640"', svg)
        self.assertIn('rx="44"', svg)
        self.assertIn(">1 │ </tspan>", svg)
        self.assertIn("sample caption", svg)
        self.assertIn("#0b1026", svg)

    def test_svg_renders_emoji_with_font_fallbacks(self) -> None:
        result = self.runner.invoke(
            app,
            [
                "--content",
                "print('🚀✨')  # shipped ✅",
                "--title",
                "Release 🚀",
                "--caption",
                "Ready ✅",
                "--output",
                str(self.output),
            ],
        )

        self.assertEqual(result.exit_code, 0, result.output)
        svg = self.output.read_text(encoding="utf-8")
        self.assertIn("🚀✨", svg)
        self.assertIn("Release ", svg)
        self.assertIn("Ready ", svg)
        self.assertIn(">🚀</tspan>", svg)
        self.assertIn(">✅</tspan>", svg)
        self.assertIn("Noto Color Emoji", svg)
        self.assertIn('fill="#ffd447"', svg)
        self.assertIn('fill="#34c759"', svg)

    def test_stdin_defaults_to_plain_text_and_preserves_heart_emoji(self) -> None:
        result = self.runner.invoke(
            app,
            ["--output", str(self.output)],
            input='echo "I print beautifully ❤️"\nI print beautifully ❤️\n',
        )

        self.assertEqual(result.exit_code, 0, result.output)
        svg = self.output.read_text(encoding="utf-8")
        self.assertIn("I print beautifully ", svg)
        self.assertIn(">❤️</tspan>", svg)
        self.assertIn('font-family="\'Apple Color Emoji\'', svg)
        self.assertIn('fill-opacity="0"', svg)
        self.assertIn('fill="#ff3b57"', svg)
        self.assertNotIn('fill="#f8f8f2" font-family="\'Apple Color Emoji\'', svg)
        self.assertNotIn("<tspan fill=\"#a6e22e\">print</tspan>", svg)
        self.assertNotIn(">❤</tspan><tspan", svg)

    def test_explicit_python_lexer_preserves_heart_emoji(self) -> None:
        result = self.runner.invoke(
            app,
            [
                "--content",
                "value = '❤️'",
                "--lexer",
                "python",
                "--output",
                str(self.output),
            ],
        )

        self.assertEqual(result.exit_code, 0, result.output)
        svg = self.output.read_text(encoding="utf-8")
        self.assertIn("❤️", svg)
        self.assertNotIn(">❤</tspan><tspan", svg)

    def test_word_wrap_keeps_compound_emoji_intact(self) -> None:
        lines = _wrap_fragments([Fragment("aaaaaaaaaaaa👩‍💻b", "#fff")], width=13)

        self.assertEqual("".join(fragment.text for fragment in lines[0]), "aaaaaaaaaaaa")
        self.assertEqual("".join(fragment.text for fragment in lines[1]), "👩‍💻b")

    def test_stdin_writes_svg(self) -> None:
        result = self.runner.invoke(
            app,
            ["--lexer", "python", "--output", str(self.output)],
            input="value = 42\n",
        )

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("value", self.output.read_text(encoding="utf-8"))

    def test_content_takes_precedence_over_source(self) -> None:
        source = Path(self.tmp.name) / "sample.py"
        source.write_text("from_file = True\n", encoding="utf-8")

        result = self.runner.invoke(
            app,
            [
                str(source),
                "--content",
                "inline_value = True",
                "--output",
                str(self.output),
            ],
        )

        self.assertEqual(result.exit_code, 0, result.output)
        svg = self.output.read_text(encoding="utf-8")
        self.assertIn("inline_value", svg)
        self.assertNotIn("from_file", svg)

    def test_list_themes_lists_custom_and_pygments_styles(self) -> None:
        result = self.runner.invoke(app, ["--list-themes"])

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("monokai-extended", result.output)
        self.assertIn("monokai", result.output)

    def test_source_uses_typer_path_validation(self) -> None:
        result = self.runner.invoke(app, ["missing.py", "--output", str(self.output)])

        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("does not exist", result.output)

    def test_background_uses_typer_choice_validation(self) -> None:
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
        self.assertIn("purple-haze", result.output)

    def test_cli_background_choices_match_renderer_presets(self) -> None:
        self.assertEqual(
            {preset.value for preset in BackgroundPreset},
            set(BACKGROUND_PRESETS),
        )

    def test_new_background_gradient_preset_renders(self) -> None:
        result = self.runner.invoke(
            app,
            [
                "--content",
                "print('hello')",
                "--background",
                "electric-twilight",
                "--output",
                str(self.output),
            ],
        )

        self.assertEqual(result.exit_code, 0, result.output)
        svg = self.output.read_text(encoding="utf-8")
        self.assertIn("#0b1026", svg)
        self.assertIn("#00d4ff", svg)
        self.assertIn("#ff2fb3", svg)

    def test_additional_popular_background_preset_renders(self) -> None:
        result = self.runner.invoke(
            app,
            [
                "--content",
                "print('hello')",
                "--background",
                "winter-neva",
                "--output",
                str(self.output),
            ],
        )

        self.assertEqual(result.exit_code, 0, result.output)
        svg = self.output.read_text(encoding="utf-8")
        self.assertIn("#a1c4fd", svg)
        self.assertIn("#c2e9fb", svg)
        self.assertIn("#eef8ff", svg)

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


if __name__ == "__main__":
    unittest.main()
