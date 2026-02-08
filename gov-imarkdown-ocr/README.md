# Gov iMarkdown OCR (Offline) — BEL-ready

Offline system to convert **images + PDFs** (scans/photos) into:
- **iMarkdown** (`.md`): YAML header + clean Markdown body
- **JSON** (`.json`): regions, boxes, confidences, tables incl. spanning headers, per-page outputs for PDFs

Supports:
- printed text (TrOCR printed)
- handwriting (TrOCR handwritten)
- tables (Table Transformer detection + structure recognition + cell OCR)
- mixed pages (diagrams + labels + stamps + tables)

## 1) Offline model folders (copy into `models/`)
Download on an internet machine, then copy folders to air-gapped BEL box.

Required (HuggingFace local dirs):
- `models/trocr_print/`  (e.g. microsoft/trocr-base-printed)
- `models/trocr_hand/`   (e.g. microsoft/trocr-base-handwritten)
- `models/table_det/`    (e.g. microsoft/table-transformer-detection)
- `models/table_struct/` (e.g. microsoft/table-transformer-structure-recognition)

Optional (for smarter section grouping):
- `models/embeddings/` (e.g. sentence-transformers/all-MiniLM-L6-v2)

### Download commands (internet machine)
```bash
pip install -U "huggingface_hub[cli]"
huggingface-cli download microsoft/trocr-base-printed --local-dir trocr_print
huggingface-cli download microsoft/trocr-base-handwritten --local-dir trocr_hand
huggingface-cli download microsoft/table-transformer-detection --local-dir table_det
huggingface-cli download microsoft/table-transformer-structure-recognition --local-dir table_struct
huggingface-cli download sentence-transformers/all-MiniLM-L6-v2 --local-dir embeddings
```
Copy these directories into `models/` on BEL.

## 2) System dependencies (BEL offline)
### Poppler (PDF → images)
- Ubuntu/Debian: `sudo apt-get install poppler-utils`
- RHEL/CentOS: `sudo yum install poppler-utils`

## 3) Backend (FastAPI)
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
```
> Use `--workers 1` on GPU to avoid loading models multiple times.

Open:
- Health: `GET /health`
- API docs: `/docs`

## 4) Frontend (React + Vite)
```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```
Frontend uses proxy to backend.

## 5) Endpoints
- `POST /api/convert` — single image or PDF (multi-page)
- `POST /api/batch` — multiple images + PDFs (multi-page)
- `GET /api/output/{id}` — fetch saved `.md` / `.json` metadata

## 6) Output rules (Gov-safe)
- Never hallucinate unreadable text.
- Low confidence → mark as `[UNREADABLE]` and add a Notes section.
- Spanning/merged header cells are preserved in JSON, and rendered in Markdown as a semantic line or multi-header rows.

## 7) Fine-tuning TrOCR (offline)
See `backend/train/README_TRAINING.md`.
