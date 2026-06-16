from __future__ import annotations

from pathlib import Path

from rich_card.cli import app

from tests.cli_helpers import JPEG_IMAGE, PNG_IMAGE, SVG_IMAGE, RichCardsCliTestCase


class RichCardsCliImagesTest(RichCardsCliTestCase):
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
                "--output",
                str(self.output),
            ],
        )

        self.assertEqual(result.exit_code, 0, result.output)
        svg = self.output.read_text(encoding="utf-8")
        self.assertIn("<image", svg)
        self.assertIn("data:image/png;base64,", svg)
        self.assertIn("Preview", svg)

    def test_image_defaults_to_auto_width(self) -> None:
        image = Path(self.tmp.name) / "sample.png"
        image.write_bytes(PNG_IMAGE)

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
        self.assertLess(self.svg_width(self.output), 520)

    def test_image_default_title_uses_plain_ui_font_for_digits(self) -> None:
        file_name = "Screenshot from 2026-06-09 15-26-17.png"
        image = Path(self.tmp.name) / file_name
        image.write_bytes(PNG_IMAGE)

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
        self.assertIn(file_name, svg)

    def test_logo_renders_in_title_bar(self) -> None:
        logo = Path(self.tmp.name) / "logo.png"
        logo.write_bytes(PNG_IMAGE)

        result = self.runner.invoke(
            app,
            [
                "--title",
                "Demo",
                "--logo",
                str(logo),
                "--width",
                "640",
                "--output",
                str(self.output),
            ],
            input="print('hello')\n",
        )

        self.assertEqual(result.exit_code, 0, result.output)
        svg = self.output.read_text(encoding="utf-8")
        self.assertIn("rich-card-logo-bar", svg)
        self.assertIn("data:image/png;base64,", svg)
        self.assertNotIn("rich-card-logo-watermark", svg)

    def test_watermark_reuses_logo_when_no_image_is_provided(self) -> None:
        logo = Path(self.tmp.name) / "logo.png"
        logo.write_bytes(PNG_IMAGE)

        result = self.runner.invoke(
            app,
            [
                "--logo",
                str(logo),
                "--watermark",
                "--width",
                "640",
                "--output",
                str(self.output),
            ],
            input="print('hello')\n",
        )

        self.assertEqual(result.exit_code, 0, result.output)
        svg = self.output.read_text(encoding="utf-8")
        self.assertIn("rich-card-logo-bar", svg)
        self.assertIn("rich-card-logo-watermark", svg)
        self.assertEqual(svg.count("data:image/png;base64,"), 2)

    def test_watermark_renders_without_logo(self) -> None:
        watermark = Path(self.tmp.name) / "watermark.svg"
        watermark.write_bytes(SVG_IMAGE)

        result = self.runner.invoke(
            app,
            [
                "--watermark",
                str(watermark),
                "--width",
                "640",
                "--output",
                str(self.output),
            ],
            input="print('hello')\n",
        )

        self.assertEqual(result.exit_code, 0, result.output)
        svg = self.output.read_text(encoding="utf-8")
        self.assertIn("rich-card-logo-watermark", svg)
        self.assertIn("data:image/svg+xml;base64,", svg)
        self.assertNotIn("rich-card-logo-bar", svg)

    def test_logo_and_watermark_can_use_different_images(self) -> None:
        logo = Path(self.tmp.name) / "logo.png"
        watermark = Path(self.tmp.name) / "watermark.svg"
        logo.write_bytes(PNG_IMAGE)
        watermark.write_bytes(SVG_IMAGE)

        result = self.runner.invoke(
            app,
            [
                "--logo",
                str(logo),
                "--watermark",
                str(watermark),
                "--width",
                "640",
                "--output",
                str(self.output),
            ],
            input="print('hello')\n",
        )

        self.assertEqual(result.exit_code, 0, result.output)
        svg = self.output.read_text(encoding="utf-8")
        self.assertIn("rich-card-logo-bar", svg)
        self.assertIn("rich-card-logo-watermark", svg)
        self.assertIn("data:image/png;base64,", svg)
        self.assertIn("data:image/svg+xml;base64,", svg)

    def test_bare_watermark_does_not_consume_following_option(self) -> None:
        logo = Path(self.tmp.name) / "logo.png"
        logo.write_bytes(PNG_IMAGE)

        result = self.runner.invoke(
            app,
            [
                "--logo",
                str(logo),
                "--watermark",
                "--title",
                "Demo",
                "--width",
                "640",
                "--output",
                str(self.output),
            ],
            input="print('hello')\n",
        )

        self.assertEqual(result.exit_code, 0, result.output)
        svg = self.output.read_text(encoding="utf-8")
        self.assertIn("Demo", svg)
        self.assertIn("rich-card-logo-watermark", svg)

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
        self.assertIn("data:image/jpeg;base64,", svg)
        self.assertIn("sample.jpg", svg)

    def test_image_card_renders_logo(self) -> None:
        image = Path(self.tmp.name) / "sample.png"
        logo = Path(self.tmp.name) / "logo.svg"
        image.write_bytes(PNG_IMAGE)
        logo.write_bytes(SVG_IMAGE)

        result = self.runner.invoke(
            app,
            [
                "--image",
                str(image),
                "--logo",
                str(logo),
                "--watermark",
                "--width",
                "640",
                "--output",
                str(self.output),
            ],
        )

        self.assertEqual(result.exit_code, 0, result.output)
        svg = self.output.read_text(encoding="utf-8")
        self.assertIn("rich-card-logo-bar", svg)
        self.assertIn("rich-card-logo-watermark", svg)

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
        self.assertIn("data:image/svg+xml;base64,", svg)

    def test_image_mode_ignores_piped_stdin(self) -> None:
        image = Path(self.tmp.name) / "sample.png"
        image.write_bytes(PNG_IMAGE)

        result = self.runner.invoke(
            app,
            [
                "--image",
                str(image),
                "--output",
                str(self.output),
            ],
            input="unused text",
        )

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("data:image/png;base64,", self.output.read_text(encoding="utf-8"))
