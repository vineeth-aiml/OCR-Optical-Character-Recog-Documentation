from __future__ import annotations
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from PIL import Image
import io, uuid, json
from pathlib import Path
from typing import List

from .config import settings
from .models import ModelBundle
from .pipeline import run_pipeline
from .pdf_utils import pdf_bytes_to_images

app = FastAPI(title="Gov iMarkdown OCR (Offline)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # lock down in BEL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MODELS: ModelBundle | None = None

@app.on_event("startup")
def load_models():
    global MODELS
    MODELS = ModelBundle(
        trocr_print_dir=str(settings.trocr_print_dir),
        trocr_hand_dir=str(settings.trocr_hand_dir),
        table_det_dir=str(settings.table_det_dir),
        table_struct_dir=str(settings.table_struct_dir),
        embeddings_dir=str(settings.embeddings_dir) if settings.embeddings_dir.exists() else None,
        device_pref=settings.device,
    )

@app.get("/health")
def health():
    return {"ok": True, "device": MODELS.device if MODELS else "not_loaded"}

def _save_outputs(file_id: str, payload: dict):
    out_md = settings.outputs_dir / f"{file_id}.md"
    out_json = settings.outputs_dir / f"{file_id}.json"
    out_md.write_text(payload["markdown"], encoding="utf-8")
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

@app.get("/api/output/{file_id}")
def get_output(file_id: str, kind: str = "md"):
    if kind not in ("md", "json"):
        return JSONResponse({"error": "kind must be md or json"}, status_code=400)
    path = settings.outputs_dir / f"{file_id}.{kind}"
    if not path.exists():
        return JSONResponse({"error": "not found"}, status_code=404)
    if kind == "md":
        return PlainTextResponse(path.read_text(encoding="utf-8"))
    return JSONResponse(json.loads(path.read_text(encoding="utf-8")))

@app.post("/api/convert")
async def convert(file: UploadFile = File(...)):
    if MODELS is None:
        return JSONResponse({"error": "Models not loaded"}, status_code=500)

    data = await file.read()
    ext = Path(file.filename).suffix.lower()
    file_id = str(uuid.uuid4())

    # save upload
    stored = settings.uploads_dir / f"{file_id}{ext or ''}"
    stored.write_bytes(data)

    # pdf?
    if ext == ".pdf" or file.content_type == "application/pdf":
        try:
            pages = pdf_bytes_to_images(data, dpi=settings.pdf_dpi)
        except Exception as e:
            return JSONResponse({"error": f"PDF render failed (poppler): {e}"}, status_code=400)

        page_results = []
        for i, img in enumerate(pages, start=1):
            result = run_pipeline(MODELS, img, filename=f"{file.filename}#page={i}",
                                  accept_threshold=settings.accept_threshold,
                                  min_region_conf=settings.min_region_conf)
            page_id = f"{file_id}_p{i}"
            payload = {
                "id": page_id,
                "filename": f"{file.filename}#page={i}",
                "doc_type": result["doc_type"],
                "avg_confidence": round(result["avg_confidence"], 4),
                "accepted": result["accepted"],
                "engine": result["engine"],
                "markdown": result["markdown"],
                "regions": result["regions"],
            }
            _save_outputs(page_id, payload)
            page_results.append(payload)

        combined_md = "\n\n---\n\n".join([p["markdown"] for p in page_results])
        combined = {
            "id": file_id,
            "filename": file.filename,
            "type": "pdf",
            "pages": len(page_results),
            "page_results": page_results,
            "combined_markdown": combined_md,
        }
        _save_outputs(file_id, {"markdown": combined_md, "combined": combined})
        return combined

    # image
    try:
        img = Image.open(io.BytesIO(data)).convert("RGB")
    except Exception as e:
        return JSONResponse({"error": f"Invalid image: {e}"}, status_code=400)

    result = run_pipeline(MODELS, img, filename=file.filename,
                          accept_threshold=settings.accept_threshold,
                          min_region_conf=settings.min_region_conf)
    payload = {
        "id": file_id,
        "filename": file.filename,
        "doc_type": result["doc_type"],
        "avg_confidence": round(result["avg_confidence"], 4),
        "accepted": result["accepted"],
        "engine": result["engine"],
        "markdown": result["markdown"],
        "regions": result["regions"],
    }
    _save_outputs(file_id, payload)
    return payload

@app.post("/api/batch")
async def batch_convert(files: List[UploadFile] = File(...)):
    if MODELS is None:
        return JSONResponse({"error": "Models not loaded"}, status_code=500)

    all_items = []
    combined_blocks = []

    for f in files:
        data = await f.read()
        ext = Path(f.filename).suffix.lower()
        file_id = str(uuid.uuid4())

        stored = settings.uploads_dir / f"{file_id}{ext or ''}"
        stored.write_bytes(data)

        if ext == ".pdf" or f.content_type == "application/pdf":
            pages = pdf_bytes_to_images(data, dpi=settings.pdf_dpi)
            page_results = []
            for i, img in enumerate(pages, start=1):
                result = run_pipeline(MODELS, img, filename=f"{f.filename}#page={i}",
                                      accept_threshold=settings.accept_threshold,
                                      min_region_conf=settings.min_region_conf)
                page_id = f"{file_id}_p{i}"
                payload = {
                    "id": page_id,
                    "filename": f"{f.filename}#page={i}",
                    "doc_type": result["doc_type"],
                    "avg_confidence": round(result["avg_confidence"], 4),
                    "accepted": result["accepted"],
                    "engine": result["engine"],
                    "markdown": result["markdown"],
                    "regions": result["regions"],
                }
                _save_outputs(page_id, payload)
                page_results.append(payload)
                combined_blocks.append(payload["markdown"])

            all_items.append({
                "id": file_id,
                "filename": f.filename,
                "type": "pdf",
                "pages": len(page_results),
                "page_results": page_results
            })
        else:
            try:
                img = Image.open(io.BytesIO(data)).convert("RGB")
            except Exception as e:
                all_items.append({"id": file_id, "filename": f.filename, "type": "image", "error": str(e)})
                continue

            result = run_pipeline(MODELS, img, filename=f.filename,
                                  accept_threshold=settings.accept_threshold,
                                  min_region_conf=settings.min_region_conf)
            payload = {
                "id": file_id,
                "filename": f.filename,
                "doc_type": result["doc_type"],
                "avg_confidence": round(result["avg_confidence"], 4),
                "accepted": result["accepted"],
                "engine": result["engine"],
                "markdown": result["markdown"],
                "regions": result["regions"],
            }
            _save_outputs(file_id, payload)
            all_items.append({"id": file_id, "filename": f.filename, "type": "image", "result": payload})
            combined_blocks.append(payload["markdown"])

    combined_markdown = "\n\n---\n\n".join(combined_blocks)
    batch_id = str(uuid.uuid4())
    _save_outputs(batch_id, {"markdown": combined_markdown, "items": all_items})
    return {"id": batch_id, "count": len(all_items), "items": all_items, "combined_markdown": combined_markdown}
