from __future__ import annotations

import unittest
from typing import Any, cast

from rich_card.options import (
    BACKGROUND_PRESETS,
    BackgroundPreset,
    DEFAULT_BACKGROUND,
    DEFAULT_CARD_RADIUS,
    DEFAULT_LOGO_PLACEMENT,
    LOGO_PLACEMENTS,
    LogoPlacement,
    require_background,
    require_logo_placement,
)


class RichCardOptionsTest(unittest.TestCase):
    def test_background_presets_mapping_cannot_be_mutated(self) -> None:
        presets = cast(Any, BACKGROUND_PRESETS)

        with self.assertRaises(TypeError):
            presets["new-background"] = ("#000000", "#111111", "#222222")

        self.assertNotIn("new-background", BACKGROUND_PRESETS)

    def test_require_background_returns_valid_input(self) -> None:
        self.assertEqual(require_background("aurora"), BackgroundPreset.aurora)
        self.assertEqual(require_background("ember"), BackgroundPreset.ember)

    def test_require_logo_placement_returns_valid_input(self) -> None:
        self.assertEqual(require_logo_placement("bar"), LogoPlacement.bar)
        self.assertEqual(require_logo_placement("watermark"), LogoPlacement.watermark)
        self.assertEqual(require_logo_placement("both"), LogoPlacement.both)

    def test_require_background_rejects_invalid_value_with_choices(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            r"Unknown background preset 'bogus'\. Use one of: .*aurora.*ember",
        ):
            require_background("bogus")

    def test_require_logo_placement_rejects_invalid_value_with_choices(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            r"Unknown logo placement 'corner'\. Use one of: .*bar.*both.*watermark",
        ):
            require_logo_placement("corner")

    def test_defaults_are_coherent(self) -> None:
        self.assertEqual(
            require_background(DEFAULT_BACKGROUND.value), DEFAULT_BACKGROUND
        )
        self.assertEqual(
            require_logo_placement(DEFAULT_LOGO_PLACEMENT.value), DEFAULT_LOGO_PLACEMENT
        )
        self.assertIn(DEFAULT_BACKGROUND.value, BACKGROUND_PRESETS)
        self.assertIn(DEFAULT_LOGO_PLACEMENT.value, LOGO_PLACEMENTS)
        self.assertEqual(DEFAULT_CARD_RADIUS, 12)
        self.assertEqual(len(BACKGROUND_PRESETS[DEFAULT_BACKGROUND.value]), 3)


if __name__ == "__main__":
    unittest.main()
