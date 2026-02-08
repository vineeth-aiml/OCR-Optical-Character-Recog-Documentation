from __future__ import annotations
import torch
from transformers import TrOCRProcessor, VisionEncoderDecoderModel
from transformers import DetrImageProcessor, TableTransformerForObjectDetection
from craft_text_detector import Craft

try:
    from sentence_transformers import SentenceTransformer
except Exception:
    SentenceTransformer = None

class ModelBundle:
    def __init__(self, trocr_print_dir: str, trocr_hand_dir: str, table_det_dir: str, table_struct_dir: str,
                 embeddings_dir: str | None, device_pref: str = "cuda"):

        self.device = device_pref if (device_pref == "cuda" and torch.cuda.is_available()) else "cpu"

        if self.device == "cuda":
            torch.backends.cudnn.benchmark = True

        # OCR models
        self.print_processor = TrOCRProcessor.from_pretrained(trocr_print_dir)
        self.print_model = VisionEncoderDecoderModel.from_pretrained(trocr_print_dir).to(self.device).eval()

        self.hand_processor = TrOCRProcessor.from_pretrained(trocr_hand_dir)
        self.hand_model = VisionEncoderDecoderModel.from_pretrained(trocr_hand_dir).to(self.device).eval()

        # Optional fp16
        if self.device == "cuda":
            self.print_model.half()
            self.hand_model.half()

        # Table models
        self.table_det_processor = DetrImageProcessor.from_pretrained(table_det_dir)
        self.table_det_model = TableTransformerForObjectDetection.from_pretrained(table_det_dir).to(self.device).eval()

        self.table_struct_processor = DetrImageProcessor.from_pretrained(table_struct_dir)
        self.table_struct_model = TableTransformerForObjectDetection.from_pretrained(table_struct_dir).to(self.device).eval()

        if self.device == "cuda":
            self.table_det_model.half()
            self.table_struct_model.half()

        # Text detector
        self.craft = Craft(output_dir=None, crop_type="poly", cuda=(self.device == "cuda"))

        # Optional embeddings for section grouping
        self.embedder = None
        if embeddings_dir and SentenceTransformer is not None:
            try:
                self.embedder = SentenceTransformer(embeddings_dir, device=self.device)
            except Exception:
                self.embedder = None

    @torch.inference_mode()
    def ocr_print(self, pil_img):
        return self._trocr_single(pil_img, self.print_processor, self.print_model)

    @torch.inference_mode()
    def ocr_hand(self, pil_img):
        return self._trocr_single(pil_img, self.hand_processor, self.hand_model)

    def _trocr_single(self, pil_img, processor, model):
        pv = processor(images=pil_img, return_tensors="pt").pixel_values.to(self.device)
        use_amp = (self.device == "cuda")
        with torch.autocast(device_type="cuda", dtype=torch.float16, enabled=use_amp):
            gen = model.generate(
                pv,
                output_scores=True,
                return_dict_in_generate=True,
                max_new_tokens=128,
                num_beams=3
            )
        text = processor.batch_decode(gen.sequences, skip_special_tokens=True)[0].strip()
        conf = _sequence_confidence(gen)
        return text, conf

def _sequence_confidence(gen_out) -> float:
    scores = gen_out.scores
    if not scores:
        return 0.0
    probs = []
    for s in scores:
        p = torch.softmax(s[0].float(), dim=-1).max().item()
        probs.append(p)
    return float(sum(probs)/len(probs))
