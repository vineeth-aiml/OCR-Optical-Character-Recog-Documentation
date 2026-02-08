from pydantic import BaseModel
from typing import List, Literal, Optional, Dict, Any

RegionType = Literal["printed", "handwritten", "table", "figure", "unknown"]

class BBox(BaseModel):
    x1: int
    y1: int
    x2: int
    y2: int

class TableSpan(BaseModel):
    label: str
    columns: List[int]          # indices of columns spanned
    bbox: Optional[BBox] = None
    confidence: float = 0.0

class TableData(BaseModel):
    title: Optional[str] = None
    columns: List[str]
    rows: List[List[str]]
    spans: List[TableSpan] = []
    markdown: str

class Region(BaseModel):
    id: str
    type: RegionType
    bbox: BBox
    confidence: float
    text: Optional[str] = None
    table: Optional[TableData] = None
    meta: Dict[str, Any] = {}

class OutputDoc(BaseModel):
    schema: str = "imarkdown.v1"
    image_file: str
    doc_type: str
    engine: Dict[str, Any]
    quality: Dict[str, Any]
    regions: List[Region]
    markdown: str
