from __future__ import annotations

import unittest
from unittest import mock

from rich_card.renderer_options import BUILTIN_ANSI_PALETTE, RendererDefaults
from rich_card.terminal_palette import renderer_with_terminal_palette


class TerminalPaletteTest(unittest.TestCase):
    def test_renderer_with_terminal_palette_applies_detected_colors(self) -> None:
        detected = {index: f"#{index:02x}{index:02x}{index:02x}" for index in range(16)}

        with mock.patch(
            "rich_card.terminal_palette.query_terminal_palette",
            return_value=(detected, "#eeeeee", "#1d1f21"),
        ):
            renderer = renderer_with_terminal_palette(RendererDefaults())

        self.assertEqual(renderer.default_text, "#eeeeee")
        self.assertEqual(renderer.card_fill, "#1d1f21")
        self.assertEqual(renderer.terminal_palette, "config")
        self.assertEqual(renderer.ansi_palette[1], "#010101")

    def test_renderer_with_terminal_palette_falls_back_to_configured_palette(
        self,
    ) -> None:
        with mock.patch(
            "rich_card.terminal_palette.query_terminal_palette",
            return_value=({}, None, None),
        ):
            renderer = renderer_with_terminal_palette(RendererDefaults())

        self.assertEqual(renderer.default_text, RendererDefaults().default_text)
        self.assertEqual(renderer.card_fill, RendererDefaults().card_fill)
        self.assertEqual(renderer.ansi_palette, BUILTIN_ANSI_PALETTE)


if __name__ == "__main__":
    unittest.main()
