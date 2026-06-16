from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path
import sys
from typing import Annotated

from pygments.styles import get_all_styles
import typer
from typer.core import TyperCommand

from .config import (
    ConfigError,
    RichCardConfig,
    load_config,
    renderer_defaults,
)
from .errors import RendererError
from .options import (
    BACKGROUND_CHOICES,
    BackgroundChoice,
    BackgroundPreset,
    DEFAULT_CARD_RADIUS,
    require_background_choice,
)
from .renderer_options import DEFAULT_THEME
from .runtime import RenderSettings, render_card

app = typer.Typer(
    add_completion=False,
    context_settings={"help_option_names": ["-h", "--help"]},
    no_args_is_help=False,
)


CODE_ONLY_OPTIONS = ("lexer", "theme", "line_numbers", "word_wrap", "tab_size")
REQUIRED_VALUE_OPTIONS = {"--logo"}
WATERMARK_USE_LOGO = "__rich_card_watermark_use_logo__"


class RichCardCommand(TyperCommand):
    def main(
        self,
        args: Sequence[str] | None = None,
        prog_name: str | None = None,
        complete_var: str | None = None,
        standalone_mode: bool = True,
        windows_expand_args: bool = True,
        **extra: object,
    ) -> object:
        normalized_args = _normalize_optional_watermark_args(
            sys.argv[1:] if args is None else args
        )
        return super().main(
            args=normalized_args,
            prog_name=prog_name,
            complete_var=complete_var,
            standalone_mode=standalone_mode,
            windows_expand_args=windows_expand_args,
            **extra,
        )


def _normalize_optional_watermark_args(args: Sequence[str]) -> list[str]:
    normalized: list[str] = []
    index = 0
    while index < len(args):
        arg = args[index]
        if arg in REQUIRED_VALUE_OPTIONS and (
            index + 1 == len(args) or _looks_like_option(args[index + 1])
        ):
            return [arg]
        normalized.append(arg)
        if arg == "--":
            normalized.extend(args[index + 1 :])
            break
        if arg == "--watermark" and (
            index + 1 == len(args) or _looks_like_option(args[index + 1])
        ):
            normalized.append(WATERMARK_USE_LOGO)
        index += 1
    return normalized


def _looks_like_option(value: str) -> bool:
    return value != "-" and value.startswith("-")


def _validate_image_mode(
    ctx: typer.Context, source: Path | None, command: str | None
) -> None:
    if source is not None:
        raise typer.BadParameter("--image cannot be used with a SOURCE path.")
    if command is not None:
        raise typer.BadParameter("--image cannot be used with --exec.")
    for name in CODE_ONLY_OPTIONS:
        if not _uses_default(ctx, name):
            option = name.replace("_", "-")
            raise typer.BadParameter(f"--image cannot be used with --{option}.")


def _validate_exec_mode(
    ctx: typer.Context, source: Path | None, image: Path | None
) -> None:
    if source is not None:
        raise typer.BadParameter("--exec cannot be used with a SOURCE path.")
    if image is not None:
        raise typer.BadParameter("--exec cannot be used with --image.")
    if not _uses_default(ctx, "lexer"):
        raise typer.BadParameter("--exec cannot be used with --lexer.")


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
    ctx: typer.Context, current: str, configured: BackgroundChoice | None
) -> BackgroundChoice:
    if configured is None or not _uses_default(ctx, "background"):
        return require_background_choice(current)
    return configured


def _configured_path(
    ctx: typer.Context, name: str, current: Path | None, configured: str | None
) -> Path | None:
    if configured is not None and _uses_default(ctx, name):
        return Path(configured)
    return current


def _watermark_value(
    ctx: typer.Context,
    logo: Path | None,
    current: str | None,
    configured: str | bool | None,
) -> tuple[Path | None, bool]:
    if not _uses_default(ctx, "watermark"):
        return _watermark_cli_value(logo, current)
    if configured is True:
        if logo is None:
            raise typer.BadParameter("card.watermark requires card.logo or --logo.")
        return None, True
    if isinstance(configured, str):
        return Path(configured), False
    return None, False


def _watermark_cli_value(
    logo: Path | None, watermark: str | None
) -> tuple[Path | None, bool]:
    if watermark == WATERMARK_USE_LOGO:
        if logo is None:
            raise typer.BadParameter(
                "--watermark requires --logo or configured card.logo."
            )
        return None, True
    if watermark:
        return Path(watermark), False
    raise typer.BadParameter("--watermark must be a non-empty image path.")


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
    watermark: str | None,
    background: str,
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
    resolved_logo = _configured_path(ctx, "logo", logo, card_config.logo)
    resolved_watermark, watermark_uses_logo = _watermark_value(
        ctx, resolved_logo, watermark, card_config.watermark
    )
    return RenderSettings(
        output=resolved_output,
        lexer=_configured_value(ctx, "lexer", lexer, card_config.lexer),
        theme=_configured_value(ctx, "theme", theme, card_config.theme),
        title=_configured_value(ctx, "title", title, card_config.title),
        logo=resolved_logo,
        watermark=resolved_watermark,
        watermark_uses_logo=watermark_uses_logo,
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
ExecOption = Annotated[
    str | None,
    typer.Option("--exec", "-x", help="Run a command and render its terminal output."),
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
        help="Logo image to place in the title bar. Supports PNG, JPEG, and SVG.",
    ),
]
WatermarkOption = Annotated[
    str | None,
    typer.Option(
        "--watermark",
        metavar="[FILE]",
        help="Render a watermark. Omit FILE to reuse --logo. Supports PNG, JPEG, and SVG.",
    ),
]
BackgroundOption = Annotated[
    str,
    typer.Option(
        "--background",
        "-b",
        help="Background option. See `rich-card --list-backgrounds`.",
    ),
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
ListBackgroundsOption = Annotated[
    bool,
    typer.Option("--list-backgrounds", help="List background options and exit."),
]


@app.command(cls=RichCardCommand)
def render(
    ctx: typer.Context,
    source: SourceArg = None,
    command: ExecOption = None,
    image: ImageOption = None,
    output: OutputOption = Path("card.svg"),
    lexer: LexerOption = None,
    theme: ThemeOption = DEFAULT_THEME,
    title: TitleOption = None,
    logo: LogoOption = None,
    watermark: WatermarkOption = None,
    background: BackgroundOption = BackgroundPreset.aurora.value,
    width: WidthOption = None,
    padding: PaddingOption = 72,
    inner_padding: InnerPaddingOption = None,
    radius: RadiusOption = DEFAULT_CARD_RADIUS,
    line_numbers: LineNumbersOption = False,
    word_wrap: WordWrapOption = False,
    tab_size: TabSizeOption = 2,
    list_themes: ListThemesOption = False,
    list_backgrounds: ListBackgroundsOption = False,
) -> None:
    if list_themes:
        for theme_name in [DEFAULT_THEME, *sorted(get_all_styles())]:
            typer.echo(theme_name)
        return
    if list_backgrounds:
        for background_name in BACKGROUND_CHOICES:
            typer.echo(background_name)
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
            watermark,
            background,
            width,
            padding,
            inner_padding,
            radius,
            line_numbers,
            word_wrap,
            tab_size,
        )
        if command is not None:
            _validate_exec_mode(ctx, source, image)
            if settings.title is None:
                settings = replace(settings, title=command)
        if image is not None:
            _validate_image_mode(ctx, source, command)
        output_path = render_card(source, image, command, settings)
    except (ConfigError, RendererError) as exc:
        raise typer.BadParameter(str(exc)) from exc

    typer.echo(str(output_path))
