from __future__ import annotations

from dataclasses import dataclass


DEFAULT_THEME = "monokai-extended"
BUILTIN_ANSI_PALETTE = (
    "#1d1f21",
    "#cc6666",
    "#b5bd68",
    "#f0c674",
    "#81a2be",
    "#b294bb",
    "#8abeb7",
    "#c5c8c6",
    "#666666",
    "#d54e53",
    "#b9ca4a",
    "#e7c547",
    "#7aa6da",
    "#c397d8",
    "#70c0b1",
    "#eaeaea",
)


@dataclass(frozen=True)
class RendererDefaults:
    card_fill: str = "#26282b"
    card_stroke: str = "#3b3e43"
    muted_text: str = "#8d9199"
    default_text: str = "#f0f2f5"
    terminal_palette: str = "auto"
    ansi_palette: tuple[str, ...] = BUILTIN_ANSI_PALETTE
    code_font_stack: str = (
        "'JetBrains Mono', 'Cascadia Code', 'SFMono-Regular', Menlo, Consolas, "
        "monospace"
    )
    ui_font_stack: str = (
        "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, "
        "'Helvetica Neue', Arial, sans-serif"
    )
    chrome_font_stack: str = (
        "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, "
        "'Helvetica Neue', Arial, sans-serif"
    )
    emoji_text_fallback_stack: str = (
        "'JetBrains Mono', 'Cascadia Code', 'SFMono-Regular', Menlo, Consolas, "
        "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, "
        "'Helvetica Neue', Arial, sans-serif"
    )
    emoji_font_stack: str = (
        "'Apple Color Emoji', 'Segoe UI Emoji', 'Noto Color Emoji', "
        "'Twemoji Mozilla', 'JetBrains Mono', 'Cascadia Code', 'SFMono-Regular', "
        "Menlo, Consolas, system-ui, -apple-system, BlinkMacSystemFont, "
        "'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif"
    )
    icon_font_stack: str = (
        "'Symbols Nerd Font Mono', 'Symbols Nerd Font', 'JetBrains Mono', "
        "'Cascadia Code', 'SFMono-Regular', Menlo, Consolas, monospace"
    )
    char_width: float = 9.4
    line_height: int = 21
    font_size: int = 15
    title_bar_height: int = 50
    title_bar_text_padding_x: int = 96
    min_card_width: int = 160
    logo_bar_max_height: int = 26
    logo_bar_max_width: int = 120
    logo_bar_right_padding: int = 22
    logo_watermark_width_ratio: float = 0.45
    logo_watermark_opacity: float = 0.14


DEFAULT_RENDERER = RendererDefaults()
