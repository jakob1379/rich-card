rich-card
=========

Render syntax-highlighted code as a polished terminal card on a gradient SVG
background. The CLI uses Typer for commands and an in-process Pygments style
based on bat's Monokai Extended colors.

```bash
printf 'def hello():\n    return "world"\n' \
  | rich-card --lexer python --theme monokai-extended --title hello.py -o card.svg
```

Piped terminal output is read from stdin, ANSI colors are preserved, and eza
icons render when a Nerd Font such as Symbols Nerd Font Mono is installed:

```bash
eza --tree --icons=always --git-ignore --colour=always src/ | rich-card --title tree -o tree.svg
```

Inline content works well for one-off cards:

```bash
rich-card \
  --content $'TAX_RATES = {"CA": 0.0825, "NY": 0.05}\n\nprint(TAX_RATES)' \
  --lexer python \
  --theme monokai-extended \
  --caption "clean code card" \
  --background aurora \
  --line-numbers \
  -o tax-card.svg
```

Images can be framed in the same card style:

```bash
rich-card --image screenshot.png --title "Build result" --caption "latest run" -o screenshot-card.svg
```

Useful commands:

```bash
rich-card --list-themes
rich-card src/example.py --theme monokai-extended -o example.svg
nix develop -c uv run rich-card --content 'print("hi")' -o card.svg
```

Background presets include `aurora`, `blue-raspberry`, `cosmic-lumen`,
`dusty-grass`, `electric-twilight`, `megatron`, `night-fade`, `nordic`,
`prism`, `rainy-ashville`, `sublime-light`, `tempting-azure`, `warm-flame`,
and `winter-neva`.
