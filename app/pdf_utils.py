import fitz  # PyMuPDF


def extract_text_from_pdf_bytes(pdf_bytes: bytes, max_pages: int = 3) -> str:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    texts = []
    for i in range(min(len(doc), max_pages)):
        t = (doc[i].get_text("text") or "").strip()
        if t:
            texts.append(t)
    doc.close()
    return "\n\n".join(texts).strip()


def render_pdf_pages_to_images(pdf_bytes: bytes, max_pages: int = 2, dpi: int = 220) -> list[bytes]:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    images = []
    zoom = dpi / 72
    mat = fitz.Matrix(zoom, zoom)
    for i in range(min(len(doc), max_pages)):
        pix = doc[i].get_pixmap(matrix=mat, alpha=False)
        images.append(pix.tobytes("png"))
    doc.close()
    return imagesimport fitz  # PyMuPDF


def extract_text_from_pdf_bytes(pdf_bytes: bytes, max_pages: int = 3) -> str:
    """
    Estrae testo vero da PDF (se presente).
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    texts = []
    for i in range(min(len(doc), max_pages)):
        page = doc[i]
        t = page.get_text("text") or ""
        t = t.strip()
        if t:
            texts.append(t)
    doc.close()
    return "\n\n".join(texts).strip()


def render_pdf_pages_to_images(pdf_bytes: bytes, max_pages: int = 2, dpi: int = 220) -> list[bytes]:
    """
    Converte le prime pagine del PDF in immagini PNG (per OCR).
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    images = []
    zoom = dpi / 72  # 72 dpi base
    mat = fitz.Matrix(zoom, zoom)

    for i in range(min(len(doc), max_pages)):
        page = doc[i]
        pix = page.get_pixmap(matrix=mat, alpha=False)
        images.append(pix.tobytes("png"))

    doc.close()
    return images
