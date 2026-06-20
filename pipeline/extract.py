"""Run Gemini structured extraction on PDF chunks."""

from __future__ import annotations

import os
from pathlib import Path

from google import genai
from google.genai import types

from .config import (
    CONTEXT_SUFFIX,
    DEFAULT_MODEL,
    DEFAULT_TEMPERATURE,
    DEFAULT_THINKING_LEVEL,
)


def _require_api_key() -> str:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set in the environment.")
    return api_key


def _build_parts(
    prompt: str,
    chunk_pdf: Path,
    *,
    context_pdf: Path | None = None,
) -> list[types.Part]:
    parts: list[types.Part] = [types.Part.from_text(text=prompt)]

    if context_pdf is not None:
        parts.append(types.Part.from_text(text=CONTEXT_SUFFIX.strip()))
        parts.append(
            types.Part.from_bytes(
                data=context_pdf.read_bytes(),
                mime_type="application/pdf",
            )
        )

    parts.append(
        types.Part.from_bytes(
            data=chunk_pdf.read_bytes(),
            mime_type="application/pdf",
        )
    )
    return parts


def extract_chunk(
    prompt: str,
    chunk_pdf: Path,
    *,
    context_pdf: Path | None = None,
    model: str = DEFAULT_MODEL,
    temperature: float = DEFAULT_TEMPERATURE,
    thinking_level: str = DEFAULT_THINKING_LEVEL,
) -> tuple[str, types.GenerateContentResponse]:
    """Extract structured markdown table text from one chunk PDF."""
    client = genai.Client(api_key=_require_api_key())

    contents = [
        types.Content(
            role="user",
            parts=_build_parts(prompt, chunk_pdf, context_pdf=context_pdf),
        ),
    ]
    config = types.GenerateContentConfig(
        temperature=temperature,
        thinking_config=types.ThinkingConfig(
            thinking_level=thinking_level,
        ),
    )

    response = client.models.generate_content(
        model=model,
        contents=contents,
        config=config,
    )

    text = response.text or ""
    return text, response


def save_extraction(markdown: str, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown.rstrip() + "\n", encoding="utf-8")
    return output_path
