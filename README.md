# Gov iMarkdown OCR — Offline, Layout-Aware OCR to iMarkdown

An **offline / air-gapped OCR system** that converts **images and PDFs** (scans or photos) into:

- **iMarkdown (`.md`)** — clean Markdown with YAML front-matter
- **JSON (`.json`)** — structured, auditable extraction (regions, tables, confidences)

Built for **government, enterprise, and compliance** environments where **data must never leave the premises**.

---

## Why this project exists (intuition)

Most OCR systems fail on **real documents** because they:

- ignore layout,
- flatten tables into unreadable text,
- give no confidence or audit trail.

This project is **layout-first**:

1. **Detect tables first** → extract them as real tables  
2. **Detect text regions** → OCR each region independently  
3. **Preserve structure + confidence** → auditable, review-ready output  

If you can trust the structure, you can automate downstream workflows.

---

## What you get

- Works **fully offline**
- Handles **printed + handwritten text**
- Extracts **tables as Markdown tables**
- Produces **confidence-scored, reviewable outputs**
- Supports **single files and batch processing**

---

## High-level architecture

Input (PDF / Image)
│
▼
Preprocessing
(deskew, normalize)
│
▼
Layout Detection
├─ Table Detection (TableTransformer)
└─ Text Detection (CRAFT)
│
▼
Region-wise OCR
├─ Table Structure → Cell OCR
└─ Text Regions → TrOCR (printed + handwritten)
│
▼
Renderer
(YAML + Markdown + JSON)
│
▼
Offline Storage
(.md, .json)





---

## Repository structure

gov-imarkdown-ocr/
│
├─ backend/
│ ├─ app/
│ │ ├─ main.py # FastAPI entrypoint
│ │ ├─ pipeline.py # end-to-end OCR pipeline
│ │ ├─ models.py # offline model loading
│ │ ├─ renderer.py # iMarkdown generation
│ │ ├─ pdf_utils.py # PDF → images
│ │ ├─ utils.py # image + bbox utilities
│ │ ├─ config.py # latency/accuracy knobs
│ │ └─ schemas.py # data contracts
│ │
│ └─ train/
│ ├─ finetune_trocr.py
│ └─ README_TRAINING.md
│
├─ frontend/
│ └─ src/
│ ├─ App.jsx
│ ├─ components/
│ └─ api.js
│
├─ models/ # local HF model folders (offline)
└─ storage/
└─ outputs/ # generated .md and .json


---

## Offline models (required)

Download once on an **internet machine**, then copy folders into `models/`.

- TrOCR (printed)
- TrOCR (handwritten)
- TableTransformer (detection)
- TableTransformer (structure)

Example (internet machine):

```bash
huggingface-cli download microsoft/trocr-base-printed \
  --local-dir trocr_print

huggingface-cli download microsoft/trocr-base-handwritten \
  --local-dir trocr_hand

huggingface-cli download microsoft/table-transformer-detection \
  --local-dir table_det

huggingface-cli download microsoft/table-transformer-structure-recognition \
  --local-dir table_struct


## Running the system
Backend (FastAPI)
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1

Use 1 worker on GPU to avoid loading large models multiple times.

Frontend (React)
cd frontend
npm install
npm run dev
API overview
Convert single file

POST /api/convert

Input: image or PDF

Output:

extracted Markdown

JSON with regions, tables, confidences

Batch conversion

POST /api/batch

Input: multiple files

Output:

per-file results

combined Markdown

Fetch stored outputs

GET /api/output/{id}?kind=md|json

End-to-end processing (deep intuition)
1. Preprocessing (cheap accuracy boost)

Deskew

Contrast normalization

Why:
OCR accuracy improves dramatically with minimal compute cost.

2. Table detection (layout first)

Model: TableTransformer (detection)

Finds table regions

Reserves them before text OCR

Tradeoff

Lower threshold → more tables, more false positives

Higher threshold → fewer tables, risk of missing light borders

3. Table structure recognition

Model: TableTransformer (structure)

Detects rows, columns, headers, spans

Builds a grid

OCRs each cell independently

Fallback:

If structure fails → OCR whole table as text block

Why this works

Prevents column drift

Preserves machine-readable tables

4. Text detection (non-table)

Model: CRAFT

Finds text boxes

Removes overlap with tables

5. OCR (printed + handwritten)

Models:

TrOCR Printed

TrOCR Handwritten

For each text region:

Run both models

Select result with higher confidence

Tradeoff

Higher latency

Much better mixed-content accuracy

6. Confidence & acceptance gating

Compute average confidence

Mark document as accepted / needs review

Used for:

automated pipelines

human-in-the-loop queues

Output formats
iMarkdown (.md)

YAML front-matter:

engine

confidence

region counts

Sections:

Extracted Text

Extracted Tables

Handwritten Content

JSON (.json)

Includes:

bounding boxes

per-region confidence

table grids and spans

per-page PDF results

Perfect for:

UI overlays

audit trails

downstream ETL

Latency vs accuracy tradeoffs
Biggest latency contributors

TrOCR decoding

Number of detected regions

Table cell OCR count

PDF DPI

Key tuning knobs
Variable	Effect
IMD_PDF_DPI	↑ DPI = ↑ accuracy, ↑ latency
IMD_ACCEPT_THRESHOLD	↑ strictness
IMD_MIN_REGION_CONF	filters faint/noisy text
Presets

Fast

IMD_PDF_DPI=200
IMD_ACCEPT_THRESHOLD=0.80

Balanced (recommended)

IMD_PDF_DPI=300
IMD_ACCEPT_THRESHOLD=0.85

Accuracy-first

IMD_PDF_DPI=400
IMD_ACCEPT_THRESHOLD=0.88
Accuracy expectations

Best for:

clean scans

printed forms

structured tables

Hard cases:

heavy blur

shadows

cursive handwriting

nested multi-row tables

Improving accuracy (most impact)

Better scans (300 DPI, minimal compression)

Fine-tune TrOCR on your document templates

Adjust region confidence thresholds

Security & compliance

No internet calls at runtime

Models loaded from local disk

All files stored on-prem

Suitable for air-gapped BEL / govt environments

Known limitations

Complex multi-level table headers

Very faint stamps

No multilingual routing yet

Roadmap ideas

bbox overlay preview

semantic section grouping

caching repeated templates

multilingual OCR routing

License & attribution

Uses offline deployments of:

TrOCR

TableTransformer

CRAFT

FastAPI, React

Ensure compliance with individual model licenses.
