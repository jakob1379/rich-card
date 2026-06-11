from __future__ import annotations

import base64
import unittest

from rich_card.errors import UnsupportedImageError
from rich_card.images import ImageContent, image_metadata, load_image_content


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


class ImageContentTest(unittest.TestCase):
    def test_load_image_content_embeds_png_with_dimensions(self) -> None:
        image = load_image_content(PNG_IMAGE, "logo.png")

        self.assertEqual(image.width, 2.0)
        self.assertEqual(image.height, 1.0)
        self.assertEqual(
            image.data_uri,
            f"data:image/png;base64,{base64.b64encode(PNG_IMAGE).decode('ascii')}",
        )

    def test_load_image_content_embeds_jpeg_with_dimensions(self) -> None:
        image = load_image_content(JPEG_IMAGE, "logo.jpeg")

        self.assertEqual(image.width, 2.0)
        self.assertEqual(image.height, 3.0)
        self.assertEqual(
            image.data_uri,
            f"data:image/jpeg;base64,{base64.b64encode(JPEG_IMAGE).decode('ascii')}",
        )

    def test_load_image_content_embeds_svg_with_dimensions(self) -> None:
        image = load_image_content(SVG_IMAGE, "logo.svg")

        self.assertEqual(image.width, 4.0)
        self.assertEqual(image.height, 2.0)
        self.assertEqual(
            image.data_uri,
            f"data:image/svg+xml;base64,{base64.b64encode(SVG_IMAGE).decode('ascii')}",
        )

    def test_image_metadata_returns_png_metadata(self) -> None:
        self.assertEqual(image_metadata(PNG_IMAGE, "LOGO.PNG"), ("image/png", 2.0, 1.0))

    def test_image_metadata_returns_jpeg_metadata(self) -> None:
        self.assertEqual(
            image_metadata(JPEG_IMAGE, "logo.jpg"), ("image/jpeg", 2.0, 3.0)
        )

    def test_image_metadata_returns_svg_metadata_from_dimensions(self) -> None:
        svg = b'<svg xmlns="http://www.w3.org/2000/svg" width="12px" height="6"></svg>'

        self.assertEqual(image_metadata(svg, "logo.svg"), ("image/svg+xml", 12.0, 6.0))

    def test_unsupported_extension_raises(self) -> None:
        with self.assertRaises(UnsupportedImageError):
            image_metadata(PNG_IMAGE, "logo.gif")

    def test_image_content_rejects_non_positive_dimensions(self) -> None:
        with self.assertRaises(UnsupportedImageError):
            ImageContent("data:image/png;base64,x", 0, 1)

    def test_image_content_rejects_non_finite_dimensions(self) -> None:
        for width, height in ((float("nan"), 1), (1, float("inf"))):
            with self.subTest(width=width, height=height):
                with self.assertRaisesRegex(
                    UnsupportedImageError, "Image dimensions must be finite"
                ):
                    ImageContent("data:image/png;base64,x", width, height)

    def test_svg_metadata_rejects_non_finite_viewbox_dimensions(self) -> None:
        svg = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 inf 2"></svg>'

        with self.assertRaisesRegex(
            UnsupportedImageError, "SVG image dimensions must be finite"
        ):
            image_metadata(svg, "logo.svg")

    def test_svg_metadata_rejects_non_svg_root(self) -> None:
        svg = b'<html width="12" height="6"></html>'

        with self.assertRaisesRegex(UnsupportedImageError, "Invalid SVG root element"):
            image_metadata(svg, "logo.svg")

    def test_invalid_png_raises(self) -> None:
        with self.assertRaises(UnsupportedImageError):
            image_metadata(b"not a png", "logo.png")

    def test_invalid_jpeg_raises(self) -> None:
        with self.assertRaises(UnsupportedImageError):
            image_metadata(b"\xff\xd8\xff\xd9", "logo.jpg")

    def test_invalid_svg_raises(self) -> None:
        with self.assertRaises(UnsupportedImageError):
            image_metadata(b"<svg>", "logo.svg")


if __name__ == "__main__":
    unittest.main()
