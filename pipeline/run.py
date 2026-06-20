#!/usr/bin/env python3
"""End-to-end pipeline: split PDFs into chunks, then extract structured tables."""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from pypdf import PdfReader

from .chunk_pdf import context_page, page_ranges, split_pdf, write_context_page_pdf
from .config import (
    DEFAULT_CHUNK_PAGES,
    DEFAULT_MODEL,
    DEFAULT_PROMPT,
    DEFAULT_TEMPERATURE,
    DEFAULT_THINKING_LEVEL,
)
from .extract import extract_chunk, save_extraction
from .merge import merge_source_extractions


@dataclass
class ChunkJob:
    source_pdf: Path
    work_name: str
    chunk_pdf: Path
    extraction_md: Path
    merged_md: Path
    context_page_number: int | None


def _discover_pdfs(inputs: list[Path]) -> list[Path]:
    pdfs: list[Path] = []
    for path in inputs:
        path = path.expanduser().resolve()
        if path.is_dir():
            pdfs.extend(sorted(path.glob("*.pdf")))
        elif path.suffix.lower() == ".pdf":
            pdfs.append(path)
        else:
            print(f"Skipping non-PDF path: {path}", file=sys.stderr)
    return pdfs


def _resolve_work_names(pdfs: list[Path]) -> dict[Path, str]:
    """Assign a unique output folder / chunk prefix per PDF; log duplicate stems."""
    by_stem: dict[str, list[Path]] = defaultdict(list)
    for pdf in pdfs:
        by_stem[pdf.stem].append(pdf)

    for stem, paths in sorted(by_stem.items()):
        if len(paths) > 1:
            print(f"[duplicate] PDF name '{stem}.pdf' appears {len(paths)} times:")
            for path in paths:
                print(f"  - {path}")

    work_names: dict[Path, str] = {}
    stem_counter: dict[str, int] = defaultdict(int)

    for pdf in pdfs:
        stem = pdf.stem
        if len(by_stem[stem]) > 1:
            stem_counter[stem] += 1
            work_names[pdf] = f"{stem}__{stem_counter[stem]}"
        else:
            work_names[pdf] = stem

    return work_names


def _chunk_sort_key(path: Path) -> tuple[str, int]:
    match = re.search(r"__chunk_(\d{3})_|^chunk_(\d{3})_", path.name)
    index = int(match.group(1) or match.group(2)) if match else 0
    return (path.name, index)


def _list_chunk_pdfs(chunks_dir: Path) -> list[Path]:
    prefixed = sorted(chunks_dir.glob("*__chunk_*.pdf"), key=_chunk_sort_key)
    if prefixed:
        return prefixed
    return sorted(chunks_dir.glob("chunk_*.pdf"), key=_chunk_sort_key)


def _chunk_jobs_for_source(
    source_pdf: Path,
    work_dir: Path,
    *,
    work_name: str,
    chunk_size: int = DEFAULT_CHUNK_PAGES,
) -> list[ChunkJob]:
    chunks_dir = work_dir / "chunks"
    extractions_dir = work_dir / "extractions"
    final_dir = work_dir / "final"
    chunk_paths = split_pdf(
        source_pdf,
        chunks_dir,
        name_prefix=work_name,
        chunk_size=chunk_size,
    )

    reader_pages = len(PdfReader(str(source_pdf)).pages)
    ranges = page_ranges(reader_pages, chunk_size=chunk_size)

    jobs: list[ChunkJob] = []
    for index, chunk_path in enumerate(chunk_paths):
        stem = chunk_path.stem
        jobs.append(
            ChunkJob(
                source_pdf=source_pdf,
                work_name=work_name,
                chunk_pdf=chunk_path,
                extraction_md=extractions_dir / f"{stem}.md",
                merged_md=final_dir / f"{work_name}.md",
                context_page_number=context_page(index, ranges),
            )
        )
    return jobs


def extract_all(
    jobs_by_source: dict[str, list[ChunkJob]],
    *,
    prompt_path: Path,
    model: str,
    temperature: float,
    thinking_level: str,
    skip_existing: bool,
    manifest_path: Path | None,
) -> list[dict]:
    prompt = prompt_path.read_text(encoding="utf-8")
    manifest: list[dict] = []

    for source_name, jobs in jobs_by_source.items():
        print(f"[extract] {source_name}: {len(jobs)} chunk(s)")
        for job in jobs:
            if skip_existing and job.extraction_md.is_file():
                print(f"  skip (exists): {job.extraction_md.name}")
                manifest.append(
                    {
                        "source": source_name,
                        "chunk": job.chunk_pdf.name,
                        "status": "skipped",
                        "output": str(job.extraction_md),
                    }
                )
                continue

            if job.context_page_number is not None:
                with tempfile.TemporaryDirectory(prefix="gemini_ctx_") as tmp:
                    context_pdf = Path(tmp) / "context.pdf"
                    write_context_page_pdf(
                        job.source_pdf,
                        job.context_page_number,
                        context_pdf,
                    )
                    print(
                        f"  extracting: {job.chunk_pdf.name} "
                        f"(context p.{job.context_page_number})"
                    )
                    markdown, response = extract_chunk(
                        prompt,
                        job.chunk_pdf,
                        context_pdf=context_pdf,
                        model=model,
                        temperature=temperature,
                        thinking_level=thinking_level,
                    )
            else:
                print(f"  extracting: {job.chunk_pdf.name}")
                markdown, response = extract_chunk(
                    prompt,
                    job.chunk_pdf,
                    model=model,
                    temperature=temperature,
                    thinking_level=thinking_level,
                )

            save_extraction(markdown, job.extraction_md)

            usage = getattr(response, "usage_metadata", None)
            manifest.append(
                {
                    "source": source_name,
                    "chunk": job.chunk_pdf.name,
                    "status": "ok",
                    "output": str(job.extraction_md),
                    "context_page": job.context_page_number,
                    "usage": usage.model_dump() if usage is not None else None,
                }
            )
            print(f"  saved: {job.extraction_md}")

    if manifest_path is not None:
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(
            json.dumps(
                {
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "model": model,
                    "thinking_level": thinking_level,
                    "temperature": temperature,
                    "runs": manifest,
                },
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )

    return manifest


def write_processing_summary(
    output_root: Path,
    jobs_by_source: dict[str, list[ChunkJob]],
    manifest: list[dict],
) -> Path:
    """Write a per-document processing summary and print totals."""
    by_source: dict[str, dict] = {}
    for source_name, jobs in jobs_by_source.items():
        total = len(jobs)
        extracted = sum(1 for job in jobs if job.extraction_md.is_file())
        merged = jobs[0].merged_md.is_file() if jobs else False
        by_source[source_name] = {
            "chunks_total": total,
            "chunks_extracted": extracted,
            "chunks_pending": total - extracted,
            "merged": merged,
            "merged_path": str(jobs[0].merged_md) if jobs and merged else None,
        }

    status_counts: dict[str, int] = {}
    for entry in manifest:
        status = entry.get("status", "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1

    summary = {
        "documents": len(jobs_by_source),
        "chunks_total": sum(len(j) for j in jobs_by_source.values()),
        "chunks_extracted": sum(
            1
            for jobs in jobs_by_source.values()
            for job in jobs
            if job.extraction_md.is_file()
        ),
        "status_counts": status_counts,
        "per_document": by_source,
    }

    summary_path = output_root / "processing_summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print("[summary] Processing status")
    print(f"  documents: {summary['documents']}")
    print(f"  chunks: {summary['chunks_extracted']}/{summary['chunks_total']} extracted")
    for status, count in sorted(status_counts.items()):
        print(f"  {status}: {count}")
    for source_name, info in sorted(by_source.items()):
        pending = info["chunks_pending"]
        flag = "OK" if pending == 0 and info["merged"] else "INCOMPLETE"
        print(
            f"  [{flag}] {source_name}: "
            f"{info['chunks_extracted']}/{info['chunks_total']} chunks"
            + (" | merged" if info["merged"] else "")
        )
    print(f"[summary] Written to {summary_path}")
    return summary_path


def write_chunks_index(
    output_root: Path,
    jobs_by_source: dict[str, list[ChunkJob]],
) -> Path:
    """Log every chunk PDF created during preprocessing."""
    index = {
        "documents": len(jobs_by_source),
        "chunks_total": sum(len(j) for j in jobs_by_source.values()),
        "files": [],
    }
    for source_name, jobs in sorted(jobs_by_source.items()):
        for job in jobs:
            index["files"].append(
                {
                    "source": source_name,
                    "chunk": job.chunk_pdf.name,
                    "path": str(job.chunk_pdf),
                }
            )

    index_path = output_root / "chunks_index.json"
    index_path.write_text(
        json.dumps(index, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"[preprocess] Chunk index: {index['chunks_total']} file(s) -> {index_path}")
    return index_path


def merge_all(jobs_by_source: dict[str, list[ChunkJob]]) -> list[Path]:
    """Concatenate chunk extractions into one markdown file per source PDF."""
    written: list[Path] = []
    for source_name, jobs in jobs_by_source.items():
        if not jobs:
            continue
        merged_path = jobs[0].merged_md
        result = merge_source_extractions(jobs, output_path=merged_path)
        if result is None:
            print(f"[merge] {source_name}: no chunk extractions found, skipped")
            continue
        written.append(result)
        chunk_count = sum(1 for job in jobs if job.extraction_md.is_file())
        print(f"[merge] {source_name}: {chunk_count} chunk(s) -> {result}")
    return written


def load_jobs_from_output_root(output_root: Path) -> dict[str, list[ChunkJob]]:
    """Rebuild chunk jobs from an existing preprocess output tree."""
    jobs_by_source: dict[str, list[ChunkJob]] = {}

    for source_dir in sorted(p for p in output_root.iterdir() if p.is_dir()):
        chunks_dir = source_dir / "chunks"
        if not chunks_dir.is_dir():
            continue

        work_name = source_dir.name
        source_pdf = source_dir / f"{work_name}.pdf"
        if not source_pdf.is_file():
            source_pdf = next(source_dir.glob("*.pdf"), Path("__missing__.pdf"))
        if not source_pdf.is_file():
            print(
                f"Warning: no source PDF in {source_dir}; "
                "context pages cannot be rebuilt. Place the original PDF there.",
                file=sys.stderr,
            )

        reader_pages = 0
        if source_pdf.is_file():
            reader_pages = len(PdfReader(str(source_pdf)).pages)
        ranges = page_ranges(reader_pages) if reader_pages else []

        jobs: list[ChunkJob] = []
        chunk_pdfs = _list_chunk_pdfs(chunks_dir)
        for index, chunk_pdf in enumerate(chunk_pdfs):
            ctx = context_page(index, ranges) if ranges else None
            jobs.append(
                ChunkJob(
                    source_pdf=source_pdf,
                    work_name=work_name,
                    chunk_pdf=chunk_pdf,
                    extraction_md=source_dir / "extractions" / f"{chunk_pdf.stem}.md",
                    merged_md=source_dir / "final" / f"{work_name}.md",
                    context_page_number=ctx,
                )
            )
        jobs_by_source[work_name] = jobs

    return jobs_by_source


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Split cabinet stenogram PDFs and extract structured markdown tables.",
    )
    parser.add_argument(
        "inputs",
        nargs="+",
        type=Path,
        help="PDF files or directories containing PDFs",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path("pipeline_output"),
        help="root output directory (default: pipeline_output)",
    )
    parser.add_argument(
        "--prompt",
        type=Path,
        default=DEFAULT_PROMPT,
        help=f"extraction prompt file (default: {DEFAULT_PROMPT})",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Gemini model id (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--thinking-level",
        default=DEFAULT_THINKING_LEVEL,
        choices=["MINIMAL", "LOW", "MEDIUM", "HIGH"],
        help=f"thinking level (default: {DEFAULT_THINKING_LEVEL})",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=DEFAULT_TEMPERATURE,
        help=f"sampling temperature (default: {DEFAULT_TEMPERATURE})",
    )
    parser.add_argument(
        "--chunk-pages",
        type=int,
        default=DEFAULT_CHUNK_PAGES,
        help=f"pages per chunk after page 1 (default: {DEFAULT_CHUNK_PAGES})",
    )
    parser.add_argument(
        "--preprocess-only",
        action="store_true",
        help="only split PDFs into chunks; do not call Gemini",
    )
    parser.add_argument(
        "--extract-only",
        action="store_true",
        help="only run extraction on an existing output tree",
    )
    parser.add_argument(
        "--merge-only",
        action="store_true",
        help="only merge existing chunk extractions into final markdown files",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="skip chunks whose .md extraction already exists",
    )
    parser.add_argument(
        "--copy-source",
        action="store_true",
        help="copy each source PDF into its output folder (needed for --extract-only context)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.extract_only or args.merge_only:
        candidate = args.inputs[0].expanduser().resolve() if args.inputs else None
        if candidate and candidate.is_dir():
            output_root = candidate
        else:
            output_root = args.output.expanduser().resolve()
    else:
        output_root = args.output.expanduser().resolve()
    prompt_path = args.prompt.expanduser().resolve()

    if not prompt_path.is_file() and not args.merge_only:
        print(f"Error: prompt not found: {prompt_path}", file=sys.stderr)
        return 1

    if args.merge_only:
        jobs_by_source = load_jobs_from_output_root(output_root)
        if not jobs_by_source:
            print(f"Error: no output folders found under {output_root}", file=sys.stderr)
            return 1
        merge_all(jobs_by_source)
        write_processing_summary(output_root, jobs_by_source, manifest=[])
        print("Done.")
        return 0

    if args.extract_only:
        jobs_by_source = load_jobs_from_output_root(output_root)
        if not jobs_by_source:
            print(f"Error: no chunk folders found under {output_root}", file=sys.stderr)
            return 1
    else:
        pdfs = _discover_pdfs(args.inputs)
        if not pdfs:
            print("Error: no PDF inputs found.", file=sys.stderr)
            return 1

        work_names = _resolve_work_names(pdfs)
        jobs_by_source = {}
        for source_pdf in pdfs:
            work_name = work_names[source_pdf]
            work_dir = output_root / work_name
            if args.copy_source:
                work_dir.mkdir(parents=True, exist_ok=True)
                dest = work_dir / f"{work_name}.pdf"
                if not dest.exists():
                    dest.write_bytes(source_pdf.read_bytes())
            jobs = _chunk_jobs_for_source(
                source_pdf,
                work_dir,
                work_name=work_name,
                chunk_size=args.chunk_pages,
            )
            jobs_by_source[work_name] = jobs
            print(
                f"[preprocess] {source_pdf.name} -> {work_name}/ "
                f"({len(jobs)} chunk(s) in {work_dir / 'chunks'})"
            )

    if args.preprocess_only:
        write_chunks_index(output_root, jobs_by_source)
        print(f"Done. Chunks written under {output_root}")
        return 0

    manifest_path = output_root / "manifest.json"
    manifest = extract_all(
        jobs_by_source,
        prompt_path=prompt_path,
        model=args.model,
        temperature=args.temperature,
        thinking_level=args.thinking_level,
        skip_existing=args.skip_existing,
        manifest_path=manifest_path,
    )
    merge_all(jobs_by_source)
    write_processing_summary(output_root, jobs_by_source, manifest)
    print(f"Done. Manifest: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
