from __future__ import annotations

from dataclasses import dataclass, replace
import os
import re
import select
import termios
import time
import tty

from .renderer_options import BUILTIN_ANSI_PALETTE, RendererDefaults

OSC_RESPONSE_PATTERN = re.compile(
    rb"\x1b\](?P<kind>4|10|11);(?:(?P<index>\d+);)?rgb:"
    rb"(?P<red>[0-9a-fA-F]+)/(?P<green>[0-9a-fA-F]+)/(?P<blue>[0-9a-fA-F])"
    rb"(?:\x07|\x1b\\)"
)


@dataclass(frozen=True)
class TerminalPalette:
    colors: tuple[str, ...]
    foreground: str
    background: str | None = None


def resolve_terminal_palette(renderer: RendererDefaults) -> TerminalPalette:
    configured = _configured_palette(renderer)
    if renderer.terminal_palette == "builtin":
        return TerminalPalette(BUILTIN_ANSI_PALETTE, renderer.default_text)
    if renderer.terminal_palette == "config":
        return TerminalPalette(configured, renderer.default_text)

    detected_colors, detected_foreground, detected_background = query_terminal_palette()
    colors = tuple(detected_colors.get(index, configured[index]) for index in range(16))
    return TerminalPalette(
        colors,
        detected_foreground or renderer.default_text,
        detected_background,
    )


def renderer_with_terminal_palette(renderer: RendererDefaults) -> RendererDefaults:
    palette = resolve_terminal_palette(renderer)
    return replace(
        renderer,
        card_fill=palette.background or renderer.card_fill,
        default_text=palette.foreground,
        terminal_palette="config",
        ansi_palette=palette.colors,
    )


def query_terminal_palette(
    timeout: float = 0.35,
) -> tuple[dict[int, str], str | None, str | None]:
    try:
        fd = os.open("/dev/tty", os.O_RDWR | os.O_NOCTTY)
    except OSError:
        return {}, None, None

    original_attrs = None
    try:
        original_attrs = termios.tcgetattr(fd)
        tty.setraw(fd, termios.TCSANOW)
        query = b"".join(
            [f"\x1b]4;{index};?\x07".encode("ascii") for index in range(16)]
            + [b"\x1b]10;?\x07", b"\x1b]11;?\x07"]
        )
        os.write(fd, query)
        response = _read_palette_response(fd, timeout)
    except OSError:
        return {}, None, None
    finally:
        if original_attrs is not None:
            try:
                termios.tcsetattr(fd, termios.TCSANOW, original_attrs)
            except termios.error:
                pass
        try:
            os.close(fd)
        except OSError:
            pass

    colors: dict[int, str] = {}
    foreground: str | None = None
    background: str | None = None
    for match in OSC_RESPONSE_PATTERN.finditer(response):
        color = _rgb_response_to_hex(
            match.group("red"), match.group("green"), match.group("blue")
        )
        if match.group("kind") == b"10":
            foreground = color
            continue
        if match.group("kind") == b"11":
            background = color
            continue
        index = int(match.group("index"))
        if 0 <= index < 16:
            colors[index] = color
    return colors, foreground, background


def _configured_palette(renderer: RendererDefaults) -> tuple[str, ...]:
    if len(renderer.ansi_palette) != 16:
        return BUILTIN_ANSI_PALETTE
    return tuple(color.lower() for color in renderer.ansi_palette)


def _read_palette_response(fd: int, timeout: float) -> bytes:
    deadline = time.monotonic() + timeout
    chunks: list[bytes] = []
    response = b""
    while time.monotonic() < deadline:
        readable, _, _ = select.select(
            [fd], [], [], max(0.0, deadline - time.monotonic())
        )
        if not readable:
            break
        chunk = os.read(fd, 4096)
        if not chunk:
            break
        chunks.append(chunk)
        response = b"".join(chunks)
        matches = list(OSC_RESPONSE_PATTERN.finditer(response))
        color_indexes = {
            int(match.group("index"))
            for match in matches
            if match.group("kind") == b"4" and match.group("index") is not None
        }
        has_foreground = any(match.group("kind") == b"10" for match in matches)
        has_background = any(match.group("kind") == b"11" for match in matches)
        if len(color_indexes) == 16 and has_foreground and has_background:
            break
    return response


def _rgb_response_to_hex(red: bytes, green: bytes, blue: bytes) -> str:
    return "#{:02x}{:02x}{:02x}".format(
        _channel_to_byte(red),
        _channel_to_byte(green),
        _channel_to_byte(blue),
    )


def _channel_to_byte(channel: bytes) -> int:
    value = int(channel, 16)
    max_value = (16 ** len(channel)) - 1
    return round((value / max_value) * 255)
