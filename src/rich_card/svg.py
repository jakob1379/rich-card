from __future__ import annotations

import base64
from dataclasses import dataclass
from html import escape
import re
import struct
from unicodedata import category
from xml.etree import ElementTree

from pygments import lex
from pygments.lexers import get_lexer_by_name, guess_lexer_for_filename
from pygments.style import Style
from pygments.styles import get_style_by_name
from pygments.token import (
    Comment,
    Error,
    Generic,
    Keyword,
    Literal,
    Name,
    Number,
    Operator,
    Punctuation,
    String,
    Text,
    Token,
)
from pygments.util import ClassNotFound
from rich.ansi import AnsiDecoder
from rich.cells import cell_len, split_graphemes
from rich.console import Console

BACKGROUND_PRESETS: dict[str, tuple[str, str, str]] = {
    "aurora": ("#f7fbff", "#bdefff", "#48c7df"),
    "blue-raspberry": ("#dff9ff", "#00b4db", "#0083b0"),
    "cosmic-lumen": ("#07111f", "#1ba6ff", "#d9fbff"),
    "dusty-grass": ("#f6ffd7", "#d4fc79", "#96e6a1"),
    "ember": ("#f6b05f", "#dc574d", "#231f20"),
    "electric-twilight": ("#0b1026", "#00d4ff", "#ff2fb3"),
    "frozen-dream": ("#fdcbf1", "#e6dee9", "#d9e7ff"),
    "lagoon": ("#35d4b4", "#3574d4", "#1f2440"),
    "megatron": ("#c6ffdd", "#fbd786", "#f7797d"),
    "moss": ("#b9d96d", "#4e9c75", "#17261f"),
    "mono": ("#f2f2ed", "#b9b8b0", "#4f5254"),
    "night-fade": ("#a18cd1", "#fbc2eb", "#ffe7f3"),
    "nordic": ("#2e3440", "#5e81ac", "#88c0d0"),
    "premium-dark": ("#434343", "#171717", "#000000"),
    "prism": ("#c0c0c0", "#d4f1f9", "#fff9d4"),
    "rainy-ashville": ("#fbc2eb", "#a6c1ee", "#d7e8ff"),
    "sublime-light": ("#fc5c7d", "#8c6ff5", "#6a82fb"),
    "sunny-morning": ("#f6d365", "#fda085", "#ff7f8f"),
    "tempting-azure": ("#84fab0", "#8fd3f4", "#9bd7ff"),
    "warm-flame": ("#ff9a9e", "#fad0c4", "#fad0c4"),
    "winter-neva": ("#a1c4fd", "#c2e9fb", "#eef8ff"),
}

CARD_FILL = "#26282b"
CARD_STROKE = "#3b3e43"
MUTED_TEXT = "#8d9199"
DEFAULT_TEXT = "#f0f2f5"
FONT_STACK = (
    "'JetBrains Mono', 'Cascadia Code', 'SFMono-Regular', Menlo, Consolas, "
    "'Apple Color Emoji', 'Segoe UI Emoji', 'Noto Color Emoji', 'Twemoji Mozilla', monospace"
)
EMOJI_FONT_STACK = (
    "'Apple Color Emoji', 'Segoe UI Emoji', 'Noto Color Emoji', 'Twemoji Mozilla', "
    "'JetBrains Mono', 'Cascadia Code', 'SFMono-Regular', Menlo, Consolas, monospace"
)
ICON_FONT_STACK = (
    "'Symbols Nerd Font Mono', 'Symbols Nerd Font', "
    "'JetBrains Mono', 'Cascadia Code', 'SFMono-Regular', Menlo, Consolas, monospace"
)
CHAR_WIDTH = 9.4
LINE_HEIGHT = 21
FONT_SIZE = 15
INNER_PADDING_X = 34
INNER_PADDING_Y = 30
TITLE_BAR_HEIGHT = 50
CAPTION_GAP = 20
ANSI_ESCAPE_PATTERN = re.compile(r"\x1b(?:\[[0-?]*[ -/]*[@-~]|\][^\x07]*(?:\x07|\x1b\\)|[@-Z\\-_])")
ANSI_CONSOLE = Console(color_system="truecolor", force_terminal=True)


class MonokaiExtendedStyle(Style):
    background_color = CARD_FILL
    default_style = ""
    styles = {
        Token: "#f8f8f2",
        Text: "#f8f8f2",
        Error: "#f8f8f2 bg:#f92672",
        Comment: "italic #75715e",
        Keyword: "#f92672",
        Keyword.Constant: "#66d9ef",
        Keyword.Declaration: "#66d9ef",
        Keyword.Namespace: "#f92672",
        Keyword.Pseudo: "#66d9ef",
        Keyword.Reserved: "#66d9ef",
        Keyword.Type: "#66d9ef",
        Name: "#f8f8f2",
        Name.Attribute: "#a6e22e",
        Name.Builtin: "#a6e22e",
        Name.Builtin.Pseudo: "#f8f8f2",
        Name.Class: "#a6e22e",
        Name.Constant: "#66d9ef",
        Name.Decorator: "#a6e22e",
        Name.Exception: "#a6e22e",
        Name.Function: "#a6e22e",
        Name.Label: "#f8f8f2",
        Name.Namespace: "#f8f8f2",
        Name.Tag: "#f92672",
        Name.Variable: "#f8f8f2",
        Name.Variable.Class: "#f8f8f2",
        Name.Variable.Global: "#f8f8f2",
        Name.Variable.Instance: "#f8f8f2",
        Literal: "#ae81ff",
        Number: "#ae81ff",
        Operator: "#f92672",
        Operator.Word: "#f92672",
        Punctuation: "#f8f8f2",
        String: "#e6db74",
        String.Regex: "#fd971f",
        Generic.Deleted: "#f92672",
        Generic.Emph: "italic #f8f8f2",
        Generic.Error: "#f92672",
        Generic.Heading: "bold #f8f8f2",
        Generic.Inserted: "#a6e22e",
        Generic.Output: "#75715e",
        Generic.Prompt: "#75715e",
        Generic.Strong: "bold #f8f8f2",
        Generic.Subheading: "bold #75715e",
        Generic.Traceback: "#f92672",
    }


class UnknownStyleError(ValueError):
    pass


class UnsupportedImageError(ValueError):
    pass


@dataclass(frozen=True)
class CardOptions:
    lexer: str | None = None
    theme: str = "monokai-extended"
    file_name: str | None = None
    title: str | None = None
    caption: str | None = None
    background: str = "aurora"
    width: int = 1080
    padding: int = 72
    radius: int = 30
    line_numbers: bool = False
    word_wrap: bool = False
    tab_size: int = 4


@dataclass(frozen=True)
class Fragment:
    text: str
    color: str
    bold: bool = False
    italic: bool = False


@dataclass(frozen=True)
class ImageContent:
    data_uri: str
    width: float
    height: float


def render_code_card_svg(code: str, options: CardOptions) -> str:
    gradients = BACKGROUND_PRESETS.get(options.background)
    if gradients is None:
        known = ", ".join(sorted(BACKGROUND_PRESETS))
        raise UnknownStyleError(f"Unknown background preset '{options.background}'. Use one of: {known}.")

    raw_lines = _highlight_lines(code, options)
    card_width = options.width - (options.padding * 2)
    code_width = card_width - (INNER_PADDING_X * 2)
    max_columns = max(20, int(code_width / CHAR_WIDTH))
    lines = _prepare_lines(raw_lines, max_columns, options.line_numbers, options.word_wrap)

    code_height = max(1, len(lines)) * LINE_HEIGHT
    caption_height = LINE_HEIGHT + CAPTION_GAP if options.caption else 0
    card_height = TITLE_BAR_HEIGHT + INNER_PADDING_Y + code_height + caption_height + INNER_PADDING_Y
    height = card_height + (options.padding * 2)
    card_x = options.padding
    card_y = options.padding
    code_x = card_x + INNER_PADDING_X
    code_y = card_y + TITLE_BAR_HEIGHT + INNER_PADDING_Y + FONT_SIZE

    parts = [
        _svg_open(options.width, height),
        _defs(*gradients),
        f'<rect width="100%" height="100%" fill="url(#card-bg)"/>',
        f'<rect x="{card_x}" y="{card_y}" width="{card_width}" height="{card_height}" '
        f'rx="{options.radius}" fill="{CARD_FILL}" stroke="{CARD_STROKE}" stroke-width="3" '
        f'filter="url(#soft-shadow)"/>',
        _title_bar(card_x, card_y, card_width, options.title),
        _code_lines(lines, code_x, code_y),
    ]
    if options.caption:
        caption_y = code_y + code_height + CAPTION_GAP
        parts.append(
            f'<text x="{code_x}" y="{caption_y}" font-family="{FONT_STACK}" font-size="13">'
            f'{_inline_tspans(options.caption, MUTED_TEXT)}'
            "</text>"
        )
    parts.append("</svg>")
    return "\n".join(parts)


def render_image_card_svg(image: bytes, file_name: str, options: CardOptions) -> str:
    gradients = BACKGROUND_PRESETS.get(options.background)
    if gradients is None:
        known = ", ".join(sorted(BACKGROUND_PRESETS))
        raise UnknownStyleError(f"Unknown background preset '{options.background}'. Use one of: {known}.")

    content = _load_image_content(image, file_name)
    card_width = options.width - (options.padding * 2)
    image_area_width = card_width - (INNER_PADDING_X * 2)
    scale = min(1.0, image_area_width / content.width)
    image_width = content.width * scale
    image_height = content.height * scale
    caption_height = LINE_HEIGHT + CAPTION_GAP if options.caption else 0
    card_height = TITLE_BAR_HEIGHT + INNER_PADDING_Y + image_height + caption_height + INNER_PADDING_Y
    height = card_height + (options.padding * 2)
    card_x = options.padding
    card_y = options.padding
    image_x = card_x + INNER_PADDING_X + ((image_area_width - image_width) / 2)
    image_y = card_y + TITLE_BAR_HEIGHT + INNER_PADDING_Y

    parts = [
        _svg_open(options.width, height),
        _defs(*gradients),
        f'<rect width="100%" height="100%" fill="url(#card-bg)"/>',
        f'<rect x="{card_x}" y="{card_y}" width="{card_width}" height="{card_height:.1f}" '
        f'rx="{options.radius}" fill="{CARD_FILL}" stroke="{CARD_STROKE}" stroke-width="3" '
        f'filter="url(#soft-shadow)"/>',
        _title_bar(card_x, card_y, card_width, options.title),
        f'<image x="{image_x:.1f}" y="{image_y:.1f}" width="{image_width:.1f}" height="{image_height:.1f}" '
        f'href="{content.data_uri}" preserveAspectRatio="xMidYMid meet"/>',
    ]
    if options.caption:
        caption_y = image_y + image_height + CAPTION_GAP + FONT_SIZE
        caption_x = card_x + INNER_PADDING_X
        parts.append(
            f'<text x="{caption_x}" y="{caption_y:.1f}" font-family="{FONT_STACK}" font-size="13">'
            f'{_inline_tspans(options.caption, MUTED_TEXT)}'
            "</text>"
        )
    parts.append("</svg>")
    return "\n".join(parts)


def _load_image_content(image: bytes, file_name: str) -> ImageContent:
    mime_type, width, height = _image_metadata(image, file_name)
    encoded = base64.b64encode(image).decode("ascii")
    return ImageContent(f"data:{mime_type};base64,{encoded}", width, height)


def _image_metadata(image: bytes, file_name: str) -> tuple[str, float, float]:
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
        while index < len(image) and image[index] == 0xFF:
            index += 1
        if index >= len(image):
            break
        marker = image[index]
        index += 1
        if marker in {0x01, *range(0xD0, 0xD8)}:
            continue
        if marker in {0xD9, 0xDA}:
            break
        if index + 2 > len(image):
            break
        segment_length = struct.unpack(">H", image[index : index + 2])[0]
        if segment_length < 2 or index + segment_length > len(image):
            break
        if marker in {
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
        }:
            if segment_length < 7:
                break
            height, width = struct.unpack(">HH", image[index + 3 : index + 7])
            if width <= 0 or height <= 0:
                raise UnsupportedImageError("JPEG image dimensions must be positive.")
            return float(width), float(height)
        index += segment_length
    raise UnsupportedImageError("Could not determine JPEG image dimensions.")


def _svg_dimensions(image: bytes) -> tuple[float, float]:
    try:
        root = ElementTree.fromstring(image)
    except ElementTree.ParseError as exc:
        raise UnsupportedImageError("Invalid SVG image.") from exc

    width = _svg_length(root.get("width", ""))
    height = _svg_length(root.get("height", ""))
    if width is not None and height is not None:
        return width, height

    view_box = root.get("viewBox")
    if view_box:
        try:
            values = [float(value) for value in re.split(r"[\s,]+", view_box.strip()) if value]
        except ValueError as exc:
            raise UnsupportedImageError("Could not determine SVG image dimensions. Add width/height or viewBox.") from exc
        if len(values) == 4 and values[2] > 0 and values[3] > 0:
            return values[2], values[3]

    raise UnsupportedImageError("Could not determine SVG image dimensions. Add width/height or viewBox.")


def _svg_length(value: str) -> float | None:
    match = re.fullmatch(r"\s*([0-9]+(?:\.[0-9]+)?)(?:px)?\s*", value)
    if not match:
        return None
    length = float(match.group(1))
    return length if length > 0 else None


def _highlight_lines(code: str, options: CardOptions) -> list[list[Fragment]]:
    if not code:
        return [[Fragment("", DEFAULT_TEXT)]]

    has_ansi = ANSI_ESCAPE_PATTERN.search(code)
    if has_ansi and options.lexer is None and options.file_name is None:
        return _ansi_lines(code.expandtabs(options.tab_size))
    if has_ansi:
        code = ANSI_ESCAPE_PATTERN.sub("", code)

    lexer = _load_lexer(code, options.lexer, options.file_name)
    style = _load_style(options.theme)
    lines: list[list[Fragment]] = [[]]
    for token_type, value in lex(code.expandtabs(options.tab_size), lexer):
        fragment_style = _token_style(token_type, style)
        _append_text(lines, value, fragment_style)
    if lines and not lines[-1]:
        lines.pop()
    return lines or [[Fragment("", DEFAULT_TEXT)]]


def _load_lexer(code: str, lexer_name: str | None, file_name: str | None):
    try:
        if lexer_name is not None:
            return get_lexer_by_name(lexer_name)
        if file_name is not None:
            return guess_lexer_for_filename(file_name, code)
        return get_lexer_by_name("text")
    except ClassNotFound as exc:
        raise UnknownStyleError(f"Unknown Pygments lexer '{lexer_name or file_name}'.") from exc


def _load_style(theme: str):
    if theme == "monokai-extended":
        return MonokaiExtendedStyle
    try:
        return get_style_by_name(theme)
    except ClassNotFound as exc:
        raise UnknownStyleError(f"Unknown Pygments style '{theme}'. Run `rich-card --list-themes`.") from exc


def _ansi_lines(code: str) -> list[list[Fragment]]:
    lines: list[list[Fragment]] = []
    for text in AnsiDecoder().decode(code):
        line = [_segment_to_fragment(segment.text, segment.style) for segment in text.render(ANSI_CONSOLE)]
        lines.append([fragment for fragment in line if fragment.text])
    if lines and not lines[-1]:
        lines.pop()
    return lines or [[Fragment("", DEFAULT_TEXT)]]


def _segment_to_fragment(text: str, style) -> Fragment:
    color = DEFAULT_TEXT
    if style and style.color:
        triplet = style.color.get_truecolor()
        color = f"#{triplet.red:02x}{triplet.green:02x}{triplet.blue:02x}"
    return Fragment(text, color, bool(style and style.bold), bool(style and style.italic))


def _token_style(token_type, style) -> Fragment:
    token_style = style.style_for_token(token_type)
    color = f"#{token_style['color']}" if token_style["color"] else DEFAULT_TEXT
    italic = bool(token_style["italic"]) and token_type not in Comment
    return Fragment("", color, bool(token_style["bold"]), italic)


def _append_text(lines: list[list[Fragment]], text: str, style: Fragment) -> None:
    chunks = text.split("\n")
    for index, chunk in enumerate(chunks):
        if index > 0:
            lines.append([])
        if chunk:
            _append_fragment(lines[-1], style, chunk)


def _prepare_lines(
    raw_lines: list[list[Fragment]],
    max_columns: int,
    line_numbers: bool,
    word_wrap: bool,
) -> list[list[Fragment]]:
    numbered_width = len(str(len(raw_lines))) if line_numbers else 0
    content_columns = max(12, max_columns - (numbered_width + 3 if line_numbers else 0))
    output: list[list[Fragment]] = []

    for index, fragments in enumerate(raw_lines, start=1):
        wrapped = _wrap_fragments(fragments, content_columns) if word_wrap else [fragments]
        for wrap_index, line in enumerate(wrapped):
            if line_numbers:
                label = str(index).rjust(numbered_width) if wrap_index == 0 else " " * numbered_width
                output.append([Fragment(f"{label} │ ", MUTED_TEXT), *line])
            else:
                output.append(line)
    return output


def _wrap_fragments(fragments: list[Fragment], width: int) -> list[list[Fragment]]:
    text = "".join(fragment.text for fragment in fragments)
    if cell_len(text) <= width:
        return [fragments]

    wrapped: list[list[Fragment]] = []
    line: list[Fragment] = []
    line_width = 0
    for fragment in fragments:
        spans, _total_width = split_graphemes(fragment.text)
        for start, end, grapheme_width in spans:
            if grapheme_width and line and line_width + grapheme_width > width:
                wrapped.append(line)
                line = []
                line_width = 0
            _append_fragment(line, fragment, fragment.text[start:end])
            line_width += grapheme_width
    if line:
        wrapped.append(line)
    return wrapped or [[]]


def _append_fragment(line: list[Fragment], template: Fragment, text: str) -> None:
    if not text:
        return
    if line and _same_style(line[-1], template):
        previous = line[-1]
        line[-1] = Fragment(previous.text + text, previous.color, previous.bold, previous.italic)
        return
    line.append(Fragment(text, template.color, bold=template.bold, italic=template.italic))


def _same_style(left: Fragment, right: Fragment) -> bool:
    return left.color == right.color and left.bold == right.bold and left.italic == right.italic


def _svg_open(width: int, height: int) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-label="Rendered code card">'
    )


def _defs(start: str, middle: str, end: str) -> str:
    return f"""<defs>
  <linearGradient id="card-bg" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0%" stop-color="{start}"/>
    <stop offset="52%" stop-color="{middle}"/>
    <stop offset="100%" stop-color="{end}"/>
  </linearGradient>
  <filter id="soft-shadow" x="-20%" y="-20%" width="140%" height="150%">
    <feDropShadow dx="0" dy="20" stdDeviation="22" flood-color="#101114" flood-opacity="0.38"/>
  </filter>
</defs>"""


def _title_bar(x: int, y: int, width: int, title: str | None) -> str:
    dots = [
        f'<circle cx="{x + 30}" cy="{y + 25}" r="6" fill="#ff5f57"/>',
        f'<circle cx="{x + 50}" cy="{y + 25}" r="6" fill="#ffbd2e"/>',
        f'<circle cx="{x + 70}" cy="{y + 25}" r="6" fill="#28c840"/>',
    ]
    label = ""
    if title:
        label = (
            f'<text x="{x + width / 2:.1f}" y="{y + 31}" '
            f'font-family="{FONT_STACK}" font-size="13" text-anchor="middle">'
            f'{_inline_tspans(title, MUTED_TEXT)}'
            "</text>"
        )
    rule = f'<line x1="{x}" y1="{y + TITLE_BAR_HEIGHT}" x2="{x + width}" y2="{y + TITLE_BAR_HEIGHT}" stroke="#34373c"/>'
    return "\n".join([*dots, label, rule])


def _code_lines(lines: list[list[Fragment]], x: int, y: int) -> str:
    output: list[str] = []
    for index, line in enumerate(lines):
        line_y = y + (index * LINE_HEIGHT)
        spans, overlays = _line_markup(line, x, line_y)
        output.append(
            f'<text x="{x}" y="{line_y}" font-family="{FONT_STACK}" '
            f'font-size="{FONT_SIZE}" xml:space="preserve">'
            f'{"".join(spans)}'
            "</text>"
        )
        output.extend(overlays)
    return "\n".join(output)


def _line_markup(line: list[Fragment], x: int, y: int) -> tuple[list[str], list[str]]:
    spans: list[str] = []
    overlays: list[str] = []
    cell_offset = 0
    for fragment in _coalesce_whitespace_fragments(line):
        if not fragment.text:
            continue
        spans.extend(_fragment_tspans(fragment))
        for start, end, grapheme_width in split_graphemes(fragment.text)[0]:
            grapheme = fragment.text[start:end]
            overlay = _emoji_overlay(grapheme, x + (cell_offset * CHAR_WIDTH), y, grapheme_width)
            if overlay:
                overlays.append(overlay)
            cell_offset += grapheme_width
    return spans, overlays


def _coalesce_whitespace_fragments(line: list[Fragment]) -> list[Fragment]:
    output: list[Fragment] = []
    for fragment in line:
        if output and fragment.text.isspace():
            previous = output[-1]
            output[-1] = Fragment(
                previous.text + fragment.text,
                previous.color,
                previous.bold,
                previous.italic,
            )
            continue
        output.append(fragment)
    return output


def _fragment_tspans(fragment: Fragment) -> list[str]:
    spans: list[str] = []
    text = ""
    mode = "normal"
    for start, end, _grapheme_width in split_graphemes(fragment.text)[0]:
        grapheme = fragment.text[start:end]
        grapheme_mode = _grapheme_mode(grapheme)
        if text and grapheme_mode != mode:
            spans.append(_tspan(text, fragment, mode))
            text = ""
        text += grapheme
        mode = grapheme_mode
    if text:
        spans.append(_tspan(text, fragment, mode))
    return spans


def _inline_tspans(text: str, color: str) -> str:
    return "".join(_fragment_tspans(Fragment(text, color)))


def _tspan(text: str, fragment: Fragment, mode: str) -> str:
    if mode == "emoji":
        attrs = [
            f'font-family="{EMOJI_FONT_STACK}"',
            'style="font-variant-emoji: emoji;"',
        ]
        if _has_color_overlay(text):
            attrs.append('fill-opacity="0"')
    elif mode == "icon":
        attrs = [
            f'fill="{fragment.color}"',
            f'font-family="{ICON_FONT_STACK}"',
        ]
    else:
        attrs = [f'fill="{fragment.color}"']
    if fragment.bold and mode != "emoji":
        attrs.append('font-weight="700"')
    if fragment.italic and mode != "emoji":
        attrs.append('font-style="italic"')
    return f'<tspan {" ".join(attrs)}>{_escape_xml_text(text)}</tspan>'


def _escape_xml_text(text: str) -> str:
    valid_text = "".join(character for character in text if _is_valid_xml_character(character))
    return escape(valid_text)


def _is_valid_xml_character(character: str) -> bool:
    codepoint = ord(character)
    return (
        codepoint in (0x09, 0x0A, 0x0D)
        or 0x20 <= codepoint <= 0xD7FF
        or 0xE000 <= codepoint <= 0xFFFD
        or 0x10000 <= codepoint <= 0x10FFFF
    )


def _grapheme_mode(text: str) -> str:
    if _is_emoji_grapheme(text):
        return "emoji"
    if _is_icon_grapheme(text):
        return "icon"
    return "normal"


def _is_icon_grapheme(text: str) -> bool:
    for character in text:
        codepoint = ord(character)
        if 0xE000 <= codepoint <= 0xF8FF:
            return True
        if 0xF0000 <= codepoint <= 0xFFFFD:
            return True
        if 0x100000 <= codepoint <= 0x10FFFD:
            return True
    return False


def _is_emoji_grapheme(text: str) -> bool:
    if "\ufe0f" in text or "\u200d" in text:
        return True
    for character in text:
        codepoint = ord(character)
        if 0x1F000 <= codepoint <= 0x1FAFF:
            return True
        if 0x2600 <= codepoint <= 0x27BF and category(character) == "So":
            return True
    return False


def _has_color_overlay(text: str) -> bool:
    return all(_emoji_svg(text[start:end]) for start, end, _width in split_graphemes(text)[0])


def _emoji_overlay(text: str, x: float, baseline_y: int, cells: int) -> str:
    svg = _emoji_svg(text)
    if not svg:
        return ""

    size = FONT_SIZE + 2
    slot_width = max(size, cells * CHAR_WIDTH)
    image_x = x + ((slot_width - size) / 2)
    image_y = baseline_y - FONT_SIZE + 1
    scale = size / 32
    return f'<g transform="translate({image_x:.1f} {image_y:.1f}) scale({scale:.3f})">{svg}</g>'


def _emoji_svg(text: str) -> str:
    normalized = text.replace("\ufe0f", "")
    if normalized in {"❤", "♥"}:
        return (
            '<path fill="#ff3b57" d="M23.6 4.8c-2.8 0-5.2 1.5-6.6 '
            '3.7-1.4-2.2-3.8-3.7-6.6-3.7C6.2 4.8 3 8 3 12.1c0 '
            '7.1 14 15.1 14 15.1s14-8 14-15.1c0-4.1-3.2-7.3-7.4-7.3z"/>'
        )
    if normalized == "✅":
        return (
            '<circle cx="16" cy="16" r="14" fill="#34c759"/>'
            '<path fill="none" stroke="#fff" stroke-width="4" stroke-linecap="round" '
            'stroke-linejoin="round" d="M8.5 16.5 13.5 21 23.5 10.5"/>'
        )
    if normalized == "✨":
        return (
            '<path fill="#ffd447" d="M16 2 19.6 12.4 30 16l-10.4 3.6L16 30l-3.6-10.4L2 16l10.4-3.6Z"/>'
            '<path fill="#fff2a3" d="M7 3 8.5 7.5 13 9 8.5 10.5 7 15 5.5 10.5 1 9 5.5 7.5Z"/>'
        )
    if normalized == "🚀":
        return (
            '<path fill="#dfe7f1" d="M17.5 2c5.4 2 8.3 6.6 8.7 13.7l-7.7 7.7-7-7C11.9 9.7 14 5 17.5 2Z"/>'
            '<path fill="#ff5f57" d="m11.5 16.4-5.1 1.7 3.4-7.2ZM18.5 23.4l-1.7 5.1 7.2-3.4Z"/>'
            '<circle cx="19" cy="10" r="3.2" fill="#48c7df"/>'
            '<path fill="#ffb000" d="M10 22c-3.2.8-5 2.6-6 6 3.4-1 5.2-2.8 6-6Z"/>'
        )
    return ""
