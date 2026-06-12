# rich-card

Render syntax-highlighted code, terminal output, and images as polished SVG
terminal cards on gradient backgrounds. The CLI uses Typer for commands and an
in-process Pygments style based on bat's Monokai Extended colors.

![Rendered rich-card example](docs/assets/card.svg)

## Quick Start

Render a source file or inline snippet:

```bash
rich-card pyproject.toml
rich-card --content 'print("hi")' --lexer python -o hello.svg
```

Piped terminal output is read from stdin. ANSI colors are preserved, and eza
icons render when a Nerd Font such as Symbols Nerd Font Mono is installed:

```bash
eza --tree --icons=always --git-ignore --colour=always src/ | rich-card --title tree -o tree.svg
```

Images can be framed in the same card style:

```bash
rich-card --image screenshot.png --title "Build result" --inner-padding 24 -o screenshot-card.svg
```

Cards auto-size to their content by default. Pass `--width` when you want a
fixed canvas width. Use `--padding` for the outer gradient margin and
`--inner-padding` for the padding inside the terminal card:

```bash
rich-card --content 'print("hi")' --width 1080 --padding 80 --inner-padding 32 -o fixed-card.svg
```

## Configuration

Defaults can be set in `$XDG_CONFIG_HOME/rich-card/config.json`, falling back to
`~/.config/rich-card/config.json`. Explicit CLI options always override
configured defaults.

```json
{
  "output": "card.svg",
  "card": {
    "theme": "monokai-extended",
    "logo": "logo.svg",
    "logo_placement": "both",
    "background": "aurora",
    "padding": 72,
    "inner_padding": 30,
    "radius": 12,
    "line_numbers": false,
    "word_wrap": false,
    "tab_size": 2
  },
  "renderer": {
    "card_fill": "#26282b",
    "card_stroke": "#3b3e43",
    "code_font_stack": "'JetBrains Mono', 'Cascadia Code', monospace",
    "logo_bar_max_height": 26,
    "logo_bar_max_width": 120,
    "logo_bar_right_padding": 22,
    "logo_watermark_width_ratio": 0.45,
    "logo_watermark_opacity": 0.14
  }
}
```

The `card` section covers CLI defaults and `renderer` covers scalar SVG
presentation defaults that are intentionally not exposed as CLI flags.

## Generated Assets

`docs/assets/card.svg` can be regenerated with:

```bash
uv run python scripts/update_generated_docs.py
```

The Nix development shell installs a pre-commit hook that refreshes
`docs/assets/card.svg` and the CLI reference before each commit:

```bash
uv run python scripts/update_generated_docs.py
```

## CLI Reference

<!-- BEGIN CLI REFERENCE -->

### `rich-card`

**Usage**:

```console
$ rich-card [OPTIONS] [SOURCE]
```

**Arguments**:

- `[SOURCE]`: Optional source file. Omit to read from stdin.

**Options**:

- `-c, --content TEXT`: Inline code content. Takes precedence over SOURCE.
- `--image FILE`: Image file to render inside the card. Supports PNG, JPEG, and
  SVG.
- `-o, --output FILE`: SVG file to write. [default: card.svg]
- `-l, --lexer TEXT`: Pygments lexer name. Defaults to source filename
  inference, or ANSI-aware plain text for stdin.
- `-s, --theme TEXT`: Pygments theme name. See `rich-card --list-themes`.
  [default: monokai-extended]
- `-t, --title TEXT`: Optional card title shown in the card chrome.
- `--logo FILE`: Logo image to place in the title bar, terminal background, or
  both. Supports PNG, JPEG, and SVG.
- `--logo-placement [bar|watermark|both]`: Where to render --logo. [default:
  bar]
- `-b, --background TEXT`: Background option. See
  `rich-card --list-backgrounds`. [default: aurora]
- `-w, --width INTEGER RANGE`: Fixed SVG canvas width in pixels.
  [520&lt;=x&lt;=2400]
- `-p, --padding INTEGER RANGE`: Background padding outside the terminal card in
  pixels. [default: 72; 24&lt;=x&lt;=240]
- `--inner-padding INTEGER RANGE`: Padding inside the terminal card around the
  content or image. [0&lt;=x&lt;=160]
- `-r, --radius INTEGER RANGE`: Rounded card corner radius in pixels. [default:
  12; 4&lt;=x&lt;=80]
- `-n, --line-numbers / --no-line-numbers`: Show line numbers. [default:
  no-line-numbers]
- `-W, --word-wrap / --no-word-wrap`: Wrap long lines inside the card. [default:
  no-word-wrap]
- `-T, --tab-size INTEGER RANGE`: Tab expansion width. [default: 2;
  1&lt;=x&lt;=12]
- `--list-themes`: List syntax themes and exit.
- `--list-backgrounds`: List background options and exit.
- `--help`: Show this message and exit.

<!-- END CLI REFERENCE -->
