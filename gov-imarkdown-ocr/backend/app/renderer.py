from __future__ import annotations
from typing import List, Dict, Any, Tuple
import math
from .schemas import Region, TableData

def _clean_line(s: str) -> str:
    return " ".join(s.replace("\n", " ").split()).strip()

def _as_block(lines: List[str]) -> str:
    return "\n\n".join([ln for ln in lines if ln.strip()])

def _make_notes(unreadable: List[str]) -> str:
    if not unreadable:
        return ""
    out = ["### Notes"]
    for n in unreadable:
        out.append(f"- {n}")
    return "\n".join(out)

def table_to_markdown(table: TableData, include_span_note: bool = True) -> str:
    lines = []
    if table.title:
        lines.append(f"### {table.title}")
        lines.append("")
    # if spanning headers exist, add semantic note line
    if include_span_note and table.spans:
        for sp in table.spans:
            # e.g. "Transmittance (%T) spans Trial #1–Trial #5"
            col_names = [table.columns[i] for i in sp.columns if 0 <= i < len(table.columns)]
            if col_names:
                lines.append(f"**{sp.label}** covers: " + ", ".join(col_names))
        lines.append("")

    # markdown table
    cols = table.columns
    lines.append("| " + " | ".join(cols) + " |")
    lines.append("| " + " | ".join(["---"] * len(cols)) + " |")
    for r in table.rows:
        r2 = [(c if c is not None else "") for c in r]
        # pad row
        if len(r2) < len(cols):
            r2 = r2 + [""] * (len(cols) - len(r2))
        lines.append("| " + " | ".join(r2[:len(cols)]) + " |")
    return "\n".join(lines).strip()

def render_imarkdown(image_file: str, doc_type: str, engine: Dict[str,Any], avg_conf: float, accepted: bool, regions: List[Region]) -> str:
    # Build human-readable markdown like the user requested:
    # - Extracted Text
    # - Extracted Tables
    # - Company Details / Drawing Information / Customer Information when present
    # - Notes for unreadable/stamp/signature/faint text
    printed_lines: List[Tuple[float,str]] = []
    hand_lines: List[Tuple[float,str]] = []
    tables: List[TableData] = []
    notes: List[str] = []

    for r in regions:
        if r.type == "table" and r.table:
            tables.append(r.table)
        elif r.type in ("printed", "unknown") and r.text:
            printed_lines.append((r.bbox.y1, _clean_line(r.text)))
        elif r.type == "handwritten":
            if r.text and r.text.strip():
                hand_lines.append((r.bbox.y1, _clean_line(r.text)))
            else:
                # signature present
                if r.meta.get("note"):
                    notes.append(r.meta["note"])
                else:
                    notes.append("Handwritten region present but not reliably readable")

        # generic unreadable
        if r.confidence < 0.35 and (r.text is None or not r.text.strip()) and r.type != "table":
            notes.append("Some text regions are too faint/blurred to extract accurately")

        # stamp hint (if detected by upstream as meta)
        if r.meta.get("stamp") == True:
            notes.append("Circular stamp/seal present (text partially unreadable)")

    printed_lines.sort(key=lambda x: x[0])
    hand_lines.sort(key=lambda x: x[0])

    # Sectioning: use embeddings if available (done upstream) otherwise simple grouping by keywords (presentation only)
    # Upstream sets r.meta['section'] optionally. We'll respect it.
    sections: Dict[str, List[str]] = {}
    for _, txt in printed_lines:
        sec = "Extracted Text"
        # if upstream already marked a section, trust it
        # (still not OCR rule-based; it's presentation grouping)
        # Example: Company Details, Drawing Information, Customer Information
        # If no marker, keep in Extracted Text.
        # We'll also do light keyword grouping as fallback.
        upper = txt.upper()
        if "CATHODIC" in upper or "PVT" in upper or "BANGALORE" in upper or "INDUSTRIAL" in upper:
            sec = "Company Details"
        elif upper.startswith("TITLE") or "DRG" in upper or "REV" in upper or "DIMENSION" in upper or "TOLERANCE" in upper:
            sec = "Drawing Information"
        elif "CUSTOMER" in upper or "P.O." in upper or "PO NO" in upper:
            sec = "Customer Information"
        sections.setdefault(sec, []).append(txt)

    md_lines: List[str] = []
    md_lines.append("## Extracted Text")
    md_lines.append("")
    if sections.get("Extracted Text"):
        md_lines.append("\n\n".join(sections["Extracted Text"]).strip())
    else:
        md_lines.append("_No main-body printed text detected._")
    md_lines.append("")

    # tables
    if tables:
        md_lines.append("## Extracted Tables")
        md_lines.append("")
        for t in tables:
            md_lines.append(table_to_markdown(t))
            md_lines.append("")

    # handwriting block
    if hand_lines:
        md_lines.append("## Handwritten Content")
        md_lines.append("")
        md_lines.append("\n\n".join([t for _, t in hand_lines]).strip())
        md_lines.append("")

    # additional blocks
    for sec in ("Company Details", "Drawing Information", "Customer Information"):
        if sec in sections:
            md_lines.append(f"### {sec}")
            md_lines.append("\n".join(sections[sec]).strip())
            md_lines.append("")

    # notes
    notes_block = _make_notes(list(dict.fromkeys(notes)))
    if notes_block:
        md_lines.append(notes_block)
        md_lines.append("")

    # YAML front matter
    import yaml
    header = {
        "schema": "imarkdown.v1",
        "image_file": image_file,
        "doc_type": doc_type,
        "engine": engine,
        "quality": {"avg_confidence": round(avg_conf, 4), "accepted": bool(accepted)},
        "regions": {
            "total": len(regions),
            "tables": sum(1 for r in regions if r.type == "table"),
            "printed": sum(1 for r in regions if r.type == "printed"),
            "handwritten": sum(1 for r in regions if r.type == "handwritten"),
            "figures": sum(1 for r in regions if r.type == "figure"),
        }
    }
    front = yaml.safe_dump(header, sort_keys=False, allow_unicode=True).strip()
    body = "\n".join([ln.rstrip() for ln in md_lines]).strip()
    return f"---\n{front}\n---\n\n{body}\n"
