"""Merge per-chunk markdown extractions into one file per source PDF."""

from __future__ import annotations

import re
from pathlib import Path


def _chunk_sort_key_from_name(name: str) -> int:
    match = re.search(r"__chunk_(\d{3})_|^chunk_(\d{3})_", name)
    return int(match.group(1) or match.group(2)) if match else 0


def _is_separator_row(line: str) -> bool:
    stripped = line.strip()
    if not stripped.startswith("|"):
        return False
    cells = [cell.strip() for cell in stripped.strip("|").split("|")]
    return bool(cells) and all(cell.startswith(":---") for cell in cells if cell)


def _table_body_lines(lines: list[str]) -> list[str]:
    """Drop markdown table header and separator; keep data rows."""
    body: list[str] = []
    past_separator = False
    for line in lines:
        if not past_separator:
            if _is_separator_row(line):
                past_separator = True
            continue
        if line.strip():
            body.append(line)
    return body


def merge_chunk_markdowns(chunk_md_paths: list[Path]) -> str:
    """Concatenate chunk tables in order; header appears once."""
    if not chunk_md_paths:
        return ""

    sections: list[str] = []
    for index, path in enumerate(chunk_md_paths):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8").strip()
        if not text:
            continue

        lines = text.splitlines()
        if index == 0:
            sections.append(text)
        else:
            body = _table_body_lines(lines)
            if body:
                sections.append("\n".join(body))

    if not sections:
        return ""

    return "\n\n".join(sections).rstrip() + "\n"


def merge_source_extractions(jobs: list, *, output_path: Path) -> Path | None:
    """Write merged markdown for one source PDF. *jobs* must be ChunkJob-like."""
    chunk_mds = sorted(
        (job.extraction_md for job in jobs if job.extraction_md.is_file()),
        key=lambda p: _chunk_sort_key_from_name(p.name),
    )
    if not chunk_mds:
        return None

    merged = merge_chunk_markdowns(chunk_mds)
    if not merged:
        return None

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(merged, encoding="utf-8")
    return output_path
