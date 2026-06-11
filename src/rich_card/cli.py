from pathlib import Path
from typing import Annotated

import typer
from pygments.styles import get_all_styles

from .config import (
    ConfigError,
    RichCardConfig,
    load_config,
    renderer_defaults,
)
from .errors import RendererError
from .options import (
    BackgroundPreset,
    DEFAULT_CARD_RADIUS,
    LogoPlacement,
)
from .renderer_options import DEFAULT_THEME
from .runtime import RenderSettings, render_card

app = typer.Typer(
    add_completion=False,
    context_settings={"help_option_names": ["-h", "--help"]},
    no_args_is_help=False,
)


CODE_ONLY_OPTIONS = ("lexer", "theme", "line_numbers", "word_wrap", "tab_size")


def _validate_image_mode(
    ctx: typer.Context, source: Path | None, content: str | None
) -> None:
    if source is not None:
        raise typer.BadParameter("--image cannot be used with a SOURCE path.")
    if content is not None:
        raise typer.BadParameter("--image cannot be used with --content.")
    for name in CODE_ONLY_OPTIONS:
        if not _uses_default(ctx, name):
            option = name.replace("_", "-")
            raise typer.BadParameter(f"--image cannot be used with --{option}.")


def _uses_default(ctx: typer.Context, name: str) -> bool:
    source = ctx.get_parameter_source(name)
    return source is not None and source.name == "DEFAULT"


def _configured_value[T](
    ctx: typer.Context, name: str, current: T, configured: T | None
) -> T:
    if configured is not None and _uses_default(ctx, name):
        return configured
    return current


def _background_value(
    ctx: typer.Context, current: BackgroundPreset, configured: BackgroundPreset | None
) -> BackgroundPreset:
    if configured is None or not _uses_default(ctx, "background"):
        return current
    return configured


def _configured_path(
    ctx: typer.Context, name: str, current: Path | None, configured: str | None
) -> Path | None:
    if configured is not None and _uses_default(ctx, name):
        return Path(configured)
    return current


def _logo_placement_value(
    ctx: typer.Context, current: LogoPlacement, configured: LogoPlacement | None
) -> LogoPlacement:
    if configured is None or not _uses_default(ctx, "logo_placement"):
        return current
    return configured


def _inner_padding_options(
    ctx: typer.Context,
    inner_padding: int | None,
    config_inner: tuple[int | None, int | None, int | None],
) -> tuple[int, int]:
    if inner_padding is not None and not _uses_default(ctx, "inner_padding"):
        return inner_padding, inner_padding

    configured_uniform, configured_x, configured_y = config_inner
    inner_padding_x = configured_uniform if configured_uniform is not None else None
    inner_padding_y = configured_uniform if configured_uniform is not None else None
    if configured_x is not None:
        inner_padding_x = configured_x
    if configured_y is not None:
        inner_padding_y = configured_y

    return (
        34 if inner_padding_x is None else inner_padding_x,
        30 if inner_padding_y is None else inner_padding_y,
    )


def _resolve_settings(
    ctx: typer.Context,
    config: RichCardConfig,
    output: Path,
    lexer: str | None,
    theme: str,
    title: str | None,
    logo: Path | None,
    logo_placement: LogoPlacement,
    background: BackgroundPreset,
    width: int | None,
    padding: int,
    inner_padding: int | None,
    radius: int,
    line_numbers: bool,
    word_wrap: bool,
    tab_size: int,
) -> RenderSettings:
    card_config = config.card
    inner_padding_x, inner_padding_y = _inner_padding_options(
        ctx,
        inner_padding,
        (
            card_config.inner_padding,
            card_config.inner_padding_x,
            card_config.inner_padding_y,
        ),
    )
    resolved_output = (
        Path(config.output)
        if config.output is not None and _uses_default(ctx, "output")
        else output
    )
    return RenderSettings(
        output=resolved_output,
        lexer=_configured_value(ctx, "lexer", lexer, card_config.lexer),
        theme=_configured_value(ctx, "theme", theme, card_config.theme),
        title=_configured_value(ctx, "title", title, card_config.title),
        logo=_configured_path(ctx, "logo", logo, card_config.logo),
        logo_placement=_logo_placement_value(
            ctx, logo_placement, card_config.logo_placement
        ),
        background=_background_value(ctx, background, card_config.background),
        width=_configured_value(ctx, "width", width, card_config.width),
        padding=_configured_value(ctx, "padding", padding, card_config.padding),
        inner_padding_x=inner_padding_x,
        inner_padding_y=inner_padding_y,
        radius=_configured_value(ctx, "radius", radius, card_config.radius),
        line_numbers=_configured_value(
            ctx, "line_numbers", line_numbers, card_config.line_numbers
        ),
        word_wrap=_configured_value(ctx, "word_wrap", word_wrap, card_config.word_wrap),
        tab_size=_configured_value(ctx, "tab_size", tab_size, card_config.tab_size),
        renderer=renderer_defaults(config.renderer),
    )


SourceArg = Annotated[
    Path | None,
    typer.Argument(
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Optional source file. Omit to read from stdin.",
    ),
]
ContentOption = Annotated[
    str | None,
    typer.Option(
        "--content", "-c", help="Inline code content. Takes precedence over SOURCE."
    ),
]
ImageOption = Annotated[
    Path | None,
    typer.Option(
        "--image",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Image file to render inside the card. Supports PNG, JPEG, and SVG.",
    ),
]
OutputOption = Annotated[
    Path,
    typer.Option(
        "--output",
        "-o",
        file_okay=True,
        dir_okay=False,
        writable=True,
        help="SVG file to write.",
    ),
]
LexerOption = Annotated[
    str | None,
    typer.Option(
        "--lexer",
        "-l",
        help="Pygments lexer name. Defaults to source filename inference, or ANSI-aware plain text for stdin.",
    ),
]
ThemeOption = Annotated[
    str,
    typer.Option(
        "--theme", "-s", help="Pygments theme name. See `rich-card --list-themes`."
    ),
]
TitleOption = Annotated[
    str | None,
    typer.Option("--title", "-t", help="Optional card title shown in the card chrome."),
]
LogoOption = Annotated[
    Path | None,
    typer.Option(
        "--logo",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Logo image to place in the title bar, terminal background, or both. Supports PNG, JPEG, and SVG.",
    ),
]
LogoPlacementOption = Annotated[
    LogoPlacement,
    typer.Option("--logo-placement", help="Where to render --logo."),
]
BackgroundOption = Annotated[
    BackgroundPreset,
    typer.Option("--background", "-b", help="Gradient preset."),
]
WidthOption = Annotated[
    int | None,
    typer.Option(
        "--width", "-w", min=520, max=2400, help="Fixed SVG canvas width in pixels."
    ),
]
PaddingOption = Annotated[
    int,
    typer.Option(
        "--padding",
        "--background-padding",
        "-p",
        min=24,
        max=240,
        help="Background padding outside the terminal card in pixels.",
    ),
]
InnerPaddingOption = Annotated[
    int | None,
    typer.Option(
        "--inner-padding",
        "--terminal-padding",
        min=0,
        max=160,
        help="Padding inside the terminal card around the content or image.",
    ),
]
RadiusOption = Annotated[
    int,
    typer.Option(
        "--radius", "-r", min=4, max=80, help="Rounded card corner radius in pixels."
    ),
]
LineNumbersOption = Annotated[
    bool,
    typer.Option("--line-numbers/--no-line-numbers", "-n", help="Show line numbers."),
]
WordWrapOption = Annotated[
    bool,
    typer.Option(
        "--word-wrap/--no-word-wrap", "-W", help="Wrap long lines inside the card."
    ),
]
TabSizeOption = Annotated[
    int,
    typer.Option("--tab-size", "-T", min=1, max=12, help="Tab expansion width."),
]
ListThemesOption = Annotated[
    bool,
    typer.Option("--list-themes", help="List syntax themes and exit."),
]


@app.command()
def render(
    ctx: typer.Context,
    source: SourceArg = None,
    content: ContentOption = None,
    image: ImageOption = None,
    output: OutputOption = Path("card.svg"),
    lexer: LexerOption = None,
    theme: ThemeOption = DEFAULT_THEME,
    title: TitleOption = None,
    logo: LogoOption = None,
    logo_placement: LogoPlacementOption = LogoPlacement.bar,
    background: BackgroundOption = BackgroundPreset.aurora,
    width: WidthOption = None,
    padding: PaddingOption = 72,
    inner_padding: InnerPaddingOption = None,
    radius: RadiusOption = DEFAULT_CARD_RADIUS,
    line_numbers: LineNumbersOption = False,
    word_wrap: WordWrapOption = False,
    tab_size: TabSizeOption = 2,
    list_themes: ListThemesOption = False,
) -> None:
    if list_themes:
        for theme_name in [DEFAULT_THEME, *sorted(get_all_styles())]:
            typer.echo(theme_name)
        return

    try:
        config = load_config()
        settings = _resolve_settings(
            ctx,
            config,
            output,
            lexer,
            theme,
            title,
            logo,
            logo_placement,
            background,
            width,
            padding,
            inner_padding,
            radius,
            line_numbers,
            word_wrap,
            tab_size,
        )
        if image is not None:
            _validate_image_mode(ctx, source, content)
        output_path = render_card(source, content, image, settings)
    except (ConfigError, RendererError) as exc:
        raise typer.BadParameter(str(exc)) from exc

    typer.echo(str(output_path))
