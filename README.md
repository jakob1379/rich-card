rich-cards
==========

Render syntax-highlighted code as a polished terminal card on a gradient SVG
background. The CLI uses Typer for commands and an in-process Pygments style
based on bat's Monokai Extended colors.

```bash
printf 'def hello():\n    return "world"\n' \
  | rich-cards --lexer python --theme monokai-extended --title hello.py -o card.svg
```

Inline content works well for one-off cards:

```bash
rich-cards \
  --content $'TAX_RATES = {"CA": 0.0825, "NY": 0.05}\n\nprint(TAX_RATES)' \
  --lexer python \
  --theme monokai-extended \
  --caption "clean code card" \
  --background aurora \
  --line-numbers \
  -o tax-card.svg
```

Useful commands:

```bash
rich-cards --list-themes
rich-cards src/example.py --theme monokai-extended -o example.svg
nix develop -c uv run rich-cards --content 'print("hi")' -o card.svg
```

Background presets include `aurora`, `blue-raspberry`, `cosmic-lumen`,
`dusty-grass`, `electric-twilight`, `megatron`, `night-fade`, `nordic`,
`prism`, `rainy-ashville`, `sublime-light`, `tempting-azure`, `warm-flame`,
and `winter-neva`.
