from __future__ import annotations

from dataclasses import dataclass

from rich.cells import cell_len, split_graphemes


@dataclass(frozen=True)
class Fragment:
    text: str
    color: str
    bold: bool = False
    italic: bool = False


def _unwrapped_columns(raw_lines: list[list[Fragment]], line_numbers: bool) -> int:
    content_columns = max((_line_cell_width(line) for line in raw_lines), default=0)
    number_columns = len(str(len(raw_lines))) + 3 if line_numbers else 0
    return max(20, content_columns + number_columns)


def _line_cell_width(line: list[Fragment]) -> int:
    return sum(cell_len(fragment.text) for fragment in line)


def _prepare_lines(
    raw_lines: list[list[Fragment]],
    max_columns: int,
    *,
    line_numbers: bool,
    muted_text: str,
    word_wrap: bool,
) -> list[list[Fragment]]:
    numbered_width = len(str(len(raw_lines))) if line_numbers else 0
    content_columns = max(12, max_columns - (numbered_width + 3 if line_numbers else 0))
    output: list[list[Fragment]] = []

    for index, fragments in enumerate(raw_lines, start=1):
        wrapped = (
            _wrap_fragments(fragments, content_columns) if word_wrap else [fragments]
        )
        for wrap_index, line in enumerate(wrapped):
            if line_numbers:
                label = (
                    str(index).rjust(numbered_width)
                    if wrap_index == 0
                    else " " * numbered_width
                )
                output.append([Fragment(f"{label} │ ", muted_text), *line])
            else:
                output.append(line)
    return output


def _wrap_fragments(fragments: list[Fragment], width: int) -> list[list[Fragment]]:
    text = "".join(fragment.text for fragment in fragments)
    if cell_len(text) <= width:
        return [fragments]

    wrapped: list[list[Fragment]] = []
    line: list[Fragment] = []
    line_width = 0
    for fragment in fragments:
        spans, _total_width = split_graphemes(fragment.text)
        for start, end, grapheme_width in spans:
            if grapheme_width and line and line_width + grapheme_width > width:
                wrapped.append(line)
                line = []
                line_width = 0
            _append_fragment(line, fragment, fragment.text[start:end])
            line_width += grapheme_width
    if line:
        wrapped.append(line)
    return wrapped or [[]]


def _append_fragment(line: list[Fragment], template: Fragment, text: str) -> None:
    if not text:
        return
    if line and _same_style(line[-1], template):
        previous = line[-1]
        line[-1] = Fragment(
            previous.text + text, previous.color, previous.bold, previous.italic
        )
        return
    line.append(
        Fragment(text, template.color, bold=template.bold, italic=template.italic)
    )


def _same_style(left: Fragment, right: Fragment) -> bool:
    return (
        left.color == right.color
        and left.bold == right.bold
        and left.italic == right.italic
    )
