from __future__ import annotations

import json
import os
import re
import tempfile
import unittest
from pathlib import Path

from typer.testing import CliRunner

PNG_IMAGE = (
    b"\x89PNG\r\n\x1a\n"
    b"\x00\x00\x00\rIHDR"
    b"\x00\x00\x00\x02"
    b"\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00"
    b"\xf4x\xd4\xfa"
    b"\x00\x00\x00\x00IEND\xaeB`\x82"
)
JPEG_IMAGE = (
    b"\xff\xd8"
    b"\xff\xc0\x00\x11\x08"
    b"\x00\x03"
    b"\x00\x02"
    b"\x03\x01\x11\x00\x02\x11\x00\x03\x11\x00"
    b"\xff\xd9"
)
SVG_IMAGE = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 4 2"><rect width="4" height="2"/></svg>'


class RichCardsCliTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.runner = CliRunner()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.output = Path(self.tmp.name) / "card.svg"
        self.config_home = Path(self.tmp.name) / "xdg-config"
        self.old_xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
        os.environ["XDG_CONFIG_HOME"] = str(self.config_home)
        self.addCleanup(self.restore_xdg_config_home)

    def svg_width(self, path: Path) -> int:
        match = re.search(
            r'<svg[^>]* width="([0-9]+)"', path.read_text(encoding="utf-8")
        )
        self.assertIsNotNone(match)
        return int(match.group(1))

    def restore_xdg_config_home(self) -> None:
        if self.old_xdg_config_home is None:
            os.environ.pop("XDG_CONFIG_HOME", None)
        else:
            os.environ["XDG_CONFIG_HOME"] = self.old_xdg_config_home

    def write_config(self, config: object) -> Path:
        path = self.config_home / "rich-card" / "config.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(config), encoding="utf-8")
        return path
