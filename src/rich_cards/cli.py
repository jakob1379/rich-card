from __future__ import annotations

from enum import Enum
import sys
from pathlib import Path
from typing import Annotated

import typer
from pygments.lexers import get_lexer_by_name
from pygments.styles import get_all_styles, get_style_by_name
from pygments.util import ClassNotFound

from rich_cards.svg import (
    BACKGROUND_PRESETS,
    CardOptions,
    UnknownStyleError,
    render_code_card_svg,
)

BackgroundPreset = Enum(
    "BackgroundPreset",
    {name.replace("-", "_"): name for name in BACKGROUND_PRESETS},
    type=str,
)

app = typer.Typer(
    add_completion=False,
    context_settings={"help_option_names": ["-h", "--help"]},
    no_args_is_help=False,
)


def _read_source(source: Path | None, content: str | None) -> tuple[str, str | None]:
    if content is not None:
        return content, None

    if source is not None:
        return source.read_text(encoding="utf-8"), source.name

    if not sys.stdin.isatty():
        return sys.stdin.read(), None

    raise typer.BadParameter("Provide a SOURCE path, --content, or piped stdin.")


def _theme_callback(value: str) -> str:
    if value == "monokai-extended":
        return value
    try:
        get_style_by_name(value)
    except ClassNotFound as exc:
        raise typer.BadParameter(f"Unknown Pygments style '{value}'. Run `rich-cards --list-themes`.") from exc
    return value


def _lexer_callback(value: str | None) -> str | None:
    if value is None:
        return None
    try:
        get_lexer_by_name(value)
    except ClassNotFound as exc:
        raise typer.BadParameter(f"Unknown Pygments lexer '{value}'.") from exc
    return value


@app.command()
def render(
    source: Annotated[
        Path | None,
        typer.Argument(
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
            help="Optional source file. Omit to read from stdin.",
        ),
    ] = None,
    content: Annotated[
        str | None,
        typer.Option("--content", "-c", help="Inline code content. Takes precedence over SOURCE."),
    ] = None,
    output: Annotated[
        Path,
        typer.Option(
            "--output",
            "-o",
            file_okay=True,
            dir_okay=False,
            writable=True,
            help="SVG file to write.",
        ),
    ] = Path("card.svg"),
    lexer: Annotated[
        str | None,
        typer.Option(
            "--lexer",
            "-l",
            callback=_lexer_callback,
            help="Pygments lexer name. Defaults to source filename inference, or python for stdin.",
        ),
    ] = None,
    theme: Annotated[
        str,
        typer.Option(
            "--theme",
            "-s",
            callback=_theme_callback,
            help="Pygments theme name. See `rich-cards --list-themes`.",
        ),
    ] = "monokai-extended",
    title: Annotated[
        str | None,
        typer.Option("--title", "-t", help="Optional card title shown in the card chrome."),
    ] = None,
    caption: Annotated[
        str | None,
        typer.Option("--caption", "-C", help="Optional small caption below the code block."),
    ] = None,
    background: Annotated[
        BackgroundPreset,
        typer.Option("--background", "-b", help="Gradient preset."),
    ] = BackgroundPreset.aurora,
    width: Annotated[
        int,
        typer.Option("--width", "-w", min=520, max=2400, help="SVG canvas width in pixels."),
    ] = 1080,
    padding: Annotated[
        int,
        typer.Option("--padding", "-p", min=24, max=240, help="Outer canvas padding in pixels."),
    ] = 72,
    radius: Annotated[
        int,
        typer.Option("--radius", "-r", min=4, max=80, help="Rounded card corner radius in pixels."),
    ] = 30,
    line_numbers: Annotated[
        bool,
        typer.Option("--line-numbers/--no-line-numbers", "-n", help="Show line numbers."),
    ] = False,
    word_wrap: Annotated[
        bool,
        typer.Option("--word-wrap/--no-word-wrap", "-W", help="Wrap long lines inside the card."),
    ] = False,
    tab_size: Annotated[
        int,
        typer.Option("--tab-size", "-T", min=1, max=12, help="Tab expansion width."),
    ] = 4,
    list_themes: Annotated[
        bool,
        typer.Option("--list-themes", help="List syntax themes and exit."),
    ] = False,
) -> None:
    if list_themes:
        for theme_name in ["monokai-extended", *sorted(get_all_styles())]:
            typer.echo(theme_name)
        return

    code, source_name = _read_source(source, content)
    resolved_title = title if title is not None else source_name

    try:
        svg = render_code_card_svg(
            code,
            CardOptions(
                lexer=lexer,
                theme=theme,
                file_name=source_name,
                title=resolved_title,
                caption=caption,
                background=background.value,
                width=width,
                padding=padding,
                radius=radius,
                line_numbers=line_numbers,
                word_wrap=word_wrap,
                tab_size=tab_size,
            ),
        )
    except UnknownStyleError as exc:
        raise typer.BadParameter(str(exc)) from exc

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(svg, encoding="utf-8")
    typer.echo(str(output))
