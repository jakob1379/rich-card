from __future__ import annotations

from collections.abc import Collection, Mapping
from dataclasses import dataclass
import json
import math
import os
from pathlib import Path
from typing import Any

from .options import (
    BACKGROUND_CHOICES,
    LOGO_PLACEMENTS,
    BackgroundChoice,
    LogoPlacement,
    require_background_choice,
    require_logo_placement,
)
from .renderer_options import RendererDefaults


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class CardConfig:
    lexer: str | None = None
    theme: str | None = None
    title: str | None = None
    logo: str | None = None
    logo_placement: LogoPlacement | None = None
    background: BackgroundChoice | None = None
    width: int | None = None
    padding: int | None = None
    inner_padding: int | None = None
    inner_padding_x: int | None = None
    inner_padding_y: int | None = None
    radius: int | None = None
    line_numbers: bool | None = None
    word_wrap: bool | None = None
    tab_size: int | None = None


@dataclass(frozen=True)
class RendererConfig:
    card_fill: str | None = None
    card_stroke: str | None = None
    muted_text: str | None = None
    default_text: str | None = None
    code_font_stack: str | None = None
    ui_font_stack: str | None = None
    chrome_font_stack: str | None = None
    emoji_text_fallback_stack: str | None = None
    emoji_font_stack: str | None = None
    icon_font_stack: str | None = None
    char_width: float | None = None
    line_height: int | None = None
    font_size: int | None = None
    title_bar_height: int | None = None
    title_bar_text_padding_x: int | None = None
    min_card_width: int | None = None
    logo_bar_max_height: int | None = None
    logo_bar_max_width: int | None = None
    logo_bar_right_padding: int | None = None
    logo_watermark_width_ratio: float | None = None
    logo_watermark_opacity: float | None = None


@dataclass(frozen=True)
class RichCardConfig:
    output: str | None = None
    card: CardConfig = CardConfig()
    renderer: RendererConfig = RendererConfig()
    path: Path | None = None


CARD_KEYS = frozenset(CardConfig.__dataclass_fields__)
RENDERER_KEYS = frozenset(RendererConfig.__dataclass_fields__)
TOP_LEVEL_KEYS = frozenset({"output", "card", "renderer"})


def default_config_path(env: Mapping[str, str] | None = None) -> Path:
    env = os.environ if env is None else env
    config_home = env.get("XDG_CONFIG_HOME")
    stripped = config_home.strip() if config_home else ""
    base = Path(stripped) if os.path.isabs(stripped) else Path.home() / ".config"
    return base / "rich-card" / "config.json"


def load_config(path: Path | None = None) -> RichCardConfig:
    """Load JSON config from path or default_config_path().

    Returns an empty RichCardConfig when the file does not exist. Raises
    ConfigError for read, parse, and validation failures. Only TOP_LEVEL_KEYS
    are accepted at the root; _card_config and _renderer_config validate
    nested card and renderer settings.
    """
    config_path = default_config_path() if path is None else path
    try:
        text = config_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return RichCardConfig(path=config_path)
    except (OSError, UnicodeDecodeError) as exc:
        raise ConfigError(f"{config_path}: could not read config: {exc}") from exc

    try:
        raw = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ConfigError(f"{config_path}: invalid JSON: {exc.msg}") from exc

    if not isinstance(raw, dict):
        raise ConfigError(f"{config_path}: config root must be a JSON object.")

    _reject_unknown_keys(config_path, "root", raw, TOP_LEVEL_KEYS)
    output = _optional_str(config_path, "output", raw.get("output"))
    card = _card_config(config_path, raw.get("card", {}))
    renderer = _renderer_config(config_path, raw.get("renderer", {}))
    return RichCardConfig(output=output, card=card, renderer=renderer, path=config_path)


def renderer_defaults(config: RendererConfig) -> RendererDefaults:
    defaults = RendererDefaults()
    default_fields = set(RendererDefaults.__dataclass_fields__)
    config_fields = set(RendererConfig.__dataclass_fields__)
    missing_in_config = sorted(default_fields - config_fields)
    extra_in_config = sorted(config_fields - default_fields)
    if missing_in_config:
        fields = ", ".join(missing_in_config)
        raise AssertionError(
            f"RendererConfig is missing RendererDefaults fields: {fields}."
        )
    if extra_in_config:
        fields = ", ".join(extra_in_config)
        raise AssertionError(
            f"RendererConfig has extra fields not present in RendererDefaults: {fields}."
        )

    return RendererDefaults(
        **{
            field: getattr(config, field)
            if getattr(config, field) is not None
            else getattr(defaults, field)
            for field in RendererDefaults.__dataclass_fields__
        }
    )


def _card_config(path: Path, raw: Any) -> CardConfig:
    if not isinstance(raw, dict):
        raise ConfigError(f"{path}: card must be a JSON object.")

    _reject_unknown_keys(path, "card", raw, CARD_KEYS)
    return CardConfig(
        lexer=_optional_str(path, "card.lexer", raw.get("lexer")),
        theme=_optional_str(path, "card.theme", raw.get("theme")),
        title=_optional_str(path, "card.title", raw.get("title")),
        logo=_optional_str(path, "card.logo", raw.get("logo")),
        logo_placement=_optional_logo_placement(
            path, "card.logo_placement", raw.get("logo_placement"), LOGO_PLACEMENTS
        ),
        background=_optional_background(
            path, "card.background", raw.get("background"), BACKGROUND_CHOICES
        ),
        width=_optional_int(
            path, "card.width", raw.get("width"), minimum=520, maximum=2400
        ),
        padding=_optional_int(
            path, "card.padding", raw.get("padding"), minimum=24, maximum=240
        ),
        inner_padding=_optional_int(
            path, "card.inner_padding", raw.get("inner_padding"), minimum=0, maximum=160
        ),
        inner_padding_x=_optional_int(
            path,
            "card.inner_padding_x",
            raw.get("inner_padding_x"),
            minimum=0,
            maximum=160,
        ),
        inner_padding_y=_optional_int(
            path,
            "card.inner_padding_y",
            raw.get("inner_padding_y"),
            minimum=0,
            maximum=160,
        ),
        radius=_optional_int(
            path, "card.radius", raw.get("radius"), minimum=4, maximum=80
        ),
        line_numbers=_optional_bool(path, "card.line_numbers", raw.get("line_numbers")),
        word_wrap=_optional_bool(path, "card.word_wrap", raw.get("word_wrap")),
        tab_size=_optional_int(
            path, "card.tab_size", raw.get("tab_size"), minimum=1, maximum=12
        ),
    )


def _renderer_config(path: Path, raw: Any) -> RendererConfig:
    if not isinstance(raw, dict):
        raise ConfigError(f"{path}: renderer must be a JSON object.")

    _reject_unknown_keys(path, "renderer", raw, RENDERER_KEYS)
    return RendererConfig(
        card_fill=_optional_str(path, "renderer.card_fill", raw.get("card_fill")),
        card_stroke=_optional_str(path, "renderer.card_stroke", raw.get("card_stroke")),
        muted_text=_optional_str(path, "renderer.muted_text", raw.get("muted_text")),
        default_text=_optional_str(
            path, "renderer.default_text", raw.get("default_text")
        ),
        code_font_stack=_optional_str(
            path, "renderer.code_font_stack", raw.get("code_font_stack")
        ),
        ui_font_stack=_optional_str(
            path, "renderer.ui_font_stack", raw.get("ui_font_stack")
        ),
        chrome_font_stack=_optional_str(
            path, "renderer.chrome_font_stack", raw.get("chrome_font_stack")
        ),
        emoji_text_fallback_stack=_optional_str(
            path,
            "renderer.emoji_text_fallback_stack",
            raw.get("emoji_text_fallback_stack"),
        ),
        emoji_font_stack=_optional_str(
            path, "renderer.emoji_font_stack", raw.get("emoji_font_stack")
        ),
        icon_font_stack=_optional_str(
            path, "renderer.icon_font_stack", raw.get("icon_font_stack")
        ),
        char_width=_optional_number(
            path, "renderer.char_width", raw.get("char_width"), minimum=0.1
        ),
        line_height=_optional_int(
            path, "renderer.line_height", raw.get("line_height"), minimum=1
        ),
        font_size=_optional_int(
            path, "renderer.font_size", raw.get("font_size"), minimum=1
        ),
        title_bar_height=_optional_int(
            path, "renderer.title_bar_height", raw.get("title_bar_height"), minimum=1
        ),
        title_bar_text_padding_x=_optional_int(
            path,
            "renderer.title_bar_text_padding_x",
            raw.get("title_bar_text_padding_x"),
            minimum=0,
        ),
        min_card_width=_optional_int(
            path, "renderer.min_card_width", raw.get("min_card_width"), minimum=1
        ),
        logo_bar_max_height=_optional_int(
            path,
            "renderer.logo_bar_max_height",
            raw.get("logo_bar_max_height"),
            minimum=1,
        ),
        logo_bar_max_width=_optional_int(
            path,
            "renderer.logo_bar_max_width",
            raw.get("logo_bar_max_width"),
            minimum=1,
        ),
        logo_bar_right_padding=_optional_int(
            path,
            "renderer.logo_bar_right_padding",
            raw.get("logo_bar_right_padding"),
            minimum=0,
        ),
        logo_watermark_width_ratio=_optional_number(
            path,
            "renderer.logo_watermark_width_ratio",
            raw.get("logo_watermark_width_ratio"),
            minimum=0.05,
            maximum=1.0,
        ),
        logo_watermark_opacity=_optional_number(
            path,
            "renderer.logo_watermark_opacity",
            raw.get("logo_watermark_opacity"),
            minimum=0.0,
            maximum=1.0,
        ),
    )


def _reject_unknown_keys(
    path: Path, section: str, raw: Mapping[str, Any], allowed: frozenset[str]
) -> None:
    unknown = sorted(set(raw) - allowed)
    if unknown:
        keys = ", ".join(unknown)
        raise ConfigError(f"{path}: unknown {section} key: {keys}.")


def _optional_str(path: Path, name: str, value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ConfigError(f"{path}: {name} must be a string.")
    if not value:
        raise ConfigError(f"{path}: {name} must be a non-empty string.")
    return value


def _optional_bool(path: Path, name: str, value: Any) -> bool | None:
    if value is None:
        return None
    if not isinstance(value, bool):
        raise ConfigError(f"{path}: {name} must be a boolean.")
    return value


def _optional_choice(
    path: Path, name: str, value: Any, choices: Collection[str]
) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ConfigError(f"{path}: {name} must be a string.")
    if value not in choices:
        known = ", ".join(sorted(choices))
        raise ConfigError(f"{path}: {name} must be one of: {known}.")
    return value


def _optional_background(
    path: Path, name: str, value: Any, choices: Collection[str]
) -> BackgroundChoice | None:
    choice = _optional_choice(path, name, value, choices)
    return None if choice is None else require_background_choice(choice)


def _optional_logo_placement(
    path: Path, name: str, value: Any, choices: Collection[str]
) -> LogoPlacement | None:
    choice = _optional_choice(path, name, value, choices)
    return None if choice is None else require_logo_placement(choice)


def _optional_int(
    path: Path,
    name: str,
    value: Any,
    *,
    minimum: int,
    maximum: int | None = None,
) -> int | None:
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool):
        raise ConfigError(f"{path}: {name} must be an integer.")
    if value < minimum or (maximum is not None and value > maximum):
        range_text = f"{minimum}..{maximum}" if maximum is not None else f">= {minimum}"
        raise ConfigError(f"{path}: {name} must be in range {range_text}.")
    return value


def _optional_number(
    path: Path,
    name: str,
    value: Any,
    *,
    minimum: float,
    maximum: float | None = None,
) -> float | None:
    if value is None:
        return None
    if not isinstance(value, int | float) or isinstance(value, bool):
        raise ConfigError(f"{path}: {name} must be a number.")
    if not math.isfinite(value):
        raise ConfigError(f"{path}: {name} must be finite.")
    if value < minimum or (maximum is not None and value > maximum):
        range_text = f"{minimum}..{maximum}" if maximum is not None else f">= {minimum}"
        raise ConfigError(f"{path}: {name} must be in range {range_text}.")
    return float(value)
