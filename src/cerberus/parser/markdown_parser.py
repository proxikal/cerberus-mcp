import re
from pathlib import Path
from typing import List, Tuple

from cerberus.schemas import CodeSymbol

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


def parse_markdown_file(file_path: Path, content: str) -> List[CodeSymbol]:
    """
    Extract heading-based sections from workflow markdown files.
    """
    lines = content.splitlines()
    headings: List[Tuple[int, str, int]] = []

    for idx, line in enumerate(lines, start=1):
        match = HEADING_RE.match(line)
        if match:
            level = len(match.group(1))
            title = match.group(2).strip()
            headings.append((idx, title, level))

    symbols: List[CodeSymbol] = []
    if headings:
        for i, (line_no, title, level) in enumerate(headings):
            end_line = headings[i + 1][0] - 1 if i + 1 < len(headings) else max(len(lines), line_no)
            name = title or f"Section {i + 1}"
            signature = f"{'#' * level} {title}".strip()
            symbols.append(
                CodeSymbol(
                    name=name,
                    type="section",
                    file_path=str(file_path),
                    start_line=line_no,
                    end_line=end_line,
                    signature=signature,
                )
            )
    else:
        end_line = max(len(lines), 1)
        name = file_path.stem
        symbols.append(
            CodeSymbol(
                name=name,
                type="section",
                file_path=str(file_path),
                start_line=1,
                end_line=end_line,
                signature=f"# {name}",
            )
        )

    return symbols
