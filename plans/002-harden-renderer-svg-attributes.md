# Plan 002: Harden renderer SVG attribute values

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the next
> step. If anything in the "STOP conditions" section occurs, stop and report.
> When done, update the status row for this plan in `plans/README.md` unless a
> reviewer dispatched you and told you they maintain the index.
>
> **Drift check (run first)**:
> `git diff --stat 227bfe9..HEAD -- src/rich_card/config.py src/rich_card/svg.py src/rich_card/svg_markup.py tests/test_config.py tests/test_svg.py tests/test_svg_text.py tests/test_cli_config.py && git diff --stat -- src/rich_card/config.py src/rich_card/svg.py src/rich_card/svg_markup.py tests/test_config.py tests/test_svg.py tests/test_svg_text.py tests/test_cli_config.py`
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

`rich-card` accepts renderer presentation defaults from
`$XDG_CONFIG_HOME/rich-card/config.json`. Those values are currently type
checked, but several strings are interpolated directly into SVG attributes. A
malicious or accidentally malformed config value can break out of attributes in
the generated SVG. The fix should preserve legitimate renderer customization
while validating colors and escaping or validating font-family attributes.

## Current state

- `src/rich_card/config.py` parses JSON config and validates shape/ranges.
- `src/rich_card/svg.py` validates renderer numeric fields and emits card-level
  SVG attributes.
- `src/rich_card/svg_markup.py` emits code text and tspan attributes.
- `tests/test_config.py`, `tests/test_svg.py`, `tests/test_svg_text.py`, and
  `tests/test_cli_config.py` cover config and SVG rendering behavior.

Renderer string config uses generic non-empty string validation:

```python
# src/rich_card/config.py:203-237
return RendererConfig(
    card_fill=_optional_str(path, "renderer.card_fill", raw.get("card_fill")),
    card_stroke=_optional_str(path, "renderer.card_stroke", raw.get("card_stroke")),
    muted_text=_optional_str(path, "renderer.muted_text", raw.get("muted_text")),
    default_text=_optional_str(
        path, "renderer.default_text", raw.get("default_text")
    ),
    ...
    code_font_stack=_optional_str(
        path, "renderer.code_font_stack", raw.get("code_font_stack")
    ),
```

```python
# src/rich_card/config.py:304-311
def _optional_str(path: Path, name: str, value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ConfigError(f"{path}: {name} must be a string.")
    if not value:
        raise ConfigError(f"{path}: {name} must be a non-empty string.")
    return value
```

Card fill/stroke are emitted directly:

```python
# src/rich_card/svg.py:371-375
parts.extend(
    [
        f'<rect x="{card_x}" y="{card_y}" width="{_number(card_width)}" height="{_number(card_height)}" '
        f'rx="{options.radius}" fill="{renderer.card_fill}" '
        f'stroke="{renderer.card_stroke}" stroke-width="3"{filter_attr}/>',
```

Title and logo font families are emitted directly:

```python
# src/rich_card/svg.py:611-616
label = (
    f'<text x="{x + width / 2:.1f}" y="{y + 31}" '
    f'font-family="{renderer.chrome_font_stack}" font-size="13" '
    'text-anchor="middle" clip-path="url(#title-clip)">'
    f"{_inline_tspans(title, renderer.muted_text, renderer)}"
    "</text>"
)
```

Code text and tspan attributes are emitted directly:

```python
# src/rich_card/svg_markup.py:19-22
output.append(
    f'<text x="{x}" y="{line_y}" font-family="{renderer.code_font_stack}" '
    f'font-size="{renderer.font_size}" xml:space="preserve">'
    f"{''.join(spans)}</text>"
)
```

```python
# src/rich_card/svg_markup.py:90-109
def _tspan(text: str, fragment: Fragment, mode: str, renderer: RendererDefaults) -> str:
    if mode == "emoji":
        attrs = [
            f'font-family="{renderer.emoji_font_stack}"',
            'style="font-variant-emoji: emoji;"',
        ]
    elif mode == "icon":
        attrs = [
            f'fill="{fragment.color}"',
            f'font-family="{renderer.icon_font_stack}"',
        ]
    else:
        attrs = [f'fill="{fragment.color}"']
```

Existing tests validate type/shape, but not SVG attribute safety:

```python
# tests/test_config.py:44-48
def test_rejects_renderer_string_type_failure(self) -> None:
    self.assert_config_error(
        {"renderer": {"card_fill": 123}},
        "renderer.card_fill must be a string",
    )
```

```python
# tests/test_svg.py:251-258
def test_render_code_card_svg_rejects_invalid_renderer_defaults(self) -> None:
    with self.assertRaisesRegex(
        InvalidRendererOptionError, "renderer.char_width must be finite"
    ):
```

## Commands you will need

| Purpose       | Command                                                                                                  | Expected on success           |
| ------------- | -------------------------------------------------------------------------------------------------------- | ----------------------------- |
| Unit tests    | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m unittest discover`                                   | exits 0, all tests pass       |
| Config tests  | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m unittest tests.test_config tests.test_cli_config -v` | exits 0                       |
| SVG tests     | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m unittest tests.test_svg tests.test_svg_text -v`      | exits 0                       |
| Lint          | `ruff check .`                                                                                           | exits 0, no findings          |
| Format check  | `ruff format --check .`                                                                                  | exits 0, already formatted    |
| Security scan | `bandit -c pyproject.toml -r src scripts`                                                                | exits 0, no issues identified |

## Scope

**In scope**:

- `src/rich_card/config.py`
- `src/rich_card/svg.py`
- `src/rich_card/svg_markup.py`
- `tests/test_config.py`
- `tests/test_cli_config.py`
- `tests/test_svg.py`
- `tests/test_svg_text.py`

**Out of scope**:

- `src/rich_card/runtime.py` and command execution. That belongs to plan 001.
- Changing public config key names.
- Removing renderer customization entirely.
- Generated docs/assets unless a validation command explicitly regenerates them.
- Dependency updates.

## Git workflow

- Branch: `advisor/002-harden-renderer-svg-attributes`
- Commit style: Conventional Commits, matching recent history such as
  `fix(svg): tighten renderer validation`.
- Do not push or open a PR unless the operator explicitly instructs it.
- Preserve unrelated dirty worktree changes.

## Steps

### Step 1: Validate renderer color fields as hex colors at config load

In `src/rich_card/config.py`, stop using `_optional_str(...)` for these fields:

- `renderer.card_fill`
- `renderer.card_stroke`
- `renderer.muted_text`
- `renderer.default_text`

Introduce an `_optional_hex_color(path, name, value)` helper that:

- Returns `None` for missing values.
- Reuses the same type and non-empty checks as `_optional_str(...)`.
- Requires `_is_hex_color(parsed)`.
- Returns the lowercase `#rrggbb` string.
- Raises `ConfigError(f"{path}: {name} must be a #rrggbb hex color.")` on
  invalid color syntax.

Keep `_optional_ansi_palette(...)` on the same hex-color rules.

**Verify**:
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m unittest tests.test_config -v`
-> config tests pass, including new invalid-color tests.

### Step 2: Validate renderer color fields for direct API use

Config validation does not protect callers who instantiate
`RendererDefaults(...)` directly. In `src/rich_card/svg.py`, extend
`_validate_renderer_defaults(...)` so direct renderer objects also reject unsafe
color strings.

Validate:

- `card_fill`
- `card_stroke`
- `muted_text`
- `default_text`
- every item in `ansi_palette`

Use the same `#rrggbb` rule. It is acceptable to duplicate a tiny local
`_is_hex_color(...)` helper in `svg.py` rather than importing a private config
helper into rendering. Preserve existing `InvalidRendererOptionError` behavior
and add clear messages such as `renderer.card_fill must be a #rrggbb hex color`.

**Verify**:
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m unittest tests.test_svg -v`
-> SVG option validation tests pass, including new direct-API invalid-color
tests.

### Step 3: Escape font-family attribute values

In `src/rich_card/svg.py` and `src/rich_card/svg_markup.py`, ensure renderer
font stack strings are escaped with XML attribute quoting before interpolation
into `font-family="..."`.

Fields to cover:

- `renderer.code_font_stack`
- `renderer.chrome_font_stack`
- `renderer.emoji_font_stack`
- `renderer.icon_font_stack`

`ui_font_stack` and `emoji_text_fallback_stack` are currently not emitted by the
searched code paths, but if you find an emission site while implementing, apply
the same escaping there.

Suggested implementation:

- Import or use `html.escape(value, quote=True)`.
- Add a small helper such as `_svg_attr(value: str) -> str`.
- Use that helper at every `font-family="{...}"` interpolation site.
- Do not escape SVG text content with this helper; `_escape_xml_text(...)`
  already handles text nodes.

**Verify**:
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m unittest tests.test_svg tests.test_svg_text -v`
-> SVG tests pass.

### Step 4: Add injection regression tests

Add tests that would fail on the current implementation:

- In `tests/test_config.py`, reject invalid color config such as
  `{"renderer": {"card_fill": "#111111\" data-x=\"1"}}`.
- In `tests/test_svg.py`, reject direct `RendererDefaults(card_fill=...)` with
  invalid color syntax.
- In `tests/test_svg_text.py` or `tests/test_svg.py`, verify a malicious font
  stack cannot create a second SVG attribute. Example assertion shape: render
  with `RendererDefaults(code_font_stack='Mono" data-x="1')`, then assert the
  output does not contain `data-x="1"` and does contain an escaped attribute
  representation such as `Mono&quot; data-x=&quot;1`.
- In `tests/test_cli_config.py`, add an end-to-end config test that invalid
  renderer color config exits non-zero and reports the `#rrggbb` error.

Keep tests small and deterministic. Do not use browser rendering or image
conversion for this plan.

**Verify**:
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m unittest tests.test_config tests.test_cli_config tests.test_svg tests.test_svg_text -v`
-> all targeted tests pass.

### Step 5: Run the full validation lane

Run the repo checks:

1. `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m unittest discover`
2. `ruff check .`
3. `ruff format --check .`
4. `bandit -c pyproject.toml -r src scripts`

**Verify**: all commands exit 0.

## Test plan

- Add config-boundary tests in `tests/test_config.py` and
  `tests/test_cli_config.py`.
- Add renderer-direct tests in `tests/test_svg.py`.
- Add font attribute escaping tests in `tests/test_svg_text.py` or
  `tests/test_svg.py`, following the existing SVG string-assertion style.
- Full verification is the commands in Step 5.

## Done criteria

- [ ] Renderer color config fields accept only `#rrggbb` values and normalize to
      lowercase.
- [ ] Direct `RendererDefaults(...)` renderer objects reject unsafe color fields
      before SVG is emitted.
- [ ] Font-family attributes are escaped with `quote=True`.
- [ ] Regression tests prove a quote-bearing config/direct value cannot create a
      new SVG attribute.
- [ ] `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m unittest discover`
      exits 0.
- [ ] `ruff check .` exits 0.
- [ ] `ruff format --check .` exits 0.
- [ ] `bandit -c pyproject.toml -r src scripts` exits 0.
- [ ] No files outside the in-scope list are modified, except `plans/README.md`
      status updates.

## STOP conditions

Stop and report back if:

- The project intentionally supports non-hex color expressions in renderer
  config that are documented or tested outside the excerpts above.
- Escaping font-family values breaks existing default font stack rendering tests
  and the break cannot be fixed at the attribute-escaping boundary.
- The fix requires renaming public config keys.
- The fix requires changing image data URI handling or SVG image parsing.
- Any validation command fails twice after a reasonable fix attempt.

## Maintenance notes

Reviewers should focus on every SVG attribute interpolation that includes
renderer-provided strings. Future renderer options that emit strings into SVG
attributes should either use strict value validation,
`html.escape(..., quote=True)`, or both, depending on whether the SVG attribute
has a narrow grammar.
