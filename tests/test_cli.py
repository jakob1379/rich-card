from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from typer.testing import CliRunner

from rich_card.cli import BackgroundPreset, app
from rich_card.svg import BACKGROUND_PRESETS, Fragment, _wrap_fragments

PNG_IMAGE = (
    b"\x89PNG\r\n\x1a\n"
    b"\x00\x00\x00\rIHDR"
    b"\x00\x00\x00\x02"
    b"\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00"
    b"\xf4x\xd4\xfa"
    b"\x00\x00\x00\x00IEND\xaeB`\x82"
)
JPEG_IMAGE = (
    b"\xff\xd8"
    b"\xff\xc0\x00\x11\x08"
    b"\x00\x03"
    b"\x00\x02"
    b"\x03\x01\x11\x00\x02\x11\x00\x03\x11\x00"
    b"\xff\xd9"
)
SVG_IMAGE = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 4 2"><rect width="4" height="2"/></svg>'


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
                "--radius",
                "30",
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

    def test_bash_operator_spacing_does_not_emit_isolated_space_span(self) -> None:
        result = self.runner.invoke(
            app,
            [
                "--content",
                "❯ uv init --package this-sparks-joy && cd this-sparks-joy",
                "--lexer",
                "bash",
                "--output",
                str(self.output),
            ],
        )

        self.assertEqual(result.exit_code, 0, result.output)
        svg = self.output.read_text(encoding="utf-8")
        self.assertIn("&amp;&amp; </tspan>", svg)
        self.assertNotIn("&amp;&amp;</tspan><tspan fill=\"#f8f8f2\"> </tspan>", svg)

    def test_shell_comments_do_not_render_italic_spacing(self) -> None:
        result = self.runner.invoke(
            app,
            [
                "--content",
                "# inside the folder\n# And from the get go",
                "--lexer",
                "bash",
                "--output",
                str(self.output),
            ],
        )

        self.assertEqual(result.exit_code, 0, result.output)
        svg = self.output.read_text(encoding="utf-8")
        self.assertIn('<tspan fill="#75715e"># inside the folder</tspan>', svg)
        self.assertIn('<tspan fill="#75715e"># And from the get go</tspan>', svg)
        self.assertNotIn('font-style="italic"># inside', svg)

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

    def test_stdin_preserves_ansi_color_when_no_lexer_is_set(self) -> None:
        result = self.runner.invoke(
            app,
            ["--output", str(self.output)],
            input="\x1b[31mred\x1b[0m plain\n\x1b[1;38;2;1;2;3mtruecolor\x1b[0m\n",
        )

        self.assertEqual(result.exit_code, 0, result.output)
        svg = self.output.read_text(encoding="utf-8")
        self.assertIn('<tspan fill="#800000">red</tspan>', svg)
        self.assertIn('<tspan fill="#f0f2f5"> plain</tspan>', svg)
        self.assertIn('<tspan fill="#010203" font-weight="700">truecolor</tspan>', svg)
        self.assertNotIn("\x1b", svg)

    def test_stdin_renders_eza_icons_with_nerd_font_stack(self) -> None:
        result = self.runner.invoke(
            app,
            ["--output", str(self.output)],
            input="\x1b[34m󰣞 \x1b[1msrc\x1b[0m\n\x1b[33m \x1b[1mcli.py\x1b[0m\n",
        )

        self.assertEqual(result.exit_code, 0, result.output)
        svg = self.output.read_text(encoding="utf-8")
        self.assertIn(
            '<tspan fill="#000080" font-family="\'Symbols Nerd Font Mono\', \'Symbols Nerd Font\'',
            svg,
        )
        self.assertIn(">󰣞</tspan>", svg)
        self.assertIn("></tspan>", svg)
        self.assertIn("src", svg)
        self.assertIn("cli.py", svg)
        self.assertNotIn("\x1b", svg)

    def test_explicit_lexer_strips_ansi_sequences_from_stdin(self) -> None:
        result = self.runner.invoke(
            app,
            ["--lexer", "text", "--output", str(self.output)],
            input="\x1b[31mred\x1b[0m plain\n",
        )

        self.assertEqual(result.exit_code, 0, result.output)
        svg = self.output.read_text(encoding="utf-8")
        self.assertIn("red plain", svg)
        self.assertNotIn("\x1b", svg)
        self.assertNotIn("[31m", svg)

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

    def test_image_png_writes_image_card(self) -> None:
        image = Path(self.tmp.name) / "sample.png"
        image.write_bytes(PNG_IMAGE)

        result = self.runner.invoke(
            app,
            [
                "--image",
                str(image),
                "--title",
                "Preview",
                "--caption",
                "PNG sample",
                "--lexer",
                "not-a-lexer",
                "--theme",
                "not-a-theme",
                "--output",
                str(self.output),
            ],
        )

        self.assertEqual(result.exit_code, 0, result.output)
        svg = self.output.read_text(encoding="utf-8")
        self.assertIn("<image", svg)
        self.assertIn('href="data:image/png;base64,', svg)
        self.assertIn('preserveAspectRatio="xMidYMid meet"', svg)
        self.assertIn(">Preview</tspan></text>", svg)
        self.assertIn("PNG sample", svg)
        self.assertNotIn("xml:space=\"preserve\"", svg)

    def test_image_jpeg_writes_image_card(self) -> None:
        image = Path(self.tmp.name) / "sample.jpg"
        image.write_bytes(JPEG_IMAGE)

        result = self.runner.invoke(
            app,
            [
                "--image",
                str(image),
                "--output",
                str(self.output),
            ],
        )

        self.assertEqual(result.exit_code, 0, result.output)
        svg = self.output.read_text(encoding="utf-8")
        self.assertIn('href="data:image/jpeg;base64,', svg)
        self.assertIn(">sample.jpg</tspan></text>", svg)

    def test_image_svg_writes_image_card(self) -> None:
        image = Path(self.tmp.name) / "sample.svg"
        image.write_bytes(SVG_IMAGE)

        result = self.runner.invoke(
            app,
            [
                "--image",
                str(image),
                "--output",
                str(self.output),
            ],
        )

        self.assertEqual(result.exit_code, 0, result.output)
        svg = self.output.read_text(encoding="utf-8")
        self.assertIn('href="data:image/svg+xml;base64,', svg)
        self.assertIn('width="4.0"', svg)
        self.assertIn('height="2.0"', svg)

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
