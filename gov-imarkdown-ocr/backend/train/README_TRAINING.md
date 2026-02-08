# Offline fine-tuning TrOCR (client scan styles)

Goal: improve printed OCR accuracy for your specific scanners, fonts, stamps, low-contrast scans.

## Data format
Create cropped line/word images and ground-truth.

```
backend/train/data/
  train/
    images/
      000001.png
      ...
    labels.csv
  val/
    images/
    labels.csv
```

labels.csv:
```csv
file,text
000001.png,Government of India Department ...
000002.png,Name: John Doe
```

## Run training (GPU recommended)
```bash
cd backend/train
python finetune_trocr.py --base ../../models/trocr_print --out ../../models/trocr_print_finetuned --data ./data
```

Then update backend config:
- set `models/trocr_print_finetuned/` as `trocr_print_dir`.
