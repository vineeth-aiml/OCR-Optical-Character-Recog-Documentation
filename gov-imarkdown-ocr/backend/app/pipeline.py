from __future__ import annotations
from PIL import Image
import torch
from typing import List, Tuple, Dict, Any
from .schemas import Region, BBox, TableData, TableSpan
from .utils import pil_to_cv, cv_to_pil, deskew_cv, normalize_for_ocr, crop_pil, sort_boxes_reading_order, iou
from .renderer import render_imarkdown

def detect_tables(models, img: Image.Image, score_thresh: float = 0.75) -> List[Tuple[int,int,int,int,float]]:
    inputs = models.table_det_processor(images=img, return_tensors="pt").to(models.device)
    outputs = models.table_det_model(**inputs)
    target_sizes = torch.tensor([img.size[::-1]], device=models.device)
    results = models.table_det_processor.post_process_object_detection(outputs, threshold=score_thresh, target_sizes=target_sizes)[0]
    boxes = results["boxes"].detach().cpu().tolist()
    scores = results["scores"].detach().cpu().tolist()
    labels = results["labels"].detach().cpu().tolist()
    out = []
    for b, s, lab in zip(boxes, scores, labels):
        # label 0 typically "table"
        if int(lab) == 0:
            x1,y1,x2,y2 = map(int, b)
            out.append((x1,y1,x2,y2,float(s)))
    return out

def detect_text_boxes(models, img: Image.Image) -> List[Tuple[int,int,int,int]]:
    cv_img = pil_to_cv(img)
    pred = models.craft.detect_text(cv_img)
    polys = pred.get("boxes", [])
    out = []
    for poly in polys:
        xs = [p[0] for p in poly]
        ys = [p[1] for p in poly]
        x1,y1,x2,y2 = int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))
        if (x2-x1) >= 10 and (y2-y1) >= 10:
            out.append((x1,y1,x2,y2))
    return sort_boxes_reading_order(out)

def structure_table(models, table_img: Image.Image, score_thresh: float = 0.70) -> Dict[str, Any]:
    inputs = models.table_struct_processor(images=table_img, return_tensors="pt").to(models.device)
    outputs = models.table_struct_model(**inputs)
    target_sizes = torch.tensor([table_img.size[::-1]], device=models.device)
    results = models.table_struct_processor.post_process_object_detection(outputs, threshold=score_thresh, target_sizes=target_sizes)[0]

    boxes = results["boxes"].detach().cpu().tolist()
    scores = results["scores"].detach().cpu().tolist()
    labels = results["labels"].detach().cpu().tolist()
    id2label = models.table_struct_model.config.id2label

    rows, cols, spanning = [], [], []
    col_headers = []
    for b, s, lab in zip(boxes, scores, labels):
        name = id2label[int(lab)].lower()
        x1,y1,x2,y2 = map(int, b)
        if "table row" == name:
            rows.append((x1,y1,x2,y2,float(s)))
        elif "table column" == name:
            cols.append((x1,y1,x2,y2,float(s)))
        elif "spanning" in name:
            spanning.append((x1,y1,x2,y2,float(s), name))
        elif "column header" in name:
            col_headers.append((x1,y1,x2,y2,float(s)))

    rows = sorted(rows, key=lambda r: r[1])
    cols = sorted(cols, key=lambda c: c[0])

    return {"rows": rows, "cols": cols, "spanning": spanning, "col_headers": col_headers}

def build_grid(rows, cols):
    grid = []
    for r in rows:
        rx1,ry1,rx2,ry2,_ = r
        row_cells = []
        for c in cols:
            cx1,cy1,cx2,cy2,_ = c
            x1 = max(rx1, cx1); y1 = max(ry1, cy1)
            x2 = min(rx2, cx2); y2 = min(ry2, cy2)
            if x2 > x1 and y2 > y1:
                row_cells.append((x1,y1,x2,y2))
            else:
                row_cells.append((0,0,0,0))
        grid.append(row_cells)
    return grid

def ocr_cell(models, img: Image.Image) -> tuple[str, float]:
    txt, conf = models.ocr_print(img)
    return txt.replace("\n", " ").strip(), float(conf)

def grid_to_table(models, table_img: Image.Image, grid):
    confs = []
    rows_out = []
    for row in grid:
        out_row = []
        for cell in row:
            x1,y1,x2,y2 = cell
            if x2-x1 < 2 or y2-y1 < 2:
                out_row.append("")
                continue
            crop = crop_pil(table_img, (x1,y1,x2,y2))
            t, c = ocr_cell(models, crop)
            out_row.append(t)
            if t:
                confs.append(c)
        rows_out.append(out_row)

    # choose header row as first non-empty-ish row
    header_idx = 0
    for i, r in enumerate(rows_out[:3]):
        if sum(1 for x in r if x.strip()) >= max(2, len(r)//3):
            header_idx = i
            break

    header = rows_out[header_idx]
    body = rows_out[header_idx+1:]

    # trim empty columns
    if not header:
        header = [""] * len(rows_out[0])
    keep = []
    for j in range(len(header)):
        if (header[j].strip() or any((j < len(r) and r[j].strip()) for r in body)):
            keep.append(j)
    header = [header[j] for j in keep]
    body2 = []
    for r in body:
        body2.append([(r[j] if j < len(r) else "") for j in keep])

    avg_conf = float(sum(confs)/len(confs)) if confs else 0.0
    return header, body2, avg_conf

def detect_spans(models, table_img: Image.Image, table_struct: Dict[str,Any], columns: List[str]) -> List[TableSpan]:
    spans = []
    # If the model detects spanning cells, OCR them and map to column indices by overlap with columns
    cols = table_struct["cols"]
    for (x1,y1,x2,y2,s,name) in table_struct.get("spanning", []):
        crop = crop_pil(table_img, (x1,y1,x2,y2))
        label, c = models.ocr_print(crop)
        label = label.strip()
        if not label:
            continue
        # map to columns by overlap with col boxes
        covered = []
        for idx, col in enumerate(cols):
            cx1,cy1,cx2,cy2,_ = col
            # overlap in x
            ox1 = max(x1,cx1); ox2 = min(x2,cx2)
            if ox2 > ox1:
                covered.append(idx)
        covered = sorted(set(covered))
        if len(covered) >= 2:
            spans.append(TableSpan(label=label, columns=covered, bbox=BBox(x1=x1,y1=y1,x2=x2,y2=y2), confidence=float(min(1.0,(s+c)/2.0))))
    return spans

def run_pipeline(models, image: Image.Image, filename: str, accept_threshold: float, min_region_conf: float):
    # preprocess
    bgr = pil_to_cv(image)
    bgr = deskew_cv(bgr)
    bgr = normalize_for_ocr(bgr)
    img = cv_to_pil(bgr)

    regions: List[Region] = []
    confs: List[float] = []

    # 1) tables
    tables = detect_tables(models, img)
    table_boxes = [(x1,y1,x2,y2) for x1,y1,x2,y2,_ in tables]

    for i, (x1,y1,x2,y2,sc) in enumerate(tables):
        crop = crop_pil(img, (x1,y1,x2,y2))
        st = structure_table(models, crop)
        if len(st["rows"]) >= 2 and len(st["cols"]) >= 2:
            grid = build_grid(st["rows"], st["cols"])
            cols, rows, ocr_conf = grid_to_table(models, crop, grid)
            spans = detect_spans(models, crop, st, cols)

            # attempt title: OCR top strip above table if exists by cropping a bit above bbox in original image
            title = None
            # keep as None unless confident; upstream could provide better title detection
            md_dummy = TableData(title=title, columns=cols, rows=rows, spans=spans, markdown="")
            from .renderer import table_to_markdown
            md = table_to_markdown(md_dummy, include_span_note=True)
            table_data = TableData(title=title, columns=cols, rows=rows, spans=spans, markdown=md)

            conf = float(min(1.0, (sc + ocr_conf)/2.0))
        else:
            # fallback: whole-table OCR
            txt, c = models.ocr_print(crop)
            table_data = TableData(title=None, columns=["Table OCR"], rows=[[txt.strip()]], spans=[], markdown=txt.strip())
            conf = float(min(1.0, (sc + c)/2.0))

        regions.append(Region(
            id=f"table_{i+1}",
            type="table",
            bbox=BBox(x1=x1,y1=y1,x2=x2,y2=y2),
            confidence=conf,
            table=table_data,
            meta={"det_score": sc}
        ))
        confs.append(conf)

    # 2) text boxes (exclude table areas)
    text_boxes = detect_text_boxes(models, img)
    filtered = []
    for b in text_boxes:
        if any(iou(b, tb) > 0.30 for tb in table_boxes):
            continue
        filtered.append(b)

    # 3) OCR each text region with both models and choose higher confidence
    for i, (x1,y1,x2,y2) in enumerate(filtered):
        crop = crop_pil(img, (x1,y1,x2,y2))
        t1, c1 = models.ocr_print(crop)
        t2, c2 = models.ocr_hand(crop)

        if c2 > c1:
            text, conf, typ = t2, float(c2), "handwritten"
        else:
            text, conf, typ = t1, float(c1), "printed"

        text = text.strip()
        if conf < min_region_conf and not text:
            continue

        regions.append(Region(
            id=f"text_{i+1}",
            type=typ,
            bbox=BBox(x1=x1,y1=y1,x2=x2,y2=y2),
            confidence=conf,
            text=text if text else None,
            meta={}
        ))
        if text:
            confs.append(conf)

    # doc summary
    avg_conf = float(sum(confs)/len(confs)) if confs else 0.0
    types = {r.type for r in regions} if regions else {"unknown"}
    doc_type = "mixed" if len(types) > 1 else list(types)[0]
    accepted = avg_conf >= accept_threshold

    engine = {
        "text_detector": "CRAFT",
        "ocr_print": "TrOCR printed",
        "ocr_hand": "TrOCR handwritten",
        "table_detection": "TableTransformer detection",
        "table_structure": "TableTransformer structure",
        "preprocess": ["deskew", "clahe-contrast"]
    }

    md = render_imarkdown(
        image_file=filename,
        doc_type=doc_type,
        engine=engine,
        avg_conf=avg_conf,
        accepted=accepted,
        regions=regions
    )

    return {
        "doc_type": doc_type,
        "avg_confidence": avg_conf,
        "accepted": accepted,
        "markdown": md,
        "regions": [r.model_dump() for r in regions],
        "engine": engine
    }
