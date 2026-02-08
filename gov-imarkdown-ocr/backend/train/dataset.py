from __future__ import annotations
from torch.utils.data import Dataset
from PIL import Image
import pandas as pd
from pathlib import Path

class OcrLineDataset(Dataset):
    def __init__(self, root: str, processor, max_len: int = 128):
        self.root = Path(root)
        self.df = pd.read_csv(self.root / "labels.csv")
        self.img_dir = self.root / "images"
        self.processor = processor
        self.max_len = max_len

    def __len__(self):
        return len(self.df)

    def __getitem__(self, idx):
        row = self.df.iloc[idx]
        img = Image.open(self.img_dir / row["file"]).convert("RGB")
        text = str(row["text"])

        pixel_values = self.processor(images=img, return_tensors="pt").pixel_values.squeeze(0)
        labels = self.processor.tokenizer(
            text,
            return_tensors="pt",
            padding="max_length",
            truncation=True,
            max_length=self.max_len
        ).input_ids.squeeze(0)

        labels[labels == self.processor.tokenizer.pad_token_id] = -100
        return {"pixel_values": pixel_values, "labels": labels}
