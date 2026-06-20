"""Shared defaults for the stenogram extraction pipeline."""

from pathlib import Path

# Project root (parent of this package)
ROOT = Path(__file__).resolve().parent.parent

DEFAULT_PROMPT = ROOT / "prompt.md"
DEFAULT_MODEL = "gemini-3-flash-preview"
DEFAULT_THINKING_LEVEL = "MEDIUM"
DEFAULT_TEMPERATURE = 0.2
DEFAULT_CHUNK_PAGES = 10  # pages per chunk after page 1

CONTEXT_SUFFIX = """

---
CHUNK BOUNDARY CONTEXT (read-only):
The additional PDF page attached after this instruction is the LAST page of the
previous chunk. Use it only to determine whether an opening speech or agenda
topic continues from that page into this chunk.
Do NOT extract any rows whose Page/s values fall only on that context page.
Extract only speech units whose Page/s appear in the main chunk document.
"""
