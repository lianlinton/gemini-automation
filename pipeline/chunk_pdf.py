"""Split cabinet-meeting PDFs into extraction chunks.

Chunking rules (1-based page numbers):
  - Page 1 is always its own chunk.
  - Remaining pages are grouped in blocks of up to 10: 2-11, 12-21, 22-31, ...
  - The final block may contain fewer than 10 pages.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader, PdfWriter

from .config import DEFAULT_CHUNK_PAGES


@dataclass(frozen=True)
class PageRange:
    """Inclusive 1-based page range."""

    start: int
    end: int

    @property
    def label(self) -> str:
        if self.start == self.end:
            return f"{self.start}"
        return f"{self.start}-{self.end}"

    def filename_part(self) -> str:
        return f"pages_{self.label}"


def page_ranges(total_pages: int, *, chunk_size: int = DEFAULT_CHUNK_PAGES) -> list[PageRange]:
    """Return ordered chunk page ranges for a document."""
    if total_pages < 1:
        return []

    ranges: list[PageRange] = [PageRange(1, 1)]
    start = 2
    while start <= total_pages:
        end = min(start + chunk_size - 1, total_pages)
        ranges.append(PageRange(start, end))
        start = end + 1
    return ranges


def context_page(range_index: int, ranges: list[PageRange]) -> int | None:
    """Last page of the previous chunk, for boundary context (1-based)."""
    if range_index <= 0:
        return None
    return ranges[range_index - 1].end


def _write_page_subset(
    reader: PdfReader,
    page_numbers: list[int],
    output_path: Path,
) -> None:
    writer = PdfWriter()
    for page_number in page_numbers:
        writer.add_page(reader.pages[page_number - 1])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("wb") as handle:
        writer.write(handle)


def split_pdf(
    input_pdf: Path,
    output_dir: Path,
    *,
    name_prefix: str | None = None,
    chunk_size: int = DEFAULT_CHUNK_PAGES,
) -> list[Path]:
    """Split *input_pdf* into chunk PDFs under *output_dir*."""
    reader = PdfReader(str(input_pdf))
    total_pages = len(reader.pages)
    ranges = page_ranges(total_pages, chunk_size=chunk_size)
    prefix = name_prefix or input_pdf.stem

    if not ranges:
        return []

    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    for index, page_range in enumerate(ranges, start=1):
        page_numbers = list(range(page_range.start, page_range.end + 1))
        filename = f"{prefix}__chunk_{index:03d}_{page_range.filename_part()}.pdf"
        output_path = output_dir / filename
        _write_page_subset(reader, page_numbers, output_path)
        written.append(output_path)

    return written


def write_context_page_pdf(
    source_pdf: Path,
    page_number: int,
    output_path: Path,
) -> Path:
    """Write a single-page PDF used as read-only chunk-boundary context."""
    reader = PdfReader(str(source_pdf))
    _write_page_subset(reader, [page_number], output_path)
    return output_path
