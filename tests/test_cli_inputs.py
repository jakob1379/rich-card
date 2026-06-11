from __future__ import annotations

from pathlib import Path

from rich_card.cli import app

from tests.cli_helpers import RichCardsCliTestCase


class RichCardsCliInputsTest(RichCardsCliTestCase):
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

    def test_content_defaults_to_auto_width(self) -> None:
        result = self.runner.invoke(
            app,
            [
                "--content",
                "ok",
                "--output",
                str(self.output),
            ],
        )

        self.assertEqual(result.exit_code, 0, result.output)
        svg = self.output.read_text(encoding="utf-8")
        width = self.svg_width(self.output)
        self.assertLess(width, 520)
        self.assertNotIn('width="1080"', svg)
        self.assertIn(f'viewBox="0 0 {width} ', svg)

    def test_content_expands_tabs_to_two_spaces_by_default(self) -> None:
        result = self.runner.invoke(
            app,
            [
                "--content",
                "\tfoo",
                "--lexer",
                "text",
                "--output",
                str(self.output),
            ],
        )

        self.assertEqual(result.exit_code, 0, result.output)
        svg = self.output.read_text(encoding="utf-8")
        self.assertIn("foo", svg)

    def test_auto_width_tracks_longest_code_line(self) -> None:
        short_output = Path(self.tmp.name) / "short.svg"
        long_output = Path(self.tmp.name) / "long.svg"

        short_result = self.runner.invoke(
            app,
            [
                "--content",
                "short",
                "--output",
                str(short_output),
            ],
        )
        long_result = self.runner.invoke(
            app,
            [
                "--content",
                "this is a much longer line of code",
                "--output",
                str(long_output),
            ],
        )

        self.assertEqual(short_result.exit_code, 0, short_result.output)
        self.assertEqual(long_result.exit_code, 0, long_result.output)
        self.assertGreater(self.svg_width(long_output), self.svg_width(short_output))

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
        self.assertIn("def", svg)
        self.assertIn("return", svg)

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
        self.assertIn("uv", svg)
        self.assertIn("cd", svg)

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
        self.assertIn("# inside the folder", svg)
        self.assertIn("# And from the get go", svg)

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
        self.assertIn("a", svg)
        self.assertIn("b", svg)

    def test_svg_renders_emoji_with_font_fallbacks(self) -> None:
        result = self.runner.invoke(
            app,
            [
                "--content",
                "print('🚀✨')  # shipped ✅",
                "--title",
                "Release 🚀",
                "--output",
                str(self.output),
            ],
        )

        self.assertEqual(result.exit_code, 0, result.output)
        svg = self.output.read_text(encoding="utf-8")
        self.assertIn("🚀✨", svg)
        self.assertIn("Release ", svg)
        self.assertIn("✅", svg)

    def test_stdin_defaults_to_plain_text_and_preserves_heart_emoji(self) -> None:
        result = self.runner.invoke(
            app,
            ["--output", str(self.output)],
            input='echo "I print beautifully ❤️"\nI print beautifully ❤️\n',
        )

        self.assertEqual(result.exit_code, 0, result.output)
        svg = self.output.read_text(encoding="utf-8")
        self.assertIn("I print beautifully ", svg)
        self.assertIn("❤️", svg)

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
        self.assertIn("red", svg)
        self.assertIn("plain", svg)
        self.assertIn("truecolor", svg)
        self.assertNotIn("\x1b", svg)

    def test_stdin_renders_eza_icons_with_nerd_font_stack(self) -> None:
        result = self.runner.invoke(
            app,
            ["--output", str(self.output)],
            input="\x1b[34m󰣞 \x1b[1msrc\x1b[0m\n\x1b[33m \x1b[1mcli.py\x1b[0m\n",
        )

        self.assertEqual(result.exit_code, 0, result.output)
        svg = self.output.read_text(encoding="utf-8")
        self.assertIn("󰣞", svg)
        self.assertIn("", svg)
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

    def test_source_file_supplies_content_title_and_lexer(self) -> None:
        source = Path(self.tmp.name) / "pyproject.toml"
        source.write_text('[tool.rich-card]\ntheme = "monokai"\n', encoding="utf-8")

        result = self.runner.invoke(
            app,
            [
                str(source),
                "--output",
                str(self.output),
            ],
        )

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual(result.stdout, f"{self.output}\n")
        svg = self.output.read_text(encoding="utf-8")
        self.assertIn("tool.rich-card", svg)
        self.assertIn("theme", svg)
        self.assertIn("monokai", svg)
        self.assertIn("pyproject.toml", svg)
