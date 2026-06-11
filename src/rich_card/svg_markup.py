from __future__ import annotations

from html import escape
from unicodedata import category

from rich.cells import split_graphemes

from .renderer_options import RendererDefaults
from .svg_fragments import Fragment


def _code_lines(
    lines: list[list[Fragment]], x: int, y: int, renderer: RendererDefaults
) -> str:
    output: list[str] = []
    for index, line in enumerate(lines):
        line_y = y + (index * renderer.line_height)
        spans, overlays = _line_markup(line, x, line_y, renderer)
        output.append(
            f'<text x="{x}" y="{line_y}" font-family="{renderer.code_font_stack}" '
            f'font-size="{renderer.font_size}" xml:space="preserve">'
            f"{''.join(spans)}</text>"
        )
        output.extend(overlays)
    return "\n".join(output)


def _line_markup(
    line: list[Fragment], x: int, y: int, renderer: RendererDefaults
) -> tuple[list[str], list[str]]:
    spans: list[str] = []
    overlays: list[str] = []
    cell_offset = 0
    for fragment in _coalesce_whitespace_fragments(line):
        if not fragment.text:
            continue
        spans.extend(_fragment_tspans(fragment, renderer))
        for start, end, grapheme_width in split_graphemes(fragment.text)[0]:
            grapheme = fragment.text[start:end]
            overlay = _emoji_overlay(
                grapheme,
                x + (cell_offset * renderer.char_width),
                y,
                grapheme_width,
                renderer,
            )
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


def _fragment_tspans(fragment: Fragment, renderer: RendererDefaults) -> list[str]:
    spans: list[str] = []
    text = ""
    mode = "normal"
    for start, end, _grapheme_width in split_graphemes(fragment.text)[0]:
        grapheme = fragment.text[start:end]
        grapheme_mode = _grapheme_mode(grapheme)
        if text and grapheme_mode != mode:
            spans.append(_tspan(text, fragment, mode, renderer))
            text = ""
        text += grapheme
        mode = grapheme_mode
    if text:
        spans.append(_tspan(text, fragment, mode, renderer))
    return spans


def _inline_tspans(text: str, color: str, renderer: RendererDefaults) -> str:
    return "".join(_fragment_tspans(Fragment(text, color), renderer))


def _tspan(text: str, fragment: Fragment, mode: str, renderer: RendererDefaults) -> str:
    if mode == "emoji":
        attrs = [
            f'font-family="{renderer.emoji_font_stack}"',
            'style="font-variant-emoji: emoji;"',
        ]
        if _has_color_overlay(text):
            attrs.append('fill-opacity="0"')
    elif mode == "icon":
        attrs = [
            f'fill="{fragment.color}"',
            f'font-family="{renderer.icon_font_stack}"',
        ]
    else:
        attrs = [f'fill="{fragment.color}"']
    if fragment.bold and mode != "emoji":
        attrs.append('font-weight="700"')
    if fragment.italic and mode != "emoji":
        attrs.append('font-style="italic"')
    return f"<tspan {' '.join(attrs)}>{_escape_xml_text(text)}</tspan>"


def _escape_xml_text(text: str) -> str:
    valid_text = "".join(
        character for character in text if _is_valid_xml_character(character)
    )
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
        if (
            0xE000 <= codepoint <= 0xF8FF
            or 0xF0000 <= codepoint <= 0xFFFFD
            or 0x100000 <= codepoint <= 0x10FFFD
        ):
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
    return all(
        _emoji_svg(text[start:end]) for start, end, _width in split_graphemes(text)[0]
    )


def _emoji_overlay(
    text: str, x: float, baseline_y: int, cells: int, renderer: RendererDefaults
) -> str:
    svg = _emoji_svg(text)
    if not svg:
        return ""

    size = renderer.font_size + 2
    slot_width = max(size, cells * renderer.char_width)
    image_x = x + ((slot_width - size) / 2)
    image_y = baseline_y - renderer.font_size + 1
    scale = size / 32
    return f'<g transform="translate({image_x:.1f} {image_y:.1f}) scale({scale:.3f})">{svg}</g>'


def _emoji_svg(text: str) -> str:
    normalized = text.replace("\ufe0f", "")
    if normalized in {"❤", "♥"}:
        return '<path fill="#ff3b57" d="M23.6 4.8c-2.8 0-5.2 1.5-6.6 3.7-1.4-2.2-3.8-3.7-6.6-3.7C6.2 4.8 3 8 3 12.1c0 7.1 14 15.1 14 15.1s14-8 14-15.1c0-4.1-3.2-7.3-7.4-7.3z"/>'
    if normalized == "✅":
        return '<circle cx="16" cy="16" r="14" fill="#34c759"/><path fill="none" stroke="#fff" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" d="M8.5 16.5 13.5 21 23.5 10.5"/>'
    if normalized == "✨":
        return '<path fill="#ffd447" d="M16 2 19.6 12.4 30 16l-10.4 3.6L16 30l-3.6-10.4L2 16l10.4-3.6Z"/><path fill="#fff2a3" d="M7 3 8.5 7.5 13 9 8.5 10.5 7 15 5.5 10.5 1 9 5.5 7.5Z"/>'
    if normalized == "🚀":
        return '<path fill="#dfe7f1" d="M17.5 2c5.4 2 8.3 6.6 8.7 13.7l-7.7 7.7-7-7C11.9 9.7 14 5 17.5 2Z"/><path fill="#ff5f57" d="m11.5 16.4-5.1 1.7 3.4-7.2ZM18.5 23.4l-1.7 5.1 7.2-3.4Z"/><circle cx="19" cy="10" r="3.2" fill="#48c7df"/><path fill="#ffb000" d="M10 22c-3.2.8-5 2.6-6 6 3.4-1 5.2-2.8 6-6Z"/>'
    return ""
