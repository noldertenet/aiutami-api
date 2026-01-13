import io
from PIL import Image, ImageOps
import pytesseract
import cv2
import numpy as np


def _preprocess(img: Image.Image) -> Image.Image:
    """
    Pre-processing semplice ma efficace per foto di documenti:
    - grayscale
    - autocontrast
    - blur leggero
    - sogliatura Otsu
    """
    gray = ImageOps.grayscale(img)
    gray = ImageOps.autocontrast(gray)

    arr = np.array(gray)
    arr = cv2.GaussianBlur(arr, (3, 3), 0)
    _, thr = cv2.threshold(arr, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    return Image.fromarray(thr)


def ocr_image_bytes(image_bytes: bytes) -> str:
    """
    Estrae testo da bytes immagine (jpg/png/webp).
    Usa Tesseract in lingua italiana.
    """
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    proc = _preprocess(img)

    # --psm 6: assume blocco di testo uniforme
    config = "--oem 1 --psm 6"
    text = pytesseract.image_to_string(proc, lang="ita", config=config)

    return (text or "").strip()
