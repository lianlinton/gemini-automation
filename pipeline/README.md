# Gemini Automation — pipeline

Splits cabinet-meeting PDFs and runs structured extraction with Gemini 3 Flash Preview (medium thinking).

## Chunking (Step 2)

Page 1 is always its own chunk (cover/metadata: attendance, agenda). Remaining pages are grouped in blocks of up to 10.

| Chunk | Pages |
|-------|-------|
| 1 | 1 (metadata) |
| 2 | 2–11 |
| 3 | 12–21 |
| 4 | 22–25 |

## Logging (Step 6)

| File | Purpose |
|------|---------|
| `run.log` | Live processing log |
| `chunks_index.json` | All chunk PDFs after split |
| `manifest.json` | Per-chunk API usage |
| `processing_summary.json` | Per-document completion status |

## Output layout (Steps 3, 5, 7)

Each meeting produces a merged markdown table in `final/`. Chunk-level files in `extractions/` are intermediate outputs.

```
pipeline_output/
  <pdf_name>/                    # unique; duplicates become <name>__1, <name>__2
    <pdf_name>.pdf               # copy of source (with --copy-source)
    chunks/
      <pdf_name>__chunk_001_pages_1.pdf
      <pdf_name>__chunk_002_pages_2-11.pdf
      ...
    extractions/
      <pdf_name>__chunk_001_pages_1.md
      ...
    final/
      <pdf_name>.md              # merged table for the whole PDF
```

If two input PDFs share the same filename (e.g. from different folders), the
pipeline prints `[duplicate]` warnings and assigns `name__1`, `name__2`, etc.

## Chunk-boundary context

From the second chunk onward, the **last page of the previous chunk** is attached as read-only context so the model can see an ongoing speaker or agenda topic at the start of the new chunk. Rows are extracted only from the main chunk pages.

## Setup

```bash
cd /path/to/gemini-automation
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export GEMINI_API_KEY="your-key-here"
```

Never commit API keys. Rotate any key that was shared in email or chat.

## Run

Full pipeline (split + extract + merge):

```bash
python -m pipeline input/ -o pipeline_output --copy-source --skip-existing
```

Preprocess only:

```bash
python -m pipeline input/ -o pipeline_output --preprocess-only
```

Extract only (after preprocess; requires source PDF copied into each output folder):

```bash
python -m pipeline pipeline_output --extract-only --skip-existing
```

Merge only (rebuild `final/*.md` from existing chunk extractions):

```bash
python -m pipeline pipeline_output --merge-only
```

Defaults match the test configuration:

- Model: `gemini-3-flash-preview`
- Thinking: `MEDIUM`
- Temperature: `0.2`
- Prompt: `../prompt.md`

## References

- `../prompt.md` — extraction instructions
- `../run_gemini.py` — single-chunk streaming helper
- `../split_pdf.py` — earlier 10-page-only splitter (superseded by this pipeline)
- `../tests/*.md` — example model output format
