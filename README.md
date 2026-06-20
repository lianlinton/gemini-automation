# Gemini Stenogram Automation

Pipeline for extracting structured speech-unit tables from Israeli government cabinet meeting stenograms using the Gemini API.

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add GEMINI_API_KEY
```

Put source PDFs in `input/` (e.g. `input/1968/`), then:

```bash
# Split + extract + merge
python -m pipeline input/1968 -o pipeline_output/1968 --copy-source --skip-existing

# Or extract only (after chunks exist)
python -m pipeline pipeline_output/1968 --extract-only --skip-existing
```

See [`pipeline/README.md`](pipeline/README.md) for chunking rules, output layout, and options.

## Project layout

| Path | Purpose |
|------|---------|
| `prompt.md` | Extraction instructions sent to Gemini |
| `pipeline/` | Chunking, extraction, merge orchestration |
| `tests/` | Sample model outputs (quality reference) |
| `input/` | Source PDFs (not committed) |
| `pipeline_output/` | Chunks, extractions, merged tables (not committed) |

## Defaults

- Model: `gemini-3-flash-preview`
- Thinking: `MEDIUM`
- Temperature: `0.2`
