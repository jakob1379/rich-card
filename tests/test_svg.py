from __future__ import annotations

import unittest
from typing import Any, cast

from rich_card.errors import (
    InvalidRendererOptionError,
    UnknownLexerError,
    UnknownStyleError,
)
from rich_card.images import ImageContent
from rich_card.options import BACKGROUND_OFF
from rich_card.renderer_options import RendererDefaults
from rich_card.svg import (
    CHROME_FONT_STACK,
    CodeCardOptions,
    EMOJI_FONT_STACK,
    ImageCardOptions,
    render_code_card_svg,
    render_image_card_svg,
)


class RichCardSvgTest(unittest.TestCase):
    def test_render_code_card_svg_happy_path(self) -> None:
        svg = render_code_card_svg(
            "print('hello')\n",
            CodeCardOptions(title="hello.py", lexer="python", line_numbers=True),
        )

        self.assertTrue(svg.startswith("<svg "))
        self.assertIn('aria-label="Rendered code card"', svg)
        self.assertIn("hello.py", svg)
        self.assertIn("print", svg)
        self.assertIn("</svg>", svg)

    def test_render_image_card_svg_happy_path(self) -> None:
        image = ImageContent("data:image/svg+xml;base64,image", 12, 8)
        logo = ImageContent("data:image/svg+xml;base64,logo", 10, 10)

        svg = render_image_card_svg(
            image,
            ImageCardOptions(title="diagram.svg", logo=logo),
        )

        self.assertTrue(svg.startswith("<svg "))
        self.assertIn('aria-label="Rendered image card"', svg)
        self.assertIn("diagram.svg", svg)
        self.assertIn("data:image/svg+xml;base64,", svg)
        self.assertIn('preserveAspectRatio="xMidYMid meet"', svg)
        self.assertIn('width="12.0"', svg)
        self.assertIn('height="8.0"', svg)

    def test_render_code_card_svg_preserves_zero_inner_padding(self) -> None:
        svg = render_code_card_svg(
            "x",
            CodeCardOptions(lexer="text", inner_padding_x=0, inner_padding_y=0),
        )

        self.assertIn('<text x="72" y="137"', svg)

    def test_render_code_card_svg_background_off_uses_transparent_tight_canvas(
        self,
    ) -> None:
        svg = render_code_card_svg(
            "x",
            CodeCardOptions(lexer="text", background=BACKGROUND_OFF),
        )

        self.assertIn('<rect x="0" y="0"', svg)
        self.assertNotIn('id="card-bg"', svg)
        self.assertNotIn('fill="url(#card-bg)"', svg)
        self.assertNotIn('filter="url(#soft-shadow)"', svg)

    def test_render_code_card_svg_uses_configured_renderer_colors_and_fonts(
        self,
    ) -> None:
        svg = render_code_card_svg(
            "x",
            CodeCardOptions(
                lexer="text",
                line_numbers=True,
                renderer=RendererDefaults(
                    card_fill="#111111",
                    card_stroke="#222222",
                    muted_text="#abcdef",
                    code_font_stack="Configured Mono, monospace",
                    font_size=17,
                    min_card_width=300,
                ),
            ),
        )

        self.assertIn('fill="#111111" stroke="#222222"', svg)
        self.assertIn('font-family="Configured Mono, monospace"', svg)
        self.assertIn('font-size="17"', svg)
        self.assertIn('<tspan fill="#abcdef">1 │ </tspan>', svg)

    def test_render_code_card_svg_line_number_markup(self) -> None:
        svg = render_code_card_svg(
            "a = 1\nb = 2",
            CodeCardOptions(lexer="python", line_numbers=True),
        )

        self.assertIn(">1 │ </tspan>", svg)
        self.assertIn(">2 │ </tspan>", svg)

    def test_render_code_card_svg_shell_spacing_and_comment_spans(self) -> None:
        operator_svg = render_code_card_svg(
            "❯ uv init --package this-sparks-joy && cd this-sparks-joy",
            CodeCardOptions(lexer="bash"),
        )
        comment_svg = render_code_card_svg(
            "# inside the folder\n# And from the get go",
            CodeCardOptions(lexer="bash"),
        )

        self.assertIn("&amp;&amp; </tspan>", operator_svg)
        self.assertNotIn(
            '&amp;&amp;</tspan><tspan fill="#f8f8f2"> </tspan>', operator_svg
        )
        self.assertIn('<tspan fill="#75715e"># inside the folder</tspan>', comment_svg)
        self.assertIn(
            '<tspan fill="#75715e"># And from the get go</tspan>', comment_svg
        )
        self.assertNotIn('font-style="italic"># inside', comment_svg)

    def test_render_code_card_svg_nix_multiline_string_token(self) -> None:
        svg = render_code_card_svg(
            "shellHook = ''\n  export UV_PYTHON_PREFERENCE=\"managed\"\n  '';",
            CodeCardOptions(file_name="flake.nix"),
        )

        self.assertIn("shellHook", svg)
        self.assertIn("UV_PYTHON_PREFERENCE", svg)
        self.assertIn('fill="#e6db74"', svg)

    def test_render_code_card_svg_emoji_font_fallback_markup(self) -> None:
        svg = render_code_card_svg(
            "print('🚀✨')  # shipped ✅",
            CodeCardOptions(title="Release 🚀"),
        )

        self.assertIn(">🚀</tspan>", svg)
        self.assertIn(">✅</tspan>", svg)
        self.assertIn(f'font-family="{EMOJI_FONT_STACK}"', svg)
        self.assertIn("Noto Color Emoji", svg)
        self.assertIn('fill="#ffd447"', svg)
        self.assertIn('fill="#34c759"', svg)

    def test_render_code_card_svg_ansi_and_nerd_font_span_markup(self) -> None:
        svg = render_code_card_svg(
            "\x1b[31mred\x1b[0m plain\n"
            "\x1b[1;38;2;1;2;3mtruecolor\x1b[0m\n"
            "\x1b[34m󰣞 \x1b[1msrc\x1b[0m\n",
            CodeCardOptions(),
        )

        self.assertIn('<tspan fill="#800000">red</tspan>', svg)
        self.assertIn('<tspan fill="#f0f2f5"> plain</tspan>', svg)
        self.assertIn('<tspan fill="#010203" font-weight="700">truecolor</tspan>', svg)
        self.assertIn(
            "<tspan fill=\"#000080\" font-family=\"'Symbols Nerd Font Mono', 'Symbols Nerd Font'",
            svg,
        )
        self.assertIn(">󰣞</tspan>", svg)
        self.assertNotIn("\x1b", svg)

    def test_render_image_card_svg_href_and_preserve_aspect_ratio_markup(self) -> None:
        image = ImageContent("data:image/png;base64,image", 12, 8)

        svg = render_image_card_svg(image, ImageCardOptions(title="Preview"))

        self.assertIn('href="data:image/png;base64,image"', svg)
        self.assertIn('preserveAspectRatio="xMidYMid meet"', svg)

    def test_render_image_card_svg_title_uses_plain_ui_font_for_digits(self) -> None:
        file_name = "Screenshot from 2026-06-09 15-26-17.png"
        image = ImageContent("data:image/png;base64,image", 12, 8)

        svg = render_image_card_svg(image, ImageCardOptions(title=file_name))

        self.assertIn(f'font-family="{CHROME_FONT_STACK}"', svg)
        self.assertIn(file_name, svg)
        self.assertNotIn("Apple Color Emoji", svg)

    def test_render_code_card_svg_rejects_unknown_background(self) -> None:
        with self.assertRaises(InvalidRendererOptionError):
            render_code_card_svg(
                "x = 1", CodeCardOptions(background=cast(Any, "bogus"))
            )

    def test_render_code_card_svg_rejects_unknown_lexer(self) -> None:
        with self.assertRaises(UnknownLexerError):
            render_code_card_svg("x = 1", CodeCardOptions(lexer="bogus-lexer"))

    def test_render_code_card_svg_rejects_unknown_style(self) -> None:
        with self.assertRaises(UnknownStyleError):
            render_code_card_svg("x = 1", CodeCardOptions(theme="bogus-style"))

    def test_render_code_card_svg_rejects_invalid_logo_placement(self) -> None:
        logo = ImageContent("data:image/svg+xml;base64,logo", 10, 10)

        with self.assertRaises(InvalidRendererOptionError):
            render_code_card_svg(
                "x = 1", CodeCardOptions(logo=logo, logo_placement=cast(Any, "corner"))
            )

    def test_render_code_card_svg_rejects_invalid_public_geometry(self) -> None:
        with self.assertRaisesRegex(
            InvalidRendererOptionError, "width must be greater than twice the padding"
        ):
            render_code_card_svg("x = 1", CodeCardOptions(width=100, padding=60))

    def test_render_code_card_svg_rejects_invalid_renderer_defaults(self) -> None:
        with self.assertRaisesRegex(
            InvalidRendererOptionError, "renderer.char_width must be finite"
        ):
            render_code_card_svg(
                "x = 1",
                CodeCardOptions(renderer=RendererDefaults(char_width=float("nan"))),
            )

    def test_code_card_options_reject_invalid_code_options(self) -> None:
        cases = (
            ({"title": 1}, "title must be a string or None"),
            ({"lexer": 1}, "lexer must be a string or None"),
            ({"theme": None}, "theme must be a string"),
            ({"file_name": 1}, "file_name must be a string or None"),
            ({"tab_size": 0}, "tab_size must be in range 1..12"),
            ({"tab_size": 13}, "tab_size must be in range 1..12"),
            ({"tab_size": True}, "tab_size must be an integer"),
            ({"line_numbers": "yes"}, "line_numbers must be a boolean"),
            ({"word_wrap": 1}, "word_wrap must be a boolean"),
        )
        for kwargs, expected in cases:
            with self.subTest(kwargs=kwargs):
                with self.assertRaisesRegex(InvalidRendererOptionError, expected):
                    CodeCardOptions(**cast(Any, kwargs))

    def test_card_options_reject_invalid_renderer_object(self) -> None:
        with self.assertRaisesRegex(
            InvalidRendererOptionError, "renderer must be a RendererDefaults"
        ):
            CodeCardOptions(renderer=cast(Any, object()))


if __name__ == "__main__":
    unittest.main()
