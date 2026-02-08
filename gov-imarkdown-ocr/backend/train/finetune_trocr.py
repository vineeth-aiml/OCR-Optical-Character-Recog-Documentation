from __future__ import annotations
import argparse
import torch
from transformers import TrOCRProcessor, VisionEncoderDecoderModel, Trainer, TrainingArguments
from dataset import OcrLineDataset

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True, help="path to base TrOCR local dir (printed or handwritten)")
    ap.add_argument("--out", required=True, help="output dir for fine-tuned model")
    ap.add_argument("--data", required=True, help="dataset root containing train/ and val/")
    ap.add_argument("--epochs", type=int, default=5)
    args = ap.parse_args()

    device = "cuda" if torch.cuda.is_available() else "cpu"

    processor = TrOCRProcessor.from_pretrained(args.base)
    model = VisionEncoderDecoderModel.from_pretrained(args.base).to(device)

    train_ds = OcrLineDataset(f"{args.data}/train", processor)
    val_ds = OcrLineDataset(f"{args.data}/val", processor)

    targs = TrainingArguments(
        output_dir=args.out,
        per_device_train_batch_size=8 if device=="cuda" else 2,
        per_device_eval_batch_size=8 if device=="cuda" else 2,
        num_train_epochs=args.epochs,
        evaluation_strategy="epoch",
        save_strategy="epoch",
        learning_rate=5e-5,
        fp16=(device=="cuda"),
        logging_steps=50,
        save_total_limit=2,
        report_to=[],
    )

    trainer = Trainer(model=model, args=targs, train_dataset=train_ds, eval_dataset=val_ds)
    trainer.train()
    trainer.save_model(args.out)
    processor.save_pretrained(args.out)
    print("Saved fine-tuned model:", args.out)

if __name__ == "__main__":
    main()
