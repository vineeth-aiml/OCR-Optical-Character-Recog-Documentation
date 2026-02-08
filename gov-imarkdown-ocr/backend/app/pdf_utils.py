from __future__ import annotations
from typing import List
from pdf2image import convert_from_bytes
from PIL import Image

def pdf_bytes_to_images(pdf_bytes: bytes, dpi: int = 300) -> List[Image.Image]:
    pages = convert_from_bytes(pdf_bytes, dpi=dpi, fmt="png")
    return [p.convert("RGB") for p in pages]
