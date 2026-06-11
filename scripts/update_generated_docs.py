from __future__ import annotations

import os
import subprocess  # nosec B404 - runs fixed local commands for docs generation.
import sys
import tempfile
from contextlib import suppress
from pathlib import Path

import click


ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
SOURCE = ROOT / "src"
GENERATED_CARD = ROOT / "docs" / "assets" / "card.svg"
COMMAND_TIMEOUT_SECONDS = 30
BEGIN_CLI_REFERENCE = "<!-- BEGIN CLI REFERENCE -->"
END_CLI_REFERENCE = "<!-- END CLI REFERENCE -->"


def main() -> None:
    env = os.environ.copy()
    env.setdefault("UV_CACHE_DIR", str(ROOT / ".uv-cache"))
    env["XDG_CONFIG_HOME"] = str(ROOT / ".generated-config")
    env["PYTHONPATH"] = _pythonpath(env)

    cli_docs = _run(
        [
            sys.executable,
            "-m",
            "typer",
            "--app",
            "app",
            "rich_card.cli",
            "utils",
            "docs",
            "--name",
            "rich-card",
        ],
        env,
    )
    _write_card_svg()
    _update_readme(_demote_heading(cli_docs))


def _pythonpath(env: dict[str, str]) -> str:
    existing = env.get("PYTHONPATH")
    if existing:
        return f"{SOURCE}{os.pathsep}{existing}"
    return str(SOURCE)


def _write_card_svg() -> None:
    GENERATED_CARD.parent.mkdir(parents=True, exist_ok=True)
    old_sys_path = list(sys.path)
    sys.path.insert(0, str(SOURCE))
    from rich_card.cli import app

    old_xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
    os.environ["XDG_CONFIG_HOME"] = str(ROOT / ".generated-config")
    try:
        app(
            args=[str(ROOT / "pyproject.toml"), "--output", str(GENERATED_CARD)],
            prog_name="rich-card",
            standalone_mode=False,
        )
    except (click.ClickException, click.Abort) as exc:
        raise SystemExit(f"Failed to generate sample SVG: {exc}") from exc
    finally:
        if old_xdg_config_home is None:
            os.environ.pop("XDG_CONFIG_HOME", None)
        else:
            os.environ["XDG_CONFIG_HOME"] = old_xdg_config_home
        sys.path[:] = old_sys_path


def _run(command: list[str], env: dict[str, str]) -> str:
    try:
        result = subprocess.run(
            command,
            cwd=ROOT,
            env=env,
            text=True,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=COMMAND_TIMEOUT_SECONDS,
        )  # nosec B603 - command is a fixed internal list, not user input.
    except subprocess.TimeoutExpired as error:
        if error.stdout:
            sys.stderr.write(
                error.stdout if isinstance(error.stdout, str) else error.stdout.decode()
            )
        if error.stderr:
            sys.stderr.write(
                error.stderr if isinstance(error.stderr, str) else error.stderr.decode()
            )
        raise SystemExit(
            f"Command timed out after {COMMAND_TIMEOUT_SECONDS} seconds: {' '.join(command)}"
        ) from error
    if result.returncode == 0:
        return result.stdout

    sys.stderr.write(result.stdout)
    sys.stderr.write(result.stderr)
    raise SystemExit(result.returncode)


def _demote_heading(markdown: str) -> str:
    lines = markdown.strip().splitlines()
    if lines and lines[0].startswith("# "):
        lines[0] = "### " + lines[0][2:]
    return "\n".join(lines).strip()


def _update_readme(cli_docs: str) -> None:
    try:
        readme = README.read_text(encoding="utf-8")
    except OSError as error:
        raise SystemExit(f"Failed to read {README}: {error}") from error
    begin_index = readme.find(BEGIN_CLI_REFERENCE)
    end_index = readme.find(END_CLI_REFERENCE)
    if begin_index == -1 or end_index == -1 or begin_index > end_index:
        raise SystemExit("Expected one ordered CLI reference marker pair in README.md.")
    if readme.find(BEGIN_CLI_REFERENCE, begin_index + 1) != -1:
        raise SystemExit("Expected only one begin CLI reference marker in README.md.")
    if readme.find(END_CLI_REFERENCE, end_index + 1) != -1:
        raise SystemExit("Expected only one end CLI reference marker in README.md.")

    prefix = readme[: begin_index + len(BEGIN_CLI_REFERENCE)].rstrip()
    suffix = readme[end_index:].lstrip()
    updated = f"{prefix}\n\n{cli_docs}\n\n{suffix}"
    if updated != readme:
        _replace_text(README, updated)


def _replace_text(path: Path, content: str) -> None:
    temp_path: Path | None = None
    try:
        mode = path.stat().st_mode & 0o777
        with tempfile.NamedTemporaryFile(
            "w",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            encoding="utf-8",
            delete=False,
        ) as temp_file:
            temp_path = Path(temp_file.name)
            temp_file.write(content)
            temp_file.flush()
            os.fsync(temp_file.fileno())
        temp_path.chmod(mode)
        os.replace(temp_path, path)
    except OSError as error:
        raise SystemExit(f"Failed to atomically replace {path}: {error}") from error
    finally:
        if temp_path is not None and temp_path.exists():
            with suppress(OSError):
                temp_path.unlink()


if __name__ == "__main__":
    main()
