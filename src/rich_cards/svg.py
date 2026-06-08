from __future__ import annotations

from dataclasses import dataclass
from html import escape
from textwrap import wrap

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
FONT_STACK = "'JetBrains Mono', 'Cascadia Code', 'SFMono-Regular', Menlo, Consolas, monospace"
CHAR_WIDTH = 9.4
LINE_HEIGHT = 21
FONT_SIZE = 15
INNER_PADDING_X = 34
INNER_PADDING_Y = 30
TITLE_BAR_HEIGHT = 50
CAPTION_GAP = 20


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
            f'<text x="{code_x}" y="{caption_y}" fill="{MUTED_TEXT}" '
            f'font-family="{FONT_STACK}" font-size="13">{escape(options.caption)}</text>'
        )
    parts.append("</svg>")
    return "\n".join(parts)


def _highlight_lines(code: str, options: CardOptions) -> list[list[Fragment]]:
    if not code:
        return [[Fragment("", DEFAULT_TEXT)]]

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
        return get_lexer_by_name("python")
    except ClassNotFound as exc:
        raise UnknownStyleError(f"Unknown Pygments lexer '{lexer_name or file_name}'.") from exc


def _load_style(theme: str):
    if theme == "monokai-extended":
        return MonokaiExtendedStyle
    try:
        return get_style_by_name(theme)
    except ClassNotFound as exc:
        raise UnknownStyleError(f"Unknown Pygments style '{theme}'. Run `rich-cards --list-themes`.") from exc


def _token_style(token_type, style) -> Fragment:
    token_style = style.style_for_token(token_type)
    color = f"#{token_style['color']}" if token_style["color"] else DEFAULT_TEXT
    return Fragment("", color, bool(token_style["bold"]), bool(token_style["italic"]))


def _append_text(lines: list[list[Fragment]], text: str, style: Fragment) -> None:
    chunks = text.split("\n")
    for index, chunk in enumerate(chunks):
        if index > 0:
            lines.append([])
        if chunk:
            lines[-1].append(Fragment(chunk, style.color, style.bold, style.italic))


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
    if len(text) <= width:
        return [fragments]

    wrapped_text = wrap(text, width=width, replace_whitespace=False, drop_whitespace=False) or [""]
    wrapped: list[list[Fragment]] = []
    cursor = 0
    flat = [(fragment, start, start + len(fragment.text)) for start, fragment in _fragment_offsets(fragments)]
    for line_text in wrapped_text:
        line_end = cursor + len(line_text)
        line: list[Fragment] = []
        for fragment, start, end in flat:
            overlap_start = max(start, cursor)
            overlap_end = min(end, line_end)
            if overlap_start < overlap_end:
                text_start = overlap_start - start
                text_end = overlap_end - start
                line.append(
                    Fragment(
                        fragment.text[text_start:text_end],
                        fragment.color,
                        bold=fragment.bold,
                        italic=fragment.italic,
                    )
                )
        wrapped.append(line)
        cursor = line_end
    return wrapped


def _fragment_offsets(fragments: list[Fragment]):
    cursor = 0
    for fragment in fragments:
        yield cursor, fragment
        cursor += len(fragment.text)


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
            f'<text x="{x + width / 2:.1f}" y="{y + 31}" fill="{MUTED_TEXT}" '
            f'font-family="{FONT_STACK}" font-size="13" text-anchor="middle">{escape(title)}</text>'
        )
    rule = f'<line x1="{x}" y1="{y + TITLE_BAR_HEIGHT}" x2="{x + width}" y2="{y + TITLE_BAR_HEIGHT}" stroke="#34373c"/>'
    return "\n".join([*dots, label, rule])


def _code_lines(lines: list[list[Fragment]], x: int, y: int) -> str:
    output: list[str] = []
    for index, line in enumerate(lines):
        line_y = y + (index * LINE_HEIGHT)
        spans: list[str] = []
        for fragment in line:
            if not fragment.text:
                continue
            attrs = [f'fill="{fragment.color}"']
            if fragment.bold:
                attrs.append('font-weight="700"')
            if fragment.italic:
                attrs.append('font-style="italic"')
            spans.append(f'<tspan {" ".join(attrs)}>{escape(fragment.text)}</tspan>')
        output.append(
            f'<text x="{x}" y="{line_y}" font-family="{FONT_STACK}" '
            f'font-size="{FONT_SIZE}" xml:space="preserve">'
            f'{"".join(spans)}'
            "</text>"
        )
    return "\n".join(output)
