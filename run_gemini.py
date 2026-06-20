# To run this code you need to install the following dependencies:
#   pip install google-genai
# Or from this directory:
#   pip install -r requirements.txt
#
# Set GEMINI_API_KEY in your environment, then e.g.:
#   python run_gemini.py --input chunks/chunk_001_pages_1-10.pdf

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from google import genai
from google.genai import types

DEFAULT_PROMPT = Path(__file__).resolve().parent / "prompt.md"
DEFAULT_MODEL = "gemini-3-flash-preview"


def _user_parts(prompt: str, document_path: Path) -> list[types.Part]:
    suffix = document_path.suffix.lower()
    if suffix == ".pdf":
        data = document_path.read_bytes()
        return [
            types.Part.from_text(text=prompt),
            types.Part.from_bytes(data=data, mime_type="application/pdf"),
        ]
    doc_text = document_path.read_text(encoding="utf-8")
    combined = f"{prompt}\n\n---\n\nDocument content:\n\n{doc_text}"
    return [types.Part.from_text(text=combined)]


def generate(
    prompt: str,
    document_path: Path,
    *,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.2,
) -> None:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY is not set.", file=sys.stderr)
        sys.exit(1)

    client = genai.Client(api_key=api_key)

    contents = [
        types.Content(
            role="user",
            parts=_user_parts(prompt, document_path),
        ),
    ]
    generate_content_config = types.GenerateContentConfig(
        temperature=temperature,
        thinking_config=types.ThinkingConfig(
            thinking_level="MEDIUM",
        ),
    )

    for chunk in client.models.generate_content_stream(
        model=model,
        contents=contents,
        config=generate_content_config,
    ):
        if text := chunk.text:
            print(text, end="")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Stream Gemini extraction using prompt.md and a PDF or text document.",
    )
    parser.add_argument(
        "--prompt",
        type=Path,
        default=DEFAULT_PROMPT,
        help=f"path to instructions (default: {DEFAULT_PROMPT})",
    )
    parser.add_argument(
        "--input",
        "-i",
        type=Path,
        required=True,
        help="PDF or text file to send with the prompt",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"model id (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.2,
        help="sampling temperature (default: 0.2)",
    )
    args = parser.parse_args()

    prompt_path = args.prompt.expanduser().resolve()
    if not prompt_path.is_file():
        print(f"Error: prompt file not found: {prompt_path}", file=sys.stderr)
        sys.exit(1)

    doc_path = args.input.expanduser().resolve()
    if not doc_path.is_file():
        print(f"Error: input file not found: {doc_path}", file=sys.stderr)
        sys.exit(1)

    prompt_text = prompt_path.read_text(encoding="utf-8")
    generate(
        prompt_text,
        doc_path,
        model=args.model,
        temperature=args.temperature,
    )


if __name__ == "__main__":
    main()
