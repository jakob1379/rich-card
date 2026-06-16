from __future__ import annotations

from pathlib import Path
from unittest import mock

from rich_card.cli import app

from tests.cli_helpers import RichCardsCliTestCase


class RichCardsCliInputsTest(RichCardsCliTestCase):
    def test_stdin_writes_svg(self) -> None:
        result = self.runner.invoke(
            app,
            [
                "--lexer",
                "python",
                "--theme",
                "monokai-extended",
                "--radius",
                "30",
                "--output",
                str(self.output),
            ],
            input="print('hello')\n",
        )

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual(result.stdout, f"{self.output}\n")
        svg = self.output.read_text(encoding="utf-8")
        self.assertIn("<svg", svg)
        self.assertIn("print", svg)
        self.assertIn("card-bg", svg)

    def test_stdin_defaults_to_auto_width(self) -> None:
        result = self.runner.invoke(
            app,
            ["--output", str(self.output)],
            input="ok\n",
        )

        self.assertEqual(result.exit_code, 0, result.output)
        svg = self.output.read_text(encoding="utf-8")
        width = self.svg_width(self.output)
        self.assertLess(width, 520)
        self.assertNotIn('width="1080"', svg)
        self.assertIn(f'viewBox="0 0 {width} ', svg)

    def test_stdin_expands_tabs_to_two_spaces_by_default(self) -> None:
        result = self.runner.invoke(
            app,
            ["--lexer", "text", "--output", str(self.output)],
            input="\tfoo\n",
        )

        self.assertEqual(result.exit_code, 0, result.output)
        svg = self.output.read_text(encoding="utf-8")
        self.assertIn("foo", svg)

    def test_auto_width_tracks_longest_code_line(self) -> None:
        short_output = Path(self.tmp.name) / "short.svg"
        long_output = Path(self.tmp.name) / "long.svg"

        short_result = self.runner.invoke(
            app,
            ["--output", str(short_output)],
            input="short\n",
        )
        long_result = self.runner.invoke(
            app,
            ["--output", str(long_output)],
            input="this is a much longer line of code\n",
        )

        self.assertEqual(short_result.exit_code, 0, short_result.output)
        self.assertEqual(long_result.exit_code, 0, long_result.output)
        self.assertGreater(self.svg_width(long_output), self.svg_width(short_output))

    def test_svg_preserves_source_spacing(self) -> None:
        result = self.runner.invoke(
            app,
            ["--lexer", "python", "--output", str(self.output)],
            input="def f():\n    return 1\n",
        )

        self.assertEqual(result.exit_code, 0, result.output)
        svg = self.output.read_text(encoding="utf-8")
        self.assertIn("def", svg)
        self.assertIn("return", svg)

    def test_bash_operator_spacing_does_not_emit_isolated_space_span(self) -> None:
        result = self.runner.invoke(
            app,
            ["--lexer", "bash", "--output", str(self.output)],
            input="❯ uv init --package this-sparks-joy && cd this-sparks-joy\n",
        )

        self.assertEqual(result.exit_code, 0, result.output)
        svg = self.output.read_text(encoding="utf-8")
        self.assertIn("uv", svg)
        self.assertIn("cd", svg)

    def test_shell_comments_do_not_render_italic_spacing(self) -> None:
        result = self.runner.invoke(
            app,
            ["--lexer", "bash", "--output", str(self.output)],
            input="# inside the folder\n# And from the get go\n",
        )

        self.assertEqual(result.exit_code, 0, result.output)
        svg = self.output.read_text(encoding="utf-8")
        self.assertIn("# inside the folder", svg)
        self.assertIn("# And from the get go", svg)

    def test_line_numbers_are_rendered_when_enabled(self) -> None:
        result = self.runner.invoke(
            app,
            ["--lexer", "python", "--line-numbers", "--output", str(self.output)],
            input="a = 1\nb = 2\n",
        )

        self.assertEqual(result.exit_code, 0, result.output)
        svg = self.output.read_text(encoding="utf-8")
        self.assertIn("a", svg)
        self.assertIn("b", svg)

    def test_svg_renders_emoji_with_font_fallbacks(self) -> None:
        result = self.runner.invoke(
            app,
            ["--title", "Release 🚀", "--output", str(self.output)],
            input="print('🚀✨')  # shipped ✅\n",
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
            ["--lexer", "python", "--output", str(self.output)],
            input="value = '❤️'\n",
        )

        self.assertEqual(result.exit_code, 0, result.output)
        svg = self.output.read_text(encoding="utf-8")
        self.assertIn("❤️", svg)

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

    def test_stdin_crlf_ansi_renders_visible_text(self) -> None:
        result = self.runner.invoke(
            app,
            ["--output", str(self.output)],
            input="Ruff\r\n\x1b[32mUsage:\x1b[0m ruff\r\n",
        )

        self.assertEqual(result.exit_code, 0, result.output)
        svg = self.output.read_text(encoding="utf-8")
        self.assertIn("Ruff", svg)
        self.assertIn("Usage:", svg)
        self.assertNotIn("\r", svg)

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

    def test_content_option_is_removed(self) -> None:
        result = self.runner.invoke(
            app,
            ["--content", "print('hello')", "--output", str(self.output)],
        )

        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("No such option", result.output)
        self.assertIn("--content", result.output)

    def test_exec_renders_command_output_and_default_title(self) -> None:
        with mock.patch(
            "rich_card.runtime._read_command",
            return_value="\x1b[32mUsage:\x1b[0m ruff\n",
        ):
            result = self.runner.invoke(
                app,
                ["--exec", "ruff --help", "--output", str(self.output)],
            )

        self.assertEqual(result.exit_code, 0, result.output)
        svg = self.output.read_text(encoding="utf-8")
        self.assertIn("Usage:", svg)
        self.assertIn("ruff --help", svg)

    def test_exec_rejects_explicit_lexer(self) -> None:
        result = self.runner.invoke(
            app,
            [
                "--exec",
                "ruff --help",
                "--lexer",
                "python",
                "--output",
                str(self.output),
            ],
        )

        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("--exec cannot be used with --lexer", result.output)

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
