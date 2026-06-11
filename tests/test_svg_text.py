from __future__ import annotations

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

    def test_inline_tspans_uses_emoji_font_fallback(self) -> None:
        renderer = RendererDefaults()
        markup = _inline_tspans("Ship 🚀", "#ffffff", renderer)

        self.assertIn('<tspan fill="#ffffff">Ship </tspan>', markup)
        self.assertIn(f'font-family="{renderer.emoji_font_stack}"', markup)
        self.assertIn('style="font-variant-emoji: emoji;"', markup)

    def test_highlight_lines_uses_configured_lexer(self) -> None:
        lines = self.highlight("print('hello')", CodeCardOptions(lexer="python"))

        text = "".join(fragment.text for line in lines for fragment in line)

        self.assertEqual("print('hello')", text)

    def test_highlight_lines_decodes_ansi_without_lexer(self) -> None:
        lines = self.highlight("\x1b[31mred\x1b[0m", CodeCardOptions())

        self.assertEqual([Fragment("red", "#800000")], lines[0])

    def test_highlight_lines_rejects_unknown_lexer(self) -> None:
        with self.assertRaises(UnknownLexerError):
            self.highlight("x", CodeCardOptions(lexer="bogus-lexer"))


if __name__ == "__main__":
    unittest.main()
