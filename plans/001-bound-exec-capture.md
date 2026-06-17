# Plan 001: Bound `--exec` command capture

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the next
> step. If anything in the "STOP conditions" section occurs, stop and report.
> When done, update the status row for this plan in `plans/README.md` unless a
> reviewer dispatched you and told you they maintain the index.
>
> **Drift check (run first)**:
> `git diff --stat 227bfe9..HEAD -- src/rich_card/runtime.py tests/test_runtime.py && git diff --stat -- src/rich_card/runtime.py tests/test_runtime.py`
>
> This plan was written against commit `227bfe9` plus an already-dirty worktree.
> If either command shows changes, compare the "Current state" excerpts against
> the live code before proceeding; on a mismatch, treat it as a STOP condition.

## Status

- **Priority**: P1
- **Effort**: M
- **Risk**: MED
- **Depends on**: none
- **Category**: security
- **Planned at**: commit `227bfe9`, 2026-06-16

## Why this matters

The `rich-card --exec` feature intentionally runs a user-provided shell command,
but the capture path currently has no timeout and no output cap. A command that
never exits can hang the CLI, and a command that streams output can grow memory
and generate very large SVG content. The fix should keep the documented `--exec`
behavior while bounding the resource cost of accidental or hostile commands.

## Current state

- `src/rich_card/runtime.py` owns input dispatch and command capture.
- `tests/test_runtime.py` contains runtime-level tests for `--exec`.
- The repo is a Python 3.14 CLI using Typer, unittest, Ruff, and Bandit.
- Existing security comments say shell execution is intentional for explicit
  user-requested `--exec` commands. Do not remove `--exec` or replace shell
  semantics unless the maintainer explicitly asks for that product change.

Current capture flow:

```python
# src/rich_card/runtime.py:96-111
def _read_command(command: str) -> str:
    env = os.environ.copy()
    env.pop("NO_COLOR", None)
    env.update(
        {
            "CLICOLOR_FORCE": "1",
            "FORCE_COLOR": "1",
            "COLORTERM": env.get("COLORTERM", "truecolor"),
            "GIT_PAGER": "cat",
            "PAGER": "cat",
            "BAT_PAGER": "cat",
            "TERM": _color_term(env),
        }
    )
    output = _capture_command_output(command, env)
    return _command_transcript(command, output)
```

Pipe capture has no timeout:

```python
# src/rich_card/runtime.py:127-140
def _capture_command_output_pipe(command: str, env: dict[str, str]) -> str:
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
    return result.stdout
```

PTY capture loops until the process exits and accumulates every chunk:

```python
# src/rich_card/runtime.py:143-166
def _capture_command_output_pty(command: str, env: dict[str, str]) -> str:
    master_fd, slave_fd = pty.openpty()
    try:
        _set_pty_size(slave_fd, env)
        process = subprocess.Popen(  # nosec B602 - --exec intentionally runs user shell input.
            command,
            shell=True,
            executable=env.get("SHELL") or None,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=slave_fd,
            stderr=slave_fd,
            close_fds=True,
        )
        os.close(slave_fd)
        slave_fd = -1
        output = _read_pty_output(master_fd, process)
    finally:
        with suppress(OSError):
            os.close(master_fd)
        if slave_fd >= 0:
            with suppress(OSError):
                os.close(slave_fd)
    return output.decode("utf-8", errors="replace")
```

```python
# src/rich_card/runtime.py:180-186
def _read_pty_output(master_fd: int, process: subprocess.Popen[bytes]) -> bytes:
    chunks: list[bytes] = []
    while process.poll() is None:
        _read_available_pty_output(master_fd, chunks, timeout=0.05)
    _read_available_pty_output(master_fd, chunks, timeout=0)
    process.wait()
    return b"".join(chunks)
```

Existing tests assert the color-forcing environment and PTY behavior:

```python
# tests/test_runtime.py:70-88
def test_render_card_exec_forces_color_environment(self) -> None:
    with mock.patch(
        "rich_card.runtime._capture_command_output", return_value="out"
    ) as capture:
        output = render_card(None, None, "show colors", self.settings())
```

```python
# tests/test_runtime.py:90-102
def test_render_card_exec_captures_tty_color_output(self) -> None:
    command = (
        "python -c 'import sys; "
        'print("\\033[31mtty\\033[0m" if sys.stdout.isatty() else "plain")'
        "'"
    )
```

## Commands you will need

| Purpose       | Command                                                                             | Expected on success           |
| ------------- | ----------------------------------------------------------------------------------- | ----------------------------- |
| Unit tests    | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m unittest discover`              | exits 0, all tests pass       |
| Runtime tests | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m unittest tests.test_runtime -v` | exits 0, runtime tests pass   |
| Lint          | `ruff check .`                                                                      | exits 0, no findings          |
| Format check  | `ruff format --check .`                                                             | exits 0, already formatted    |
| Security scan | `bandit -c pyproject.toml -r src scripts`                                           | exits 0, no issues identified |

## Scope

**In scope**:

- `src/rich_card/runtime.py`
- `tests/test_runtime.py`

**Out of scope**:

- `src/rich_card/cli.py` command-line options. Do not add public flags for this
  plan.
- `src/rich_card/svg.py`, `src/rich_card/svg_markup.py`, and config validation.
  Those belong to plan 002.
- Any change that removes shell execution for `--exec`. It is a documented,
  explicit user feature.
- Generated docs/assets.

## Git workflow

- Branch: `advisor/001-bound-exec-capture`
- Commit style: Conventional Commits, matching recent history such as
  `feat(cli): add terminal capture and watermark`.
- Do not push or open a PR unless the operator explicitly instructs it.
- Preserve unrelated dirty worktree changes. If files in scope already contain
  user changes, work with them rather than reverting them.

## Steps

### Step 1: Add resource-limit constants and errors

In `src/rich_card/runtime.py`, add module-level constants near `COMMAND_PROMPT`:

- `COMMAND_TIMEOUT_SECONDS = 30.0`
- `COMMAND_OUTPUT_LIMIT_BYTES = 4 * 1024 * 1024`

Use `RenderRuntimeError` for both timeout and output-limit failures. Error
messages should be stable and user-facing, for example:

- `Command timed out after 30 seconds.`
- `Command output exceeded 4194304 bytes.`

Do not include the command string in these errors; commands can contain secrets
or sensitive local paths.

**Verify**:
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m unittest tests.test_runtime -v`
-> existing tests still pass.

### Step 2: Bound the non-POSIX pipe path

Update `_capture_command_output_pipe(...)` so the subprocess cannot run forever
and the returned output is capped.

Acceptable implementation shape:

- Keep `shell=True` and the existing `# nosec B602` explanation.
- Pass `timeout=COMMAND_TIMEOUT_SECONDS` to `subprocess.run(...)`.
- Catch `subprocess.TimeoutExpired` and raise `RenderRuntimeError` without
  echoing captured output.
- After completion, measure `result.stdout.encode("utf-8", errors="replace")`.
  If it exceeds `COMMAND_OUTPUT_LIMIT_BYTES`, raise `RenderRuntimeError`.

This does not perfectly prevent memory growth before `subprocess.run` returns on
non-POSIX systems, but it gives the fallback path a timeout and a consistent
user-facing limit. The POSIX PTY path is the primary runtime path for this repo.

**Verify**: add or update tests in `tests/test_runtime.py`, then run
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m unittest tests.test_runtime -v`
-> tests for pipe timeout and pipe output-limit behavior pass.

### Step 3: Bound the POSIX PTY path

Update `_capture_command_output_pty(...)`, `_read_pty_output(...)`, and
`_read_available_pty_output(...)` so PTY capture:

- Starts the shell in its own process group on POSIX, for example
  `start_new_session=True` in `subprocess.Popen(...)`.
- Tracks a monotonic deadline using `time.monotonic()`.
- Kills the process group on timeout with
  `os.killpg(process.pid, signal.SIGKILL)` when available, falling back to
  `process.kill()` if needed.
- Tracks total bytes read as chunks arrive.
- Kills the process and raises `RenderRuntimeError` as soon as the byte limit is
  exceeded.
- Always closes `master_fd` and `slave_fd` as the current code already does.

Keep the existing PTY behavior that makes `sys.stdout.isatty()` true for
captured commands.

**Verify**:
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m unittest tests.test_runtime -v`
-> existing PTY color test and new timeout/output-limit tests pass.

### Step 4: Add regression tests

In `tests/test_runtime.py`, add focused tests for:

- `_capture_command_output_pipe(...)` raises `RenderRuntimeError` on
  `subprocess.TimeoutExpired`. Mock `rich_card.runtime.subprocess.run`; do not
  sleep in the test.
- `_capture_command_output_pipe(...)` raises `RenderRuntimeError` when stdout
  exceeds `COMMAND_OUTPUT_LIMIT_BYTES`. Mock the run result; do not allocate a
  huge string if you can temporarily patch the limit smaller.
- POSIX PTY timeout: if the implementation exposes a helper for timeout
  handling, test that helper directly with a fake process; otherwise use a very
  short patched `COMMAND_TIMEOUT_SECONDS` and a command that sleeps. Skip this
  test on non-POSIX systems with `unittest.skipUnless(os.name == "posix", ...)`.
- POSIX PTY output cap: patch `COMMAND_OUTPUT_LIMIT_BYTES` to a small value and
  run a command that prints more than the limit. Skip on non-POSIX systems.

Avoid slow tests. The timeout test should complete in well under one second by
patching the timeout constant to a tiny value such as `0.05`.

**Verify**:
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m unittest tests.test_runtime -v`
-> all runtime tests pass quickly.

### Step 5: Run the full validation lane

Run the repo checks:

1. `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m unittest discover`
2. `ruff check .`
3. `ruff format --check .`
4. `bandit -c pyproject.toml -r src scripts`

**Verify**: all commands exit 0.

## Test plan

- Extend `tests/test_runtime.py`; follow the existing `RenderRuntimeTest`
  structure and `unittest.mock` style.
- Cover timeout and output-limit behavior for the pipe path.
- Cover timeout and output-limit behavior for the POSIX PTY path, skipping those
  tests when `os.name != "posix"`.
- Preserve existing `test_render_card_exec_captures_tty_color_output`.

## Done criteria

- [ ] Commands that never exit produce a `RenderRuntimeError` instead of
      hanging.
- [ ] Commands that exceed the byte limit produce a `RenderRuntimeError` before
      rendering SVG.
- [ ] Existing `--exec` color/TTY behavior still works.
- [ ] `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m unittest discover`
      exits 0.
- [ ] `ruff check .` exits 0.
- [ ] `ruff format --check .` exits 0.
- [ ] `bandit -c pyproject.toml -r src scripts` exits 0.
- [ ] No files outside the in-scope list are modified, except `plans/README.md`
      status updates.

## STOP conditions

Stop and report back if:

- `src/rich_card/runtime.py` does not contain the PTY capture functions shown in
  the excerpts. That means the current dirty worktree state changed or was not
  present.
- The fix requires adding public CLI options.
- Killing the process group breaks the existing PTY color test and cannot be
  fixed without removing PTY capture.
- A timeout or output-limit error would need to include the full command string
  or captured output.
- Any validation command fails twice after a reasonable fix attempt.

## Maintenance notes

Reviewers should scrutinize process cleanup: child processes must not survive a
timeout. Future work may add public timeout/output-limit flags, but this plan
intentionally keeps the first hardening pass internal and conservative.
