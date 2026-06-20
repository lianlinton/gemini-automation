# Setup and usage guide

This guide describes how to run **Gemini Automation** according to the project specifications. You do not need programming experience — only the ability to copy commands into **Terminal** on a Mac.

**Repository:** https://github.com/lianlinton/gemini-automation

---

## Quick reference

```bash
# Activate (every session)
cd ~/Documents/datasquad/gemini-automation
source .venv/bin/activate

# Split only
python -m pipeline input/1968 -o pipeline_output/1968 --preprocess-only

# Full workflow
python -m pipeline input/1968 -o pipeline_output/1968 --copy-source --skip-existing

# Resume
python -m pipeline pipeline_output/1968 --extract-only --skip-existing

# Merge only
python -m pipeline pipeline_output/1968 --merge-only

# Count progress
find pipeline_output/1968 -path "*/extractions/*.md" | wc -l
```

**Finished tables:** `pipeline_output/1968/<pdf-name>/final/<pdf-name>.md`

First time using this? Continue to **First-time setup** at the bottom. Already configured? Jump to **If already set up — next steps** below.

---

# If already set up — next steps

Skip to **First-time setup** at the bottom only if you have never installed Python or configured the project. See **Quick reference** above for copy-paste commands.

Your API key must already be in `.env` (see First-time setup → Step D).

---

## Workflow overview

The tool follows these steps automatically:

| Step | What happens |
|------|----------------|
| **1** | Organize input PDFs |
| **2** | Split each PDF into chunks (page 1 alone, then 10-page blocks) |
| **3** | Store chunks in a structured folder with consistent naming |
| **4** | Loop through chunks → send each to Gemini with the OCR/extraction prompt → save response |
| **5** | Save output as `.md` files (structured markdown tables) |
| **6** | Log every file processed |
| **7** | Merge chunk outputs into one complete document per meeting |

---

## Step 1 — Organize input files

Put all cabinet meeting PDFs for one batch in a single folder inside `input/`.

**In Finder:**

1. Open the `gemini-automation` folder.
2. Open `input/`.
3. Create a folder for your batch (e.g. `1968`).
4. Drag all meeting PDFs into `input/1968/`.

**Example structure:**

```
gemini-automation/
  input/
    1968/
      סטנוגרמה ישיבה א-תשכ''ט...pdf
      סטנוגרמה ישיבה ב-תשכ''ח...pdf
      ...
```

Only `.pdf` files are processed.

---

## Step 2 — Split PDFs into chunks

Each document is split so Gemini can read it reliably:

| Chunk | Pages | Purpose |
|-------|-------|---------|
| **Chunk 1** | Page 1 only | Cover sheet: metadata, attendance (present/absent), agenda |
| **Chunk 2** | Pages 2–11 | First block of transcript |
| **Chunk 3** | Pages 12–21 | Next block |
| **…** | … | Continues in 10-page blocks |
| **Last chunk** | Remainder | e.g. pages 22–25 if the document has 25 pages |

**To split only (no API cost — good for testing):**

```bash
python -m pipeline input/1968 -o pipeline_output/1968 --preprocess-only
```

This creates all chunk PDFs without calling Gemini.

---

## Step 3 — Structured chunk folders and consistent naming

Every input PDF gets its own output folder. Chunk files are named with the **original PDF name** so nothing gets mixed up across meetings.

**Output structure:**

```
pipeline_output/1968/
  <pdf-name>/
    <pdf-name>.pdf          ← copy of original (when using --copy-source)
    chunks/
      <pdf-name>__chunk_001_pages_1.pdf
      <pdf-name>__chunk_002_pages_2-11.pdf
      <pdf-name>__chunk_003_pages_12-21.pdf
      ...
```

**Naming pattern:**

```
{original-pdf-name}__chunk_{number}_{page-range}.pdf
```

If two PDFs have the same filename, the tool prints a `[duplicate]` warning and uses `name__1`, `name__2`, etc.

**Chunk index log** (written after splitting):

```
pipeline_output/1968/chunks_index.json
```

Lists every chunk file created — use this to verify all documents were split.

---

## Step 4 — Processing script (Gemini loop)

The script loops through every chunk PDF, sends it to **Gemini 3 Flash Preview** with the extraction prompt (`prompt.md`), and saves the response.

**What gets sent to Gemini:**

- The instructions in `prompt.md` (12-column table: speaker, text unit, topic, pages, etc.)
- The chunk PDF
- *(From chunk 2 onward)* the last page of the previous chunk as read-only context (so speakers/topics that span a split are not lost)

**Full run (split + process + merge):**

```bash
python -m pipeline input/1968 -o pipeline_output/1968 --copy-source --skip-existing
```

**Process only** (chunks already split):

```bash
python -m pipeline pipeline_output/1968 --extract-only --skip-existing
```

| Flag | Meaning |
|------|---------|
| `--copy-source` | Keeps original PDF in each output folder (needed to resume) |
| `--skip-existing` | Skips chunks that already have output (safe to stop and restart) |

---

## Step 5 — Output structure (`.md` files)

Output is **markdown** (`.md`) — a structured table, one row per speech unit.

**Per chunk (intermediate):**

```
pipeline_output/1968/<pdf-name>/extractions/
  <pdf-name>__chunk_001_pages_1.md
  <pdf-name>__chunk_002_pages_2-11.md
  ...
```

Each file contains a markdown table like the samples in the `tests/` folder (Serial Number, Speaker, Text Unit, Topic, Page/s, etc.).

**Why `.md` and not `.txt`?** Tables stay readable and can be opened in TextEdit, VS Code, or imported into other tools. Plain `.txt` would lose table structure.

---

## Step 6 — Logging (verify all files were processed)

The tool writes several logs so you can confirm nothing was missed:

| File | What it records |
|------|-----------------|
| `pipeline_output/1968/run.log` | Live text log (`extracting:`, `saved:`, `skip:`) |
| `pipeline_output/1968/chunks_index.json` | Every chunk PDF after splitting |
| `pipeline_output/1968/manifest.json` | Every API call + token usage per chunk |
| `pipeline_output/1968/processing_summary.json` | **Final status per document** — chunks done vs. pending, merge status |

**Check how many chunks are done:**

```bash
find pipeline_output/1968 -path "*/extractions/*.md" | wc -l
```

**Read the summary** (after a run finishes or stops):

Open `processing_summary.json` in TextEdit. Each document shows:

- `chunks_total` — how many chunks exist
- `chunks_extracted` — how many have `.md` output
- `chunks_pending` — still need processing
- `merged` — whether the final merged file exists

Documents marked `INCOMPLETE` still need work — rerun with `--skip-existing`.

**Watch the live log:**

```bash
tail -f pipeline_output/1968/run.log
```

Press `Ctrl + C` to stop watching (does not stop the main job).

---

## Step 7 — Merge into one document per meeting

After all chunks for a meeting are extracted, the tool **merges** them into one file:

```
pipeline_output/1968/<pdf-name>/final/<pdf-name>.md
```

This is the **complete structured table** for the whole meeting (header row once, all speech rows appended in order). This merged file is the primary deliverable per meeting.

**Rebuild merged files** (if extractions exist but `final/` is missing):

```bash
python -m pipeline pipeline_output/1968 --merge-only
```

---

## Stop, resume, and troubleshoot

**Stop a running job:** click the Terminal window → press `Ctrl + C`.

**Resume after stopping or an error:**

```bash
python -m pipeline pipeline_output/1968 --extract-only --skip-existing
```

**Common issues:**

| Problem | Fix |
|---------|-----|
| `GEMINI_API_KEY is not set` | Edit `.env` — see First-time setup → Step D |
| `no chunk folders found` | Use `pipeline_output/1968`, not `pipeline_output` alone |
| `Server disconnected` | Wait, then rerun resume command |
| Run stops, no new files | API budget may be exhausted — check Google AI Studio |
| `zsh: command not found: #` | Don't paste lines starting with `#` — those are comments |

---

# First-time setup (do this once)

## A — Install Python

1. Go to **https://www.python.org/downloads/**
2. Download and install Python 3.
3. Verify in Terminal:

```bash
python3 --version
```

## B — Get the project

**From GitHub:** https://github.com/lianlinton/gemini-automation → Code → Download ZIP → unzip to Documents.

**Or** use the folder you already have at `~/Documents/datasquad/gemini-automation`.

## C — Install dependencies

```bash
cd ~/Documents/datasquad/gemini-automation
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## D — Add API key

```bash
cp .env.example .env
open -a TextEdit .env
```

Replace `your-api-key-here` with your Gemini API key from [Google AI Studio](https://aistudio.google.com/). Save and close.

**Never** share or upload the `.env` file.

---

## Cost and time

- Each chunk costs API credit (PDF input + table output tokens).
- A full year of minutes can be **500+ chunks** and take **many hours**.
- A $30 budget may not cover everything — check progress and spending in Google AI Studio.
- Test with one short PDF before running the full batch.

---

## If something still fails

Before retrying, note:

1. The last 10–20 lines of Terminal output (or a screenshot).
2. Output of: `find pipeline_output/1968 -path "*/extractions/*.md" | wc -l`
3. Contents of `processing_summary.json` (if it exists).

Do **not** share or commit the `.env` file or API key.
