from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest import mock

from rich_card.options import BackgroundPreset
from rich_card.renderer_options import DEFAULT_THEME, RendererDefaults
from rich_card.runtime import RenderRuntimeError, RenderSettings, render_card


PNG_IMAGE = (
    b"\x89PNG\r\n\x1a\n"
    b"\x00\x00\x00\rIHDR"
    b"\x00\x00\x00\x02"
    b"\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00"
    b"\xf4x\xd4\xfa"
    b"\x00\x00\x00\x00IEND\xaeB`\x82"
)


class RenderRuntimeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.output = self.root / "card.svg"

    def settings(
        self,
        *,
        logo: Path | None = None,
        watermark: Path | None = None,
        watermark_uses_logo: bool = False,
    ) -> RenderSettings:
        return RenderSettings(
            output=self.output,
            lexer="python",
            theme=DEFAULT_THEME,
            title=None,
            logo=logo,
            watermark=watermark,
            watermark_uses_logo=watermark_uses_logo,
            background=BackgroundPreset.aurora,
            width=None,
            height=None,
            padding=72,
            inner_padding_x=34,
            inner_padding_y=30,
            radius=30,
            line_numbers=False,
            word_wrap=False,
            tab_size=2,
            renderer=RendererDefaults(),
        )

    def test_render_card_writes_source_file(self) -> None:
        source = self.root / "source.py"
        source.write_text("print('hello')\n", encoding="utf-8")

        output = render_card(source, None, None, self.settings())

        self.assertEqual(output, self.output)
        svg = self.output.read_text(encoding="utf-8")
        self.assertIn("print", svg)
        self.assertIn("hello", svg)

    def test_render_card_exec_forces_color_environment(self) -> None:
        with mock.patch(
            "rich_card.runtime._capture_command_output", return_value="out"
        ) as capture:
            output = render_card(None, None, "show colors", self.settings())

        self.assertEqual(output, self.output)
        args, _kwargs = capture.call_args
        self.assertEqual(args[0], "show colors")
        env = args[1]
        self.assertEqual(env["CLICOLOR_FORCE"], "1")
        self.assertEqual(env["FORCE_COLOR"], "1")
        self.assertEqual(env["COLORTERM"], "truecolor")
        self.assertEqual(env["BAT_PAGER"], "cat")
        self.assertNotIn("NO_COLOR", env)
        svg = self.output.read_text(encoding="utf-8")
        self.assertIn("❯", svg)
        self.assertIn("show colors", svg)
        self.assertIn("out", svg)

    def test_render_card_exec_captures_tty_color_output(self) -> None:
        command = (
            "python -c 'import sys; "
            'print("\\033[31mtty\\033[0m" if sys.stdout.isatty() else "plain")'
            "'"
        )

        render_card(None, None, command, self.settings())

        svg = self.output.read_text(encoding="utf-8")
        self.assertIn("tty", svg)
        self.assertIn("#cc6666", svg)
        self.assertNotIn(">plain<", svg)

    def test_render_card_writes_image_content(self) -> None:
        image = self.root / "sample.png"
        image.write_bytes(PNG_IMAGE)

        render_card(None, image, None, self.settings())

        svg = self.output.read_text(encoding="utf-8")
        self.assertIn('href="data:image/png;base64,', svg)
        self.assertIn("sample.png", svg)

    def test_render_card_rejects_image_with_code_input(self) -> None:
        image = self.root / "sample.png"
        source = self.root / "source.py"

        with self.assertRaisesRegex(RenderRuntimeError, "cannot be combined"):
            render_card(source, image, None, self.settings())
        with self.assertRaisesRegex(RenderRuntimeError, "cannot be combined"):
            render_card(None, image, "printf hello", self.settings())

    def test_render_card_loads_logo(self) -> None:
        logo = self.root / "logo.png"
        logo.write_bytes(PNG_IMAGE)

        source = self.root / "source.py"
        source.write_text("print('hello')\n", encoding="utf-8")

        render_card(source, None, None, self.settings(logo=logo))

        self.assertIn("rich-card-logo-bar", self.output.read_text(encoding="utf-8"))

    def test_render_card_reuses_logo_as_watermark(self) -> None:
        logo = self.root / "logo.png"
        logo.write_bytes(PNG_IMAGE)

        source = self.root / "source.py"
        source.write_text("print('hello')\n", encoding="utf-8")

        render_card(
            source, None, None, self.settings(logo=logo, watermark_uses_logo=True)
        )

        svg = self.output.read_text(encoding="utf-8")
        self.assertIn("rich-card-logo-bar", svg)
        self.assertIn("rich-card-logo-watermark", svg)
        self.assertEqual(svg.count("data:image/png;base64,"), 2)

    def test_render_card_loads_distinct_watermark(self) -> None:
        watermark = self.root / "watermark.png"
        watermark.write_bytes(PNG_IMAGE)

        source = self.root / "source.py"
        source.write_text("print('hello')\n", encoding="utf-8")

        render_card(source, None, None, self.settings(watermark=watermark))

        svg = self.output.read_text(encoding="utf-8")
        self.assertNotIn("rich-card-logo-bar", svg)
        self.assertIn("rich-card-logo-watermark", svg)

    def test_render_card_rejects_missing_source_content_and_stdin(self) -> None:
        stdin = mock.Mock()
        stdin.isatty.return_value = True
        with mock.patch("rich_card.runtime.sys.stdin", stdin):
            with self.assertRaisesRegex(RenderRuntimeError, "Provide a SOURCE path"):
                render_card(None, None, None, self.settings())

    def test_render_card_reports_output_write_failure(self) -> None:
        blocked_parent = self.root / "blocked"
        blocked_parent.write_text("not a directory", encoding="utf-8")
        settings = replace(self.settings(), output=blocked_parent / "card.svg")

        with self.assertRaisesRegex(RenderRuntimeError, "Could not write SVG file"):
            render_card(None, None, "printf hello", settings)


if __name__ == "__main__":
    unittest.main()
