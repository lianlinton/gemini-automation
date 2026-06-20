"""Cabinet stenogram preprocessing and Gemini extraction pipeline."""

from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root when the pipeline package is imported.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")
