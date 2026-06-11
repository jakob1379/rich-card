from __future__ import annotations

import importlib.util
import subprocess  # nosec B404 - tests mock subprocess results and constants only.
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import click


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "update_generated_docs.py"


def load_script():
    spec = importlib.util.spec_from_file_location("update_generated_docs", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load update_generated_docs.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class UpdateGeneratedDocsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.docs = load_script()

    def test_run_uses_bounded_subprocess_timeout(self) -> None:
        completed = subprocess.CompletedProcess(["cmd"], 0, "out", "")

        with mock.patch.object(
            self.docs.subprocess, "run", return_value=completed
        ) as run:
            self.assertEqual(self.docs._run(["cmd"], {"ENV": "value"}), "out")

        run.assert_called_once_with(
            ["cmd"],
            cwd=self.docs.ROOT,
            env={"ENV": "value"},
            text=True,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=self.docs.COMMAND_TIMEOUT_SECONDS,
        )

    def test_run_exits_on_timeout(self) -> None:
        timeout = subprocess.TimeoutExpired(["cmd"], 30, output="out", stderr="err")

        with mock.patch.object(self.docs.subprocess, "run", side_effect=timeout):
            with mock.patch.object(self.docs.sys.stderr, "write") as write:
                with self.assertRaisesRegex(SystemExit, "Command timed out"):
                    self.docs._run(["cmd"], {})

        write.assert_has_calls([mock.call("out"), mock.call("err")])

    def test_update_readme_replaces_only_cli_reference_block(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            readme = Path(tmp) / "README.md"
            readme.write_text(
                "before\n<!-- BEGIN CLI REFERENCE -->\nold\n<!-- END CLI REFERENCE -->\nafter",
                encoding="utf-8",
            )
            readme.chmod(0o644)
            original_inode = readme.stat().st_ino
            self.docs.README = readme

            self.docs._update_readme("new docs")

            updated_stat = readme.stat()
            self.assertEqual(
                readme.read_text(encoding="utf-8"),
                "before\n<!-- BEGIN CLI REFERENCE -->\n\nnew docs\n\n<!-- END CLI REFERENCE -->\nafter",
            )
            self.assertNotEqual(updated_stat.st_ino, original_inode)
            self.assertEqual(updated_stat.st_mode & 0o777, 0o644)
            self.assertEqual(list(readme.parent.glob(f".{readme.name}.*.tmp")), [])

    def test_update_readme_rejects_missing_or_duplicate_markers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            readme = Path(tmp) / "README.md"
            self.docs.README = readme
            readme.write_text("no markers", encoding="utf-8")

            with self.assertRaisesRegex(SystemExit, "marker pair"):
                self.docs._update_readme("docs")

            readme.write_text(
                "<!-- BEGIN CLI REFERENCE --><!-- BEGIN CLI REFERENCE --><!-- END CLI REFERENCE -->",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(SystemExit, "only one begin"):
                self.docs._update_readme("docs")

    def test_update_readme_exits_with_path_on_read_failure(self) -> None:
        read_error = PermissionError("denied")
        readme = mock.Mock()
        readme.read_text.side_effect = read_error
        self.docs.README = readme

        with self.assertRaisesRegex(SystemExit, r"Failed to read .*denied") as raised:
            self.docs._update_readme("docs")

        self.assertIs(raised.exception.__cause__, read_error)

    def test_replace_text_exits_with_path_and_preserves_replace_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            readme = Path(tmp) / "README.md"
            readme.write_text("old", encoding="utf-8")
            replace_error = PermissionError("blocked")

            with mock.patch.object(self.docs.os, "replace", side_effect=replace_error):
                with mock.patch.object(
                    Path, "unlink", side_effect=OSError("cleanup failed")
                ):
                    with self.assertRaisesRegex(
                        SystemExit, rf"Failed to atomically replace {readme}: blocked"
                    ) as raised:
                        self.docs._replace_text(readme, "new")

            self.assertIs(raised.exception.__cause__, replace_error)

    def test_update_readme_skips_write_when_content_is_unchanged(self) -> None:
        content = "before\n<!-- BEGIN CLI REFERENCE -->\n\ndocs\n\n<!-- END CLI REFERENCE -->\nafter"
        readme = mock.Mock()
        readme.read_text.return_value = content
        self.docs.README = readme

        with mock.patch.object(self.docs, "_replace_text") as replace:
            self.docs._update_readme("docs")

        replace.assert_not_called()

    def test_write_card_svg_translates_click_errors(self) -> None:
        from rich_card import cli

        error = click.ClickException("bad sample")
        with mock.patch.object(cli, "app", side_effect=error):
            with self.assertRaisesRegex(
                SystemExit, "Failed to generate sample SVG: bad sample"
            ) as raised:
                self.docs._write_card_svg()

        self.assertIs(raised.exception.__cause__, error)

    def test_main_generates_cli_docs_writes_svg_then_updates_readme(self) -> None:
        calls = []

        def run(command, env):
            calls.append(("run", command, env))
            return "# rich-card\n\nbody"

        def write_card_svg():
            calls.append(("write_card_svg",))

        def update_readme(cli_docs):
            calls.append(("update_readme", cli_docs))

        with mock.patch.object(self.docs, "_run", side_effect=run):
            with mock.patch.object(
                self.docs, "_write_card_svg", side_effect=write_card_svg
            ):
                with mock.patch.object(
                    self.docs, "_update_readme", side_effect=update_readme
                ):
                    self.docs.main()

        self.assertEqual(calls[0][0], "run")
        self.assertEqual(calls[1], ("write_card_svg",))
        self.assertEqual(calls[2], ("update_readme", "### rich-card\n\nbody"))
        self.assertEqual(calls[0][1][1:4], ["-m", "typer", "--app"])
        self.assertIn(str(self.docs.SOURCE), calls[0][2]["PYTHONPATH"])
        self.assertEqual(
            calls[0][2]["XDG_CONFIG_HOME"], str(self.docs.ROOT / ".generated-config")
        )


if __name__ == "__main__":
    unittest.main()
