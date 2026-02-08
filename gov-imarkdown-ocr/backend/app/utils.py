from __future__ import annotations
import numpy as np
import cv2
from PIL import Image
from typing import List, Tuple

def pil_to_cv(img: Image.Image) -> np.ndarray:
    arr = np.array(img.convert("RGB"))
    return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)

def cv_to_pil(img: np.ndarray) -> Image.Image:
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    return Image.fromarray(rgb)

def deskew_cv(bgr: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5,5), 0)
    thr = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    coords = np.column_stack(np.where(thr > 0))
    if coords.size == 0:
        return bgr
    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle
    h, w = bgr.shape[:2]
    M = cv2.getRotationMatrix2D((w//2, h//2), angle, 1.0)
    return cv2.warpAffine(bgr, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

def normalize_for_ocr(bgr: np.ndarray) -> np.ndarray:
    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    l2 = clahe.apply(l)
    lab2 = cv2.merge((l2, a, b))
    return cv2.cvtColor(lab2, cv2.COLOR_LAB2BGR)

def crop_pil(img: Image.Image, box: Tuple[int,int,int,int]) -> Image.Image:
    x1,y1,x2,y2 = box
    x1 = max(0, x1); y1 = max(0, y1)
    x2 = min(img.size[0], x2); y2 = min(img.size[1], y2)
    return img.crop((x1,y1,x2,y2))

def sort_boxes_reading_order(boxes: List[Tuple[int,int,int,int]]) -> List[Tuple[int,int,int,int]]:
    return sorted(boxes, key=lambda b: (b[1]//25, b[0]))

def iou(a, b) -> float:
    ax1,ay1,ax2,ay2 = a; bx1,by1,bx2,by2 = b
    ix1,iy1,ix2,iy2 = max(ax1,bx1), max(ay1,by1), min(ax2,bx2), min(ay2,by2)
    if ix2 <= ix1 or iy2 <= iy1:
        return 0.0
    inter = (ix2-ix1)*(iy2-iy1)
    area_a = (ax2-ax1)*(ay2-ay1)
    area_b = (bx2-bx1)*(by2-by1)
    return inter / float(area_a + area_b - inter + 1e-6)
