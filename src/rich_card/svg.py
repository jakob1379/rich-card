from __future__ import annotations

from dataclasses import dataclass, field
import html
from math import ceil, isfinite
from typing import cast

from rich.cells import cell_len

from .errors import (
    InvalidRendererOptionError,
    UnknownBackgroundError,
)
from .images import ImageContent
from .options import (
    BACKGROUND_OFF,
    BACKGROUND_PRESETS,
    BackgroundChoice,
    DEFAULT_CARD_RADIUS,
    BackgroundPreset,
    LogoPlacement,
)
from .renderer_options import DEFAULT_RENDERER, DEFAULT_THEME, RendererDefaults
from .svg_fragments import (
    Fragment,
    _line_cell_width,
    _prepare_lines,
    _unwrapped_columns,
    _wrap_fragments as _wrap_fragments,
)
from .svg_markup import _code_lines, _inline_tspans
from .svg_syntax import _highlight_lines

CARD_FILL = DEFAULT_RENDERER.card_fill
CARD_STROKE = DEFAULT_RENDERER.card_stroke
MUTED_TEXT = DEFAULT_RENDERER.muted_text
DEFAULT_TEXT = DEFAULT_RENDERER.default_text
CODE_FONT_STACK = DEFAULT_RENDERER.code_font_stack
UI_FONT_STACK = DEFAULT_RENDERER.ui_font_stack
CHROME_FONT_STACK = DEFAULT_RENDERER.chrome_font_stack
EMOJI_TEXT_FALLBACK_STACK = DEFAULT_RENDERER.emoji_text_fallback_stack
EMOJI_FONT_STACK = DEFAULT_RENDERER.emoji_font_stack
ICON_FONT_STACK = DEFAULT_RENDERER.icon_font_stack
CHAR_WIDTH = DEFAULT_RENDERER.char_width
LINE_HEIGHT = DEFAULT_RENDERER.line_height
FONT_SIZE = DEFAULT_RENDERER.font_size
INNER_PADDING_X = 34
INNER_PADDING_Y = 30
TITLE_BAR_HEIGHT = DEFAULT_RENDERER.title_bar_height
TITLE_BAR_TEXT_PADDING_X = DEFAULT_RENDERER.title_bar_text_padding_x
MIN_CARD_WIDTH = DEFAULT_RENDERER.min_card_width

__all__ = [
    "CodeCardOptions",
    "CommonCardOptions",
    "Fragment",
    "ImageCardOptions",
    "INNER_PADDING_X",
    "INNER_PADDING_Y",
    "RendererDefaults",
    "render_code_card_svg",
    "render_image_card_svg",
]


@dataclass(frozen=True)
class CommonCardOptions:
    title: str | None = None
    background: BackgroundChoice = BackgroundPreset.aurora
    width: int | None = None
    padding: int = 72
    inner_padding_x: int = INNER_PADDING_X
    inner_padding_y: int = INNER_PADDING_Y
    radius: int = DEFAULT_CARD_RADIUS
    logo: ImageContent | None = None
    logo_placement: LogoPlacement = LogoPlacement.bar
    renderer: RendererDefaults = field(default_factory=RendererDefaults)

    def __post_init__(self) -> None:
        _validate_common_options(self)


@dataclass(frozen=True)
class CodeCardOptions(CommonCardOptions):
    lexer: str | None = None
    theme: str = DEFAULT_THEME
    file_name: str | None = None
    line_numbers: bool = False
    word_wrap: bool = False
    tab_size: int = 2


@dataclass(frozen=True)
class ImageCardOptions(CommonCardOptions):
    pass


def render_code_card_svg(code: str, options: CodeCardOptions) -> str:
    """Render code as SVG; renderer option failures raise RendererError."""
    renderer = options.renderer
    _validate_renderer_defaults(renderer)

    raw_lines = _highlight_lines(
        code,
        renderer=renderer,
        lexer_name=options.lexer,
        file_name=options.file_name,
        tab_size=options.tab_size,
        theme=options.theme,
    )
    if options.width is None:
        lines = _prepare_lines(
            raw_lines,
            _unwrapped_columns(raw_lines, options.line_numbers),
            line_numbers=options.line_numbers,
            muted_text=renderer.muted_text,
            word_wrap=False,
        )
        width = _auto_code_canvas_width(lines, options)
    else:
        width = options.width
        padding = _effective_padding(options)
        card_width = width - (padding * 2)
        code_width = max(1, card_width - (options.inner_padding_x * 2))
        max_columns = max(20, int(code_width / renderer.char_width))
        lines = _prepare_lines(
            raw_lines,
            max_columns,
            line_numbers=options.line_numbers,
            muted_text=renderer.muted_text,
            word_wrap=options.word_wrap,
        )

    padding = _effective_padding(options)
    card_width = width - (padding * 2)
    code_height = max(1, len(lines)) * renderer.line_height
    card_height = (
        renderer.title_bar_height
        + options.inner_padding_y
        + code_height
        + options.inner_padding_y
    )
    height = card_height + (padding * 2)
    card_x = padding
    card_y = padding
    code_x = card_x + options.inner_padding_x
    code_y = (
        card_y
        + renderer.title_bar_height
        + options.inner_padding_y
        + renderer.font_size
    )

    parts = _card_frame_parts(
        width,
        height,
        card_x,
        card_y,
        card_width,
        card_height,
        options,
        renderer,
        "Rendered code card",
    )
    parts.append(_code_lines(lines, code_x, code_y, renderer))
    parts.append("</svg>")
    return "\n".join(parts)


def render_image_card_svg(content: ImageContent, options: ImageCardOptions) -> str:
    """Render decoded image content as SVG; renderer failures raise RendererError."""
    renderer = options.renderer
    _validate_renderer_defaults(renderer)
    if options.width is None:
        width = _auto_image_canvas_width(content, options)
    else:
        width = options.width

    padding = _effective_padding(options)
    card_width = width - (padding * 2)
    image_area_width = max(1, card_width - (options.inner_padding_x * 2))
    scale = min(1.0, image_area_width / content.width)
    image_width = content.width * scale
    image_height = content.height * scale
    card_height = (
        renderer.title_bar_height
        + options.inner_padding_y
        + image_height
        + options.inner_padding_y
    )
    height = card_height + (padding * 2)
    card_x = padding
    card_y = padding
    image_x = card_x + options.inner_padding_x + ((image_area_width - image_width) / 2)
    image_y = card_y + renderer.title_bar_height + options.inner_padding_y

    parts = _card_frame_parts(
        width,
        height,
        card_x,
        card_y,
        card_width,
        card_height,
        options,
        renderer,
        "Rendered image card",
    )
    parts.append(
        f'<image x="{image_x:.1f}" y="{image_y:.1f}" width="{image_width:.1f}" height="{image_height:.1f}" '
        f'href="{html.escape(content.data_uri, quote=True)}" preserveAspectRatio="xMidYMid meet"/>'
    )
    parts.append("</svg>")
    return "\n".join(parts)


def _validate_common_options(options: CommonCardOptions) -> None:
    _validate_optional_string("title", options.title)
    if isinstance(options, CodeCardOptions):
        _validate_optional_string("lexer", options.lexer)
        _validate_string("theme", options.theme)
        _validate_optional_string("file_name", options.file_name)
    if not isinstance(options.renderer, RendererDefaults):
        raise InvalidRendererOptionError("renderer must be a RendererDefaults.")
    if options.background != BACKGROUND_OFF and not isinstance(
        options.background, BackgroundPreset
    ):
        raise InvalidRendererOptionError(
            "background must be a BackgroundPreset or 'off'."
        )
    if not isinstance(options.logo_placement, LogoPlacement):
        raise InvalidRendererOptionError("logo_placement must be a LogoPlacement.")
    if options.logo is not None and not isinstance(options.logo, ImageContent):
        raise InvalidRendererOptionError("logo must be an ImageContent or None.")
    _validate_optional_int("width", options.width, minimum=1)
    _validate_int("padding", options.padding, minimum=0)
    _validate_int("inner_padding_x", options.inner_padding_x, minimum=0)
    _validate_int("inner_padding_y", options.inner_padding_y, minimum=0)
    _validate_int("radius", options.radius, minimum=0)
    padding = _effective_padding(options)
    if options.width is not None and options.width <= padding * 2:
        raise InvalidRendererOptionError(
            "width must be greater than twice the padding."
        )
    if isinstance(options, CodeCardOptions):
        _validate_bool("line_numbers", options.line_numbers)
        _validate_bool("word_wrap", options.word_wrap)
        _validate_int("tab_size", options.tab_size, minimum=1, maximum=12)


def _validate_renderer_defaults(renderer: RendererDefaults) -> None:
    for field_name in (
        "char_width",
        "line_height",
        "font_size",
        "title_bar_height",
        "min_card_width",
        "logo_bar_max_height",
        "logo_bar_max_width",
    ):
        _validate_number(
            f"renderer.{field_name}", getattr(renderer, field_name), minimum=0.1
        )
    for field_name in ("title_bar_text_padding_x", "logo_bar_right_padding"):
        _validate_number(
            f"renderer.{field_name}", getattr(renderer, field_name), minimum=0
        )
    _validate_number(
        "renderer.logo_watermark_width_ratio",
        renderer.logo_watermark_width_ratio,
        minimum=0.1,
    )
    _validate_number(
        "renderer.logo_watermark_opacity",
        renderer.logo_watermark_opacity,
        minimum=0,
        maximum=1,
    )


def _validate_optional_int(name: str, value: int | None, *, minimum: int) -> None:
    if value is None:
        return
    _validate_int(name, value, minimum=minimum)


def _validate_int(
    name: str, value: int, *, minimum: int, maximum: int | None = None
) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise InvalidRendererOptionError(f"{name} must be an integer.")
    if value < minimum or (maximum is not None and value > maximum):
        range_text = f"{minimum}..{maximum}" if maximum is not None else f">= {minimum}"
        raise InvalidRendererOptionError(f"{name} must be in range {range_text}.")


def _validate_bool(name: str, value: bool) -> None:
    if not isinstance(value, bool):
        raise InvalidRendererOptionError(f"{name} must be a boolean.")


def _validate_string(name: str, value: object) -> None:
    if not isinstance(value, str):
        raise InvalidRendererOptionError(f"{name} must be a string.")


def _validate_optional_string(name: str, value: object) -> None:
    if value is not None and not isinstance(value, str):
        raise InvalidRendererOptionError(f"{name} must be a string or None.")


def _validate_number(
    name: str, value: float | int, *, minimum: float, maximum: float | None = None
) -> None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise InvalidRendererOptionError(f"{name} must be a number.")
    if not isfinite(value):
        raise InvalidRendererOptionError(f"{name} must be finite.")
    if value < minimum or (maximum is not None and value > maximum):
        range_text = f"{minimum}..{maximum}" if maximum is not None else f">= {minimum}"
        raise InvalidRendererOptionError(f"{name} must be in range {range_text}.")


def _background_gradients(background: BackgroundPreset) -> tuple[str, str, str]:
    try:
        return BACKGROUND_PRESETS[background.value]
    except KeyError as exc:
        raise UnknownBackgroundError(
            f"Unknown background preset '{background}'."
        ) from exc


def _effective_padding(options: CommonCardOptions) -> int:
    return 0 if options.background == BACKGROUND_OFF else options.padding


def _card_frame_parts(
    width: float,
    height: float,
    card_x: int,
    card_y: int,
    card_width: float,
    card_height: float,
    options: CommonCardOptions,
    renderer: RendererDefaults,
    aria_label: str = "Rendered code card",
) -> list[str]:
    parts = [_svg_open(width, height, aria_label)]
    filter_attr = ""
    if options.background != BACKGROUND_OFF:
        gradients = _background_gradients(options.background)
        parts.extend(
            [
                _defs(*gradients),
                '<rect width="100%" height="100%" fill="url(#card-bg)"/>',
            ]
        )
        filter_attr = ' filter="url(#soft-shadow)"'
    parts.extend(
        [
            f'<rect x="{card_x}" y="{card_y}" width="{_number(card_width)}" height="{_number(card_height)}" '
            f'rx="{options.radius}" fill="{renderer.card_fill}" '
            f'stroke="{renderer.card_stroke}" stroke-width="3"{filter_attr}/>',
            _watermark_logo(
                options,
                card_x,
                card_y + renderer.title_bar_height,
                int(card_width),
                card_height - renderer.title_bar_height,
            ),
            _title_bar(
                card_x,
                card_y,
                int(card_width),
                options.title,
                _bar_logo_content(options),
                renderer,
            ),
        ]
    )
    return parts


def _number(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else f"{value:.1f}"


def _auto_code_canvas_width(
    lines: list[list[Fragment]], options: CodeCardOptions
) -> int:
    content_width = ceil(
        max((_line_cell_width(line) for line in lines), default=0)
        * options.renderer.char_width
    )
    return _auto_canvas_width(content_width, options)


def _auto_image_canvas_width(content: ImageContent, options: CommonCardOptions) -> int:
    return _auto_canvas_width(ceil(content.width), options)


def _auto_canvas_width(content_width: int, options: CommonCardOptions) -> int:
    logo_width = _logo_bar_reserved_width(_bar_logo_content(options), options.renderer)
    padding = _effective_padding(options)
    card_width = max(
        options.renderer.min_card_width,
        options.inner_padding_x * 2 + content_width,
        _inline_card_width(
            options.title,
            options.renderer.title_bar_text_padding_x + logo_width,
            options.renderer,
        ),
    )
    return card_width + (padding * 2)


def _inline_card_width(
    text: str | None, side_padding: float, renderer: RendererDefaults
) -> int:
    if not text:
        return 0
    return ceil(cell_len(text) * renderer.char_width + (side_padding * 2))


def _svg_open(
    width: float, height: float, aria_label: str = "Rendered code card"
) -> str:
    escaped_label = html.escape(aria_label, quote=True)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-label="{escaped_label}">'
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


def _title_bar(
    x: int,
    y: int,
    width: int,
    title: str | None,
    logo: ImageContent | None,
    renderer: RendererDefaults,
) -> str:
    dots = [
        f'<circle cx="{x + 30}" cy="{y + 25}" r="6" fill="#ff5f57"/>',
        f'<circle cx="{x + 50}" cy="{y + 25}" r="6" fill="#ffbd2e"/>',
        f'<circle cx="{x + 70}" cy="{y + 25}" r="6" fill="#28c840"/>',
    ]
    logo_markup = _bar_logo(x, y, width, logo, renderer)
    clip = ""
    label = ""
    if title:
        left_padding = renderer.title_bar_text_padding_x
        right_padding = renderer.title_bar_text_padding_x + _logo_bar_reserved_width(
            logo, renderer
        )
        clip_width = max(1, width - left_padding - right_padding)
        clip = (
            '<clipPath id="title-clip">'
            f'<rect x="{x + left_padding}" y="{y}" width="{clip_width}" '
            f'height="{renderer.title_bar_height}"/>'
            "</clipPath>"
        )
        label = (
            f'<text x="{x + width / 2:.1f}" y="{y + 31}" '
            f'font-family="{renderer.chrome_font_stack}" font-size="13" '
            'text-anchor="middle" clip-path="url(#title-clip)">'
            f"{_inline_tspans(title, renderer.muted_text, renderer)}"
            "</text>"
        )
    rule = (
        f'<line x1="{x}" y1="{y + renderer.title_bar_height}" '
        f'x2="{x + width}" y2="{y + renderer.title_bar_height}" stroke="#34373c"/>'
    )
    return "\n".join([*dots, clip, label, logo_markup, rule])


def _logo_bar_reserved_width(
    logo: ImageContent | None, renderer: RendererDefaults
) -> float:
    if logo is None:
        return 0
    logo_width, _logo_height = _scaled_logo_size(logo, *_bar_logo_size_limit(renderer))
    return logo_width + renderer.logo_bar_right_padding + 16


def _bar_logo(
    x: int,
    y: int,
    width: int,
    logo: ImageContent | None,
    renderer: RendererDefaults,
) -> str:
    if logo is None:
        return ""

    max_width, max_height = _bar_logo_size_limit(renderer)
    max_width = min(max_width, max(1.0, width - renderer.logo_bar_right_padding - 96))
    logo_width, logo_height = _scaled_logo_size(logo, max_width, max_height)
    image_x = x + width - renderer.logo_bar_right_padding - logo_width
    image_y = y + ((renderer.title_bar_height - logo_height) / 2)
    return (
        f'<image class="rich-card-logo rich-card-logo-bar" x="{image_x:.1f}" '
        f'y="{image_y:.1f}" width="{logo_width:.1f}" height="{logo_height:.1f}" '
        f'href="{html.escape(logo.data_uri, quote=True)}" preserveAspectRatio="xMidYMid meet"/>'
    )


def _watermark_logo(
    options: CommonCardOptions, x: int, y: float, width: int, height: float
) -> str:
    if not _has_logo_placement(options, LogoPlacement.watermark):
        return ""

    logo = cast(ImageContent, options.logo)
    renderer = options.renderer
    max_width = width * renderer.logo_watermark_width_ratio
    max_height = max(1.0, height * 0.72)
    logo_width, logo_height = _scaled_logo_size(logo, max_width, max_height)
    image_x = x + ((width - logo_width) / 2)
    image_y = y + ((height - logo_height) / 2)
    return (
        f'<image class="rich-card-logo rich-card-logo-watermark" x="{image_x:.1f}" '
        f'y="{image_y:.1f}" width="{logo_width:.1f}" height="{logo_height:.1f}" '
        f'opacity="{renderer.logo_watermark_opacity:.3g}" href="{html.escape(logo.data_uri, quote=True)}" '
        'preserveAspectRatio="xMidYMid meet"/>'
    )


def _bar_logo_size_limit(renderer: RendererDefaults) -> tuple[float, float]:
    return (
        float(renderer.logo_bar_max_width),
        float(min(renderer.logo_bar_max_height, renderer.title_bar_height)),
    )


def _has_logo_placement(options: CommonCardOptions, placement: LogoPlacement) -> bool:
    if options.logo is None:
        return False
    return options.logo_placement in {placement, LogoPlacement.both}


def _bar_logo_content(options: CommonCardOptions) -> ImageContent | None:
    if _has_logo_placement(options, LogoPlacement.bar):
        return options.logo
    return None


def _scaled_logo_size(
    logo: ImageContent, max_width: float, max_height: float
) -> tuple[float, float]:
    scale = min(max_width / logo.width, max_height / logo.height)
    return logo.width * scale, logo.height * scale
