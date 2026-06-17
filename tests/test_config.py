from __future__ import annotations

import json
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from rich_card.config import ConfigError, load_config, renderer_defaults
from rich_card.renderer_options import RendererDefaults


class LoadConfigTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "config.json"

    def write_config(self, config: object) -> Path:
        self.path.write_text(json.dumps(config), encoding="utf-8")
        return self.path

    def assert_config_error(self, config: object, expected: str) -> None:
        path = self.write_config(config)
        with self.assertRaisesRegex(ConfigError, expected):
            load_config(path)

    def test_rejects_invalid_root_type(self) -> None:
        self.assert_config_error([], "config root must be a JSON object")

    def test_rejects_invalid_output_type(self) -> None:
        self.assert_config_error({"output": 7}, "output must be a string")

    def test_rejects_invalid_renderer_section_shape(self) -> None:
        self.assert_config_error({"renderer": []}, "renderer must be a JSON object")

    def test_rejects_unknown_renderer_key(self) -> None:
        self.assert_config_error(
            {"renderer": {"drop_shadow": True}},
            "unknown renderer key: drop_shadow",
        )

    def test_rejects_renderer_string_type_failure(self) -> None:
        self.assert_config_error(
            {"renderer": {"card_fill": 123}},
            "renderer.card_fill must be a string",
        )

    def test_rejects_renderer_color_attribute_injection(self) -> None:
        self.assert_config_error(
            {"renderer": {"card_fill": '#111111" data-x="1'}},
            r"renderer\.card_fill must be a #rrggbb hex color",
        )

    def test_renderer_color_config_is_normalized_to_lowercase(self) -> None:
        path = self.write_config({"renderer": {"card_fill": "#ABCDEF"}})

        config = load_config(path)
        defaults = renderer_defaults(config.renderer)

        self.assertEqual(defaults.card_fill, "#abcdef")

    def test_rejects_invalid_terminal_palette_mode(self) -> None:
        self.assert_config_error(
            {"renderer": {"terminal_palette": "magic"}},
            "renderer.terminal_palette must be one of",
        )

    def test_rejects_invalid_ansi_palette_shape(self) -> None:
        self.assert_config_error(
            {"renderer": {"ansi_palette": ["#000000"]}},
            "renderer.ansi_palette must be a list of 16 hex colors",
        )

    def test_rejects_invalid_ansi_palette_color(self) -> None:
        self.assert_config_error(
            {"renderer": {"ansi_palette": ["#000000"] * 15 + ["red"]}},
            r"renderer\.ansi_palette\[15\] must be a #rrggbb hex color",
        )

    def test_accepts_ansi_palette(self) -> None:
        palette = tuple(f"#{index:02x}{index:02x}{index:02x}" for index in range(16))
        path = self.write_config(
            {"renderer": {"terminal_palette": "config", "ansi_palette": list(palette)}}
        )

        config = load_config(path)
        defaults = renderer_defaults(config.renderer)

        self.assertEqual(defaults.terminal_palette, "config")
        self.assertEqual(defaults.ansi_palette, palette)

    def test_rejects_renderer_integer_type_failure(self) -> None:
        self.assert_config_error(
            {"renderer": {"line_height": 21.5}},
            "renderer.line_height must be an integer",
        )

    def test_rejects_renderer_number_type_failure(self) -> None:
        self.assert_config_error(
            {"renderer": {"char_width": "9.4"}},
            "renderer.char_width must be a number",
        )

    def test_rejects_renderer_minimum_range_failure(self) -> None:
        self.assert_config_error(
            {"renderer": {"char_width": 0}},
            "renderer.char_width must be in range >= 0.1",
        )

    def test_rejects_renderer_maximum_range_failure(self) -> None:
        self.assert_config_error(
            {"renderer": {"logo_watermark_opacity": 1.1}},
            "renderer.logo_watermark_opacity must be in range 0.0..1.0",
        )

    def test_rejects_non_finite_renderer_numbers(self) -> None:
        cases = (
            ('{"renderer": {"char_width": NaN}}', "renderer.char_width must be finite"),
            (
                '{"renderer": {"logo_watermark_opacity": Infinity}}',
                "renderer.logo_watermark_opacity must be finite",
            ),
        )
        for raw_json, expected in cases:
            with self.subTest(expected=expected):
                self.path.write_text(raw_json, encoding="utf-8")
                with self.assertRaisesRegex(ConfigError, expected):
                    load_config(self.path)

    def test_valid_renderer_defaults_fill_missing_values(self) -> None:
        path = self.write_config({"renderer": {"font_size": 18, "char_width": 10}})

        config = load_config(path)
        defaults = renderer_defaults(config.renderer)

        self.assertEqual(defaults.font_size, 18)
        self.assertEqual(defaults.char_width, 10.0)
        self.assertEqual(defaults.card_fill, RendererDefaults().card_fill)

    def test_missing_config_returns_empty_config(self) -> None:
        missing = Path(self.tmp.name) / "missing.json"

        config = load_config(missing)

        self.assertEqual(config.path, missing)

    def test_read_failure_reports_path(self) -> None:
        with mock.patch.object(Path, "read_text", side_effect=OSError("blocked")):
            with self.assertRaisesRegex(
                ConfigError,
                rf"{re.escape(str(self.path))}: could not read config: blocked",
            ):
                load_config(self.path)


if __name__ == "__main__":
    unittest.main()
