from __future__ import annotations

from html import escape
import unittest

from rich_card.errors import UnknownLexerError
from rich_card.renderer_options import RendererDefaults
from rich_card.svg import CodeCardOptions
from rich_card.svg_fragments import Fragment, _wrap_fragments
from rich_card.svg_markup import _code_lines, _inline_tspans
from rich_card.svg_syntax import _highlight_lines


class RichCardSvgTextTest(unittest.TestCase):
    def highlight(self, code: str, options: CodeCardOptions) -> list[list[Fragment]]:
        return _highlight_lines(
            code,
            renderer=options.renderer,
            lexer_name=options.lexer,
            file_name=options.file_name,
            tab_size=options.tab_size,
            theme=options.theme,
        )

    def test_word_wrap_keeps_compound_emoji_intact(self) -> None:
        lines = _wrap_fragments([Fragment("aaaaaaaaaaaa👩‍💻b", "#fff")], width=13)

        self.assertEqual(
            "".join(fragment.text for fragment in lines[0]), "aaaaaaaaaaaa"
        )
        self.assertEqual("".join(fragment.text for fragment in lines[1]), "👩‍💻b")

    def test_code_lines_renders_styled_text_and_escapes_xml(self) -> None:
        svg = _code_lines(
            [[Fragment("if x < 3", "#f92672", bold=True)]],
            10,
            20,
            RendererDefaults(),
        )

        self.assertIn('<text x="10" y="20"', svg)
        self.assertIn(
            '<tspan fill="#f92672" font-weight="700">if x &lt; 3</tspan>', svg
        )

    def test_code_lines_escapes_font_family_attribute_values(self) -> None:
        svg = _code_lines(
            [[Fragment("x", "#f92672")]],
            10,
            20,
            RendererDefaults(code_font_stack='Mono" data-x="1'),
        )

        self.assertNotIn('data-x="1"', svg)
        self.assertIn('font-family="Mono&quot; data-x=&quot;1"', svg)

    def test_inline_tspans_uses_emoji_font_fallback(self) -> None:
        renderer = RendererDefaults()
        markup = _inline_tspans("Ship 🚀", "#ffffff", renderer)

        self.assertIn('<tspan fill="#ffffff">Ship </tspan>', markup)
        self.assertIn(
            f'font-family="{escape(renderer.emoji_font_stack, quote=True)}"', markup
        )
        self.assertIn('style="font-variant-emoji: emoji;"', markup)

    def test_highlight_lines_uses_configured_lexer(self) -> None:
        lines = self.highlight("print('hello')", CodeCardOptions(lexer="python"))

        text = "".join(fragment.text for line in lines for fragment in line)

        self.assertEqual("print('hello')", text)

    def test_highlight_lines_decodes_ansi_without_lexer(self) -> None:
        lines = self.highlight("\x1b[31mred\x1b[0m", CodeCardOptions())

        self.assertEqual([Fragment("red", "#cc6666")], lines[0])

    def test_highlight_lines_maps_standard_ansi_through_configured_palette(
        self,
    ) -> None:
        palette = tuple(f"#{index:02x}{index:02x}{index:02x}" for index in range(16))
        renderer = RendererDefaults(terminal_palette="config", ansi_palette=palette)

        lines = self.highlight(
            "\x1b[31mred\x1b[0m",
            CodeCardOptions(renderer=renderer),
        )

        self.assertEqual([Fragment("red", "#010101")], lines[0])

    def test_highlight_lines_keeps_truecolor_ansi_exact(self) -> None:
        palette = tuple("#111111" for _index in range(16))
        renderer = RendererDefaults(terminal_palette="config", ansi_palette=palette)

        lines = self.highlight(
            "\x1b[38;2;1;2;3mtruecolor\x1b[0m",
            CodeCardOptions(renderer=renderer),
        )

        self.assertEqual([Fragment("truecolor", "#010203")], lines[0])

    def test_highlight_lines_strips_non_display_terminal_controls(self) -> None:
        lines = self.highlight(
            "\x1b]10;?\x07\x1b]11;?\x07\x1b[c\x1b[31mred\x1b[0m",
            CodeCardOptions(),
        )

        self.assertEqual([Fragment("red", "#cc6666")], lines[0])

    def test_highlight_lines_normalizes_terminal_crlf(self) -> None:
        lines = self.highlight("Ruff\r\n\x1b[32mUsage:\x1b[0m\r\n", CodeCardOptions())

        text = "\n".join("".join(fragment.text for fragment in line) for line in lines)

        self.assertEqual(text, "Ruff\nUsage:")

    def test_highlight_lines_rejects_unknown_lexer(self) -> None:
        with self.assertRaises(UnknownLexerError):
            self.highlight("x", CodeCardOptions(lexer="bogus-lexer"))


if __name__ == "__main__":
    unittest.main()
