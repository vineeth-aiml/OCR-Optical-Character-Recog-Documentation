from pydantic import BaseModel
from pathlib import Path
import os

class Settings(BaseModel):
    project_root: Path = Path(__file__).resolve().parents[2]
    models_dir: Path = project_root / "models"
    storage_dir: Path = project_root / "storage"
    uploads_dir: Path = storage_dir / "uploads"
    outputs_dir: Path = storage_dir / "outputs"

    trocr_print_dir: Path = models_dir / "trocr_print"
    trocr_hand_dir: Path = models_dir / "trocr_hand"
    table_det_dir: Path = models_dir / "table_det"
    table_struct_dir: Path = models_dir / "table_struct"
    embeddings_dir: Path = models_dir / "embeddings"  # optional

    device: str = os.environ.get("IMD_DEVICE", "cuda")  # "cuda" or "cpu"
    pdf_dpi: int = int(os.environ.get("IMD_PDF_DPI", "300"))
    accept_threshold: float = float(os.environ.get("IMD_ACCEPT_THRESHOLD", "0.85"))
    min_region_conf: float = float(os.environ.get("IMD_MIN_REGION_CONF", "0.35"))

settings = Settings()
settings.uploads_dir.mkdir(parents=True, exist_ok=True)
settings.outputs_dir.mkdir(parents=True, exist_ok=True)
