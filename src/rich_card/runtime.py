from __future__ import annotations

from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
import sys
import tempfile

from .errors import RendererError, UnsupportedImageError
from .images import ImageContent, load_image_content
from .options import BackgroundChoice, LogoPlacement
from .renderer_options import RendererDefaults
from .svg import (
    CodeCardOptions,
    ImageCardOptions,
    render_code_card_svg,
    render_image_card_svg,
)


@dataclass(frozen=True)
class RenderSettings:
    output: Path
    lexer: str | None
    theme: str
    title: str | None
    logo: Path | None
    logo_placement: LogoPlacement
    background: BackgroundChoice
    width: int | None
    padding: int
    inner_padding_x: int
    inner_padding_y: int
    radius: int
    line_numbers: bool
    word_wrap: bool
    tab_size: int
    renderer: RendererDefaults


class RenderRuntimeError(RendererError):
    pass


def render_card(
    source: Path | None,
    content: str | None,
    image: Path | None,
    settings: RenderSettings,
) -> Path:
    if image is not None and (source is not None or content is not None):
        raise RenderRuntimeError(
            "Image rendering cannot be combined with source or content input."
        )
    svg = (
        _render_image_card(image, settings)
        if image is not None
        else _render_code_card(source, content, settings)
    )
    _write_svg(settings.output, svg)
    return settings.output


def _read_source(source: Path | None, content: str | None) -> tuple[str, str | None]:
    if content is not None:
        return content, None

    if source is not None:
        try:
            return source.read_text(encoding="utf-8"), source.name
        except (OSError, UnicodeDecodeError) as exc:
            raise RenderRuntimeError(
                f"Could not read source file '{source}': {exc}"
            ) from exc

    if not sys.stdin.isatty():
        try:
            return sys.stdin.read(), None
        except (OSError, UnicodeDecodeError) as exc:
            raise RenderRuntimeError(f"Could not read stdin: {exc}") from exc

    raise RenderRuntimeError("Provide a SOURCE path, --content, or piped stdin.")


def _read_logo(logo: Path | None) -> ImageContent | None:
    if logo is None:
        return None
    try:
        return load_image_content(logo.read_bytes(), logo.name)
    except OSError as exc:
        raise RenderRuntimeError(f"Could not read logo image '{logo}': {exc}") from exc
    except UnsupportedImageError as exc:
        raise RenderRuntimeError(f"Could not load logo image '{logo}': {exc}") from exc


def _read_image_content(image: Path) -> ImageContent:
    try:
        return load_image_content(image.read_bytes(), image.name)
    except OSError as exc:
        raise RenderRuntimeError(f"Could not read image file '{image}': {exc}") from exc
    except UnsupportedImageError as exc:
        raise RenderRuntimeError(f"Could not load image file '{image}': {exc}") from exc


def _render_image_card(image: Path, settings: RenderSettings) -> str:
    image_content = _read_image_content(image)
    logo_content = _read_logo(settings.logo)
    return render_image_card_svg(
        image_content,
        ImageCardOptions(
            title=settings.title if settings.title is not None else image.name,
            background=settings.background,
            width=settings.width,
            padding=settings.padding,
            inner_padding_x=settings.inner_padding_x,
            inner_padding_y=settings.inner_padding_y,
            radius=settings.radius,
            logo=logo_content,
            logo_placement=settings.logo_placement,
            renderer=settings.renderer,
        ),
    )


def _render_code_card(
    source: Path | None,
    content: str | None,
    settings: RenderSettings,
) -> str:
    code, source_name = _read_source(source, content)
    logo_content = _read_logo(settings.logo)
    resolved_title = settings.title if settings.title is not None else source_name
    return render_code_card_svg(
        code,
        CodeCardOptions(
            lexer=settings.lexer,
            theme=settings.theme,
            file_name=source_name,
            title=resolved_title,
            line_numbers=settings.line_numbers,
            word_wrap=settings.word_wrap,
            tab_size=settings.tab_size,
            background=settings.background,
            width=settings.width,
            padding=settings.padding,
            inner_padding_x=settings.inner_padding_x,
            inner_padding_y=settings.inner_padding_y,
            radius=settings.radius,
            logo=logo_content,
            logo_placement=settings.logo_placement,
            renderer=settings.renderer,
        ),
    )


def _write_svg(output: Path, svg: str) -> None:
    temp_path: Path | None = None
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=output.parent, delete=False
        ) as temp_file:
            temp_path = Path(temp_file.name)
            temp_file.write(f"{svg}\n")
        temp_path.replace(output)
    except OSError as exc:
        if temp_path is not None:
            with suppress(OSError):
                temp_path.unlink(missing_ok=True)
        raise RenderRuntimeError(f"Could not write SVG file '{output}': {exc}") from exc
