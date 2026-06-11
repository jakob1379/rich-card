from __future__ import annotations

import base64
from dataclasses import dataclass
import math
import re
import struct

from defusedxml import ElementTree
from defusedxml.common import DefusedXmlException

from .errors import InvalidRendererOptionError, UnsupportedImageError


@dataclass(frozen=True)
class ImageContent:
    data_uri: str
    width: float
    height: float

    def __post_init__(self) -> None:
        if not math.isfinite(self.width) or not math.isfinite(self.height):
            raise UnsupportedImageError("Image dimensions must be finite.")
        if self.width <= 0 or self.height <= 0:
            raise UnsupportedImageError("Image dimensions must be positive.")
        _validate_data_uri(self.data_uri)


def _validate_data_uri(data_uri: str) -> None:
    """Validate that data_uri is a safe data: URI for SVG embedding."""
    if not data_uri.startswith("data:"):
        raise InvalidRendererOptionError(
            "data_uri must start with 'data:' for safe SVG embedding."
        )

    # Enforce strict data URI format: data:<mediatype>;base64,<data>
    # The pattern allows safe characters in mediatype and base64 data only
    # Explicitly rejects quotes, angle brackets, and control characters
    safe_data_uri_pattern = re.compile(
        r"^data:[a-zA-Z0-9!#$%&*+\-./^_`{|}~]+;base64,[A-Za-z0-9+/]+=*$"
    )

    if not safe_data_uri_pattern.match(data_uri):
        raise InvalidRendererOptionError(
            "data_uri contains invalid characters or format. "
            "Must match pattern: data:<mediatype>;base64,<base64-data>"
        )


JPEG_STANDALONE_MARKERS = frozenset({0x01, *range(0xD0, 0xD8)})
JPEG_TERMINAL_MARKERS = frozenset({0xD9, 0xDA})
JPEG_START_OF_FRAME_MARKERS = frozenset(
    {
        0xC0,
        0xC1,
        0xC2,
        0xC3,
        0xC5,
        0xC6,
        0xC7,
        0xC9,
        0xCA,
        0xCB,
        0xCD,
        0xCE,
        0xCF,
    }
)


def load_image_content(image: bytes, file_name: str) -> ImageContent:
    """Load image bytes into embeddable SVG content or raise UnsupportedImageError."""
    mime_type, width, height = image_metadata(image, file_name)
    encoded = base64.b64encode(image).decode("ascii")
    return ImageContent(f"data:{mime_type};base64,{encoded}", width, height)


def image_metadata(image: bytes, file_name: str) -> tuple[str, float, float]:
    """Return image MIME type and dimensions or raise UnsupportedImageError."""
    lowered = file_name.lower()
    if lowered.endswith(".png"):
        return "image/png", *_png_dimensions(image)
    if lowered.endswith((".jpg", ".jpeg")):
        return "image/jpeg", *_jpeg_dimensions(image)
    if lowered.endswith(".svg"):
        return "image/svg+xml", *_svg_dimensions(image)
    raise UnsupportedImageError("Unsupported image format. Use PNG, JPEG, or SVG.")


def _png_dimensions(image: bytes) -> tuple[float, float]:
    if len(image) < 24 or image[:8] != b"\x89PNG\r\n\x1a\n" or image[12:16] != b"IHDR":
        raise UnsupportedImageError("Invalid PNG image.")
    width, height = struct.unpack(">II", image[16:24])
    if width <= 0 or height <= 0:
        raise UnsupportedImageError("PNG image dimensions must be positive.")
    return float(width), float(height)


def _jpeg_dimensions(image: bytes) -> tuple[float, float]:
    if len(image) < 4 or image[:2] != b"\xff\xd8":
        raise UnsupportedImageError("Invalid JPEG image.")

    index = 2
    while index < len(image):
        marker, index = _next_jpeg_marker(image, index)
        if marker is None or marker in JPEG_TERMINAL_MARKERS:
            break
        if marker in JPEG_STANDALONE_MARKERS:
            continue

        segment_length = _jpeg_segment_length(image, index)
        if segment_length is None:
            break
        if marker in JPEG_START_OF_FRAME_MARKERS:
            return _jpeg_segment_dimensions(image, index, segment_length)
        index += segment_length
    raise UnsupportedImageError("Could not determine JPEG image dimensions.")


def _next_jpeg_marker(image: bytes, index: int) -> tuple[int | None, int]:
    while index < len(image) and image[index] == 0xFF:
        index += 1
    if index >= len(image):
        return None, index
    return image[index], index + 1


def _jpeg_segment_length(image: bytes, index: int) -> int | None:
    if index + 2 > len(image):
        return None
    segment_length = struct.unpack(">H", image[index : index + 2])[0]
    if segment_length < 2 or index + segment_length > len(image):
        return None
    return segment_length


def _jpeg_segment_dimensions(
    image: bytes, index: int, segment_length: int
) -> tuple[float, float]:
    if segment_length < 7:
        raise UnsupportedImageError("Could not determine JPEG image dimensions.")
    height, width = struct.unpack(">HH", image[index + 3 : index + 7])
    if width <= 0 or height <= 0:
        raise UnsupportedImageError("JPEG image dimensions must be positive.")
    return float(width), float(height)


def _svg_dimensions(image: bytes) -> tuple[float, float]:
    try:
        root = ElementTree.fromstring(image)
    except (ElementTree.ParseError, DefusedXmlException) as exc:
        raise UnsupportedImageError("Invalid SVG image.") from exc

    if root.tag != "svg" and not root.tag.endswith("}svg"):
        raise UnsupportedImageError("Invalid SVG root element.")

    width = _svg_length(root.get("width", ""))
    height = _svg_length(root.get("height", ""))
    if width is not None and height is not None:
        return width, height

    dimensions = _svg_view_box_dimensions(root.get("viewBox"))
    if dimensions is not None:
        return dimensions

    raise UnsupportedImageError(
        "Could not determine SVG image dimensions. Add width/height or viewBox."
    )


def _svg_view_box_dimensions(view_box: str | None) -> tuple[float, float] | None:
    if not view_box:
        return None
    try:
        values = [
            float(value) for value in re.split(r"[\s,]+", view_box.strip()) if value
        ]
    except ValueError as exc:
        raise UnsupportedImageError(
            "Could not determine SVG image dimensions. Add width/height or viewBox."
        ) from exc
    if len(values) != 4:
        return None
    width, height = values[2], values[3]
    if not math.isfinite(width) or not math.isfinite(height):
        raise UnsupportedImageError("SVG image dimensions must be finite.")
    return (width, height) if width > 0 and height > 0 else None


def _svg_length(value: str) -> float | None:
    match = re.fullmatch(r"\s*([0-9]+(?:\.[0-9]+)?)(?:px)?\s*", value)
    if not match:
        return None
    length = float(match.group(1))
    return length if length > 0 else None
