from __future__ import annotations

import re

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
from rich.console import Console

from .errors import UnknownLexerError, UnknownStyleError
from .renderer_options import DEFAULT_RENDERER, DEFAULT_THEME, RendererDefaults
from .svg_fragments import Fragment, _append_fragment

ANSI_ESCAPE_PATTERN = re.compile(
    r"\x1b(?:\[[0-?]*[ -/]*[@-~]|\][^\x07]*(?:\x07|\x1b\\)|[@-Z\\-_])"
)
ANSI_CONSOLE = Console(color_system="truecolor", force_terminal=True)


class MonokaiExtendedStyle(Style):
    background_color = DEFAULT_RENDERER.card_fill
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


def _highlight_lines(
    code: str,
    *,
    renderer: RendererDefaults,
    lexer_name: str | None,
    file_name: str | None,
    tab_size: int,
    theme: str,
) -> list[list[Fragment]]:
    if not code:
        return [[Fragment("", renderer.default_text)]]

    has_ansi = ANSI_ESCAPE_PATTERN.search(code)
    if has_ansi and lexer_name is None and file_name is None:
        return _ansi_lines(code.expandtabs(tab_size), renderer)
    if has_ansi:
        code = ANSI_ESCAPE_PATTERN.sub("", code)

    lexer = _load_lexer(code, lexer_name, file_name)
    style = _load_style(theme)
    lines: list[list[Fragment]] = [[]]
    for token_type, value in lex(code.expandtabs(tab_size), lexer):
        fragment_style = _token_style(token_type, style, renderer)
        _append_text(lines, value, fragment_style)
    if lines and not lines[-1]:
        lines.pop()
    return lines or [[Fragment("", renderer.default_text)]]


def _load_lexer(code: str, lexer_name: str | None, file_name: str | None):
    try:
        if lexer_name is not None:
            return get_lexer_by_name(lexer_name)
        if file_name is not None:
            return guess_lexer_for_filename(file_name, code)
        return get_lexer_by_name("text")
    except ClassNotFound as exc:
        if lexer_name is not None:
            raise UnknownLexerError(f"Unknown Pygments lexer '{lexer_name}'.") from exc
        raise UnknownLexerError(
            f"Could not guess a Pygments lexer for filename '{file_name}'."
        ) from exc


def _load_style(theme: str):
    if theme == DEFAULT_THEME:
        return MonokaiExtendedStyle
    try:
        return get_style_by_name(theme)
    except ClassNotFound as exc:
        raise UnknownStyleError(
            f"Unknown Pygments style '{theme}'. Run `rich-card --list-themes`."
        ) from exc


def _ansi_lines(code: str, renderer: RendererDefaults) -> list[list[Fragment]]:
    lines: list[list[Fragment]] = []
    for text in AnsiDecoder().decode(code):
        line = [
            _segment_to_fragment(segment.text, segment.style, renderer)
            for segment in text.render(ANSI_CONSOLE)
        ]
        lines.append([fragment for fragment in line if fragment.text])
    if lines and not lines[-1]:
        lines.pop()
    return lines or [[Fragment("", renderer.default_text)]]


def _segment_to_fragment(text: str, style, renderer: RendererDefaults) -> Fragment:
    color = renderer.default_text
    if style and style.color:
        triplet = style.color.get_truecolor()
        color = f"#{triplet.red:02x}{triplet.green:02x}{triplet.blue:02x}"
    return Fragment(
        text, color, bool(style and style.bold), bool(style and style.italic)
    )


def _token_style(token_type, style, renderer: RendererDefaults) -> Fragment:
    token_style = style.style_for_token(token_type)
    color = (
        f"#{token_style['color']}" if token_style["color"] else renderer.default_text
    )
    italic = bool(token_style["italic"]) and token_type not in Comment
    return Fragment("", color, bool(token_style["bold"]), italic)


def _append_text(lines: list[list[Fragment]], text: str, style: Fragment) -> None:
    chunks = text.split("\n")
    for index, chunk in enumerate(chunks):
        if index > 0:
            lines.append([])
        if chunk:
            _append_fragment(lines[-1], style, chunk)
