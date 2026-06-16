from __future__ import annotations

from collections.abc import Collection, Mapping
from enum import StrEnum
from types import MappingProxyType
from typing import Literal

from .errors import InvalidRendererOptionError


BackgroundStops = tuple[str, str, str]


class BackgroundPreset(StrEnum):
    aurora = "aurora"
    blue_raspberry = "blue-raspberry"
    cosmic_lumen = "cosmic-lumen"
    dusty_grass = "dusty-grass"
    ember = "ember"
    electric_twilight = "electric-twilight"
    frozen_dream = "frozen-dream"
    lagoon = "lagoon"
    megatron = "megatron"
    moss = "moss"
    mono = "mono"
    night_fade = "night-fade"
    nordic = "nordic"
    premium_dark = "premium-dark"
    prism = "prism"
    rainy_ashville = "rainy-ashville"
    sublime_light = "sublime-light"
    sunny_morning = "sunny-morning"
    tempting_azure = "tempting-azure"
    warm_flame = "warm-flame"
    winter_neva = "winter-neva"


BackgroundChoice = BackgroundPreset | Literal["off"]


BACKGROUND_PRESETS: Mapping[str, BackgroundStops] = MappingProxyType(
    {
        "aurora": ("#f7fbff", "#bdefff", "#48c7df"),
        "blue-raspberry": ("#dff9ff", "#00b4db", "#0083b0"),
        "cosmic-lumen": ("#07111f", "#1ba6ff", "#d9fbff"),
        "dusty-grass": ("#f6ffd7", "#d4fc79", "#96e6a1"),
        "ember": ("#f6b05f", "#dc574d", "#231f20"),
        "electric-twilight": ("#0b1026", "#00d4ff", "#ff2fb3"),
        "frozen-dream": ("#fdcbf1", "#e6dee9", "#d9e7ff"),
        "lagoon": ("#35d4b4", "#3574d4", "#1f2440"),
        "megatron": ("#c6ffdd", "#fbd786", "#f7797d"),
        "moss": ("#b9d96d", "#4e9c75", "#17261f"),
        "mono": ("#f2f2ed", "#b9b8b0", "#4f5254"),
        "night-fade": ("#a18cd1", "#fbc2eb", "#ffe7f3"),
        "nordic": ("#2e3440", "#5e81ac", "#88c0d0"),
        "premium-dark": ("#434343", "#171717", "#000000"),
        "prism": ("#c0c0c0", "#d4f1f9", "#fff9d4"),
        "rainy-ashville": ("#fbc2eb", "#a6c1ee", "#d7e8ff"),
        "sublime-light": ("#fc5c7d", "#8c6ff5", "#6a82fb"),
        "sunny-morning": ("#f6d365", "#fda085", "#ff7f8f"),
        "tempting-azure": ("#84fab0", "#8fd3f4", "#9bd7ff"),
        "warm-flame": ("#ff9a9e", "#fad0c4", "#fad0c4"),
        "winter-neva": ("#a1c4fd", "#c2e9fb", "#eef8ff"),
    }
)
BACKGROUND_OFF = "off"
BACKGROUND_CHOICES = (*BACKGROUND_PRESETS, BACKGROUND_OFF)
DEFAULT_BACKGROUND = BackgroundPreset.aurora
DEFAULT_CARD_RADIUS = 12


def format_choices(values: Mapping[str, object] | Collection[str]) -> str:
    return ", ".join(sorted(values))


def require_background(value: str) -> BackgroundPreset:
    if value not in BACKGROUND_PRESETS:
        raise InvalidRendererOptionError(
            f"Unknown background preset '{value}'. Use one of: {format_choices(BACKGROUND_PRESETS)}."
        )
    return BackgroundPreset(value)


def require_background_choice(value: str) -> BackgroundChoice:
    if value == BACKGROUND_OFF:
        return BACKGROUND_OFF
    if value in BACKGROUND_PRESETS:
        return BackgroundPreset(value)
    raise InvalidRendererOptionError(
        f"Unknown background option '{value}'. Use one of: {format_choices(BACKGROUND_CHOICES)}."
    )
