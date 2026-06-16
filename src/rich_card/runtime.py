from __future__ import annotations

from contextlib import suppress
from dataclasses import dataclass
import os
from pathlib import Path
import subprocess  # nosec B404 - used for explicit user-requested --exec commands.
import sys
import tempfile

from .errors import RendererError, UnsupportedImageError
from .images import ImageContent, load_image_content
from .options import BackgroundChoice
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
    watermark: Path | None
    watermark_uses_logo: bool
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


COMMAND_PROMPT = "\x1b[32m❯\x1b[0m"


def render_card(
    source: Path | None,
    image: Path | None,
    command: str | None,
    settings: RenderSettings,
) -> Path:
    if image is not None and (source is not None or command is not None):
        raise RenderRuntimeError(
            "Image rendering cannot be combined with source or command input."
        )
    if command is not None and source is not None:
        raise RenderRuntimeError("--exec cannot be combined with a SOURCE path.")
    svg = (
        _render_image_card(image, settings)
        if image is not None
        else _render_code_card(source, command, settings)
    )
    _write_svg(settings.output, svg)
    return settings.output


def _read_source(source: Path | None) -> tuple[str, str | None]:
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

    raise RenderRuntimeError("Provide a SOURCE path, --exec, or piped stdin.")


def _read_command(command: str) -> str:
    env = os.environ.copy()
    env.pop("NO_COLOR", None)
    env.update(
        {
            "CLICOLOR_FORCE": "1",
            "FORCE_COLOR": "1",
            "COLORTERM": env.get("COLORTERM", "truecolor"),
        }
    )
    result = subprocess.run(  # nosec B602 - --exec intentionally runs user shell input.
        command,
        shell=True,
        executable=env.get("SHELL") or None,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return _command_transcript(command, result.stdout)


def _command_transcript(command: str, output: str) -> str:
    display_command = command.replace("\r", " ").replace("\n", " ")
    return f"{COMMAND_PROMPT} {display_command}\n{output}"


def _read_logo(path: Path | None, label: str = "logo") -> ImageContent | None:
    if path is None:
        return None
    try:
        return load_image_content(path.read_bytes(), path.name)
    except OSError as exc:
        raise RenderRuntimeError(
            f"Could not read {label} image '{path}': {exc}"
        ) from exc
    except UnsupportedImageError as exc:
        raise RenderRuntimeError(
            f"Could not load {label} image '{path}': {exc}"
        ) from exc


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
    watermark_content = _read_watermark(settings, logo_content)
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
            watermark=watermark_content,
            renderer=settings.renderer,
        ),
    )


def _render_code_card(
    source: Path | None,
    command: str | None,
    settings: RenderSettings,
) -> str:
    if command is None:
        code, source_name = _read_source(source)
        lexer = settings.lexer
        file_name = source_name
    else:
        code = _read_command(command)
        source_name = None
        lexer = None
        file_name = None
    logo_content = _read_logo(settings.logo)
    watermark_content = _read_watermark(settings, logo_content)
    resolved_title = settings.title if settings.title is not None else source_name
    return render_code_card_svg(
        code,
        CodeCardOptions(
            lexer=lexer,
            theme=settings.theme,
            file_name=file_name,
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
            watermark=watermark_content,
            renderer=settings.renderer,
        ),
    )


def _read_watermark(
    settings: RenderSettings, logo_content: ImageContent | None
) -> ImageContent | None:
    if settings.watermark_uses_logo:
        if logo_content is None:
            raise RenderRuntimeError(
                "--watermark requires --logo or configured card.logo."
            )
        return logo_content
    return _read_logo(settings.watermark, "watermark")


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
