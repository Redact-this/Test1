"""OCR-kern: laden, voorbewerken en herkennen van afbeeldingen en PDF's.

Deze module is bewust GUI-vrij zodat ze ook headless (CLI/tests) bruikbaar is.
"""

from __future__ import annotations

import importlib.util
import os
from dataclasses import dataclass, field
from typing import Callable, Iterable

import pytesseract
from PIL import Image, ImageFilter, ImageOps

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".gif", ".webp"}
PDF_EXTENSIONS = {".pdf"}
SUPPORTED_EXTENSIONS = IMAGE_EXTENSIONS | PDF_EXTENSIONS

# Tesseract-taalcodes voor de ondersteunde talen.
LANGUAGES = {
    "nld": "Nederlands",
    "eng": "Engels",
    "fra": "Frans",
}

# Beschikbare OCR-engines. "auto" draait Tesseract én EasyOCR en kiest het
# resultaat met de hoogste betrouwbaarheid.
ENGINES = {
    "auto": "Automatisch (beide, beste resultaat)",
    "tesseract": "Tesseract (snel)",
    "easyocr": "EasyOCR (foto's, moeilijke scans)",
}

# EasyOCR gebruikt andere taalcodes dan Tesseract.
EASYOCR_LANG_CODES = {"nld": "nl", "eng": "en", "fra": "fr"}

# Page segmentation modes die in de praktijk het nuttigst zijn.
PSM_MODES = {
    "Automatisch": 3,
    "Eén tekstblok": 6,
    "Eén tekstregel": 7,
    "Losse woorden": 11,
}

MIN_OCR_WIDTH = 1200  # kleinere afbeeldingen worden opgeschaald voor betere herkenning


@dataclass
class OcrResult:
    """Resultaat van één pagina/afbeelding."""

    source: str
    page: int
    text: str
    confidence: float  # gemiddelde woordconfidence (0-100), -1 als onbekend


@dataclass
class OcrOptions:
    languages: list[str] = field(default_factory=lambda: ["nld", "eng", "fra"])
    psm: int = 3
    preprocess: bool = True
    binarize: bool = False
    pdf_dpi: int = 300
    # Probeer elke taal ook afzonderlijk en kies het betrouwbaarste resultaat.
    # Trager, maar nauwkeuriger bij accenten (bijv. ç, é) in gemengde selecties.
    auto_best: bool = False
    engine: str = "tesseract"  # zie ENGINES

    @property
    def lang_string(self) -> str:
        langs = [l for l in self.languages if l in LANGUAGES]
        return "+".join(langs) if langs else "nld+eng+fra"


def otsu_threshold(gray: Image.Image) -> int:
    """Bepaal de Otsu-drempelwaarde uit het histogram van een grijswaardenbeeld."""
    hist = gray.histogram()
    total = sum(hist)
    if total == 0:
        return 128
    sum_all = sum(i * h for i, h in enumerate(hist))
    sum_bg = 0.0
    weight_bg = 0
    best_threshold, best_variance = 128, 0.0
    for i in range(256):
        weight_bg += hist[i]
        if weight_bg == 0:
            continue
        weight_fg = total - weight_bg
        if weight_fg == 0:
            break
        sum_bg += i * hist[i]
        mean_bg = sum_bg / weight_bg
        mean_fg = (sum_all - sum_bg) / weight_fg
        variance = weight_bg * weight_fg * (mean_bg - mean_fg) ** 2
        if variance > best_variance:
            best_variance = variance
            best_threshold = i
    return best_threshold


def preprocess_image(image: Image.Image, binarize: bool = False) -> Image.Image:
    """Voorbewerking die de herkenning meestal verbetert.

    - EXIF-rotatie toepassen
    - naar grijswaarden
    - opschalen als de afbeelding klein is
    - contrast normaliseren en licht verscherpen
    - optioneel binariseren met Otsu
    """
    image = ImageOps.exif_transpose(image)
    gray = ImageOps.grayscale(image)

    if gray.width < MIN_OCR_WIDTH:
        scale = MIN_OCR_WIDTH / gray.width
        new_size = (MIN_OCR_WIDTH, max(1, round(gray.height * scale)))
        gray = gray.resize(new_size, Image.LANCZOS)

    gray = ImageOps.autocontrast(gray, cutoff=1)
    gray = gray.filter(ImageFilter.SHARPEN)

    if binarize:
        threshold = otsu_threshold(gray)
        gray = gray.point(lambda p: 255 if p > threshold else 0)

    return gray


def ocr_image(image: Image.Image, options: OcrOptions) -> tuple[str, float]:
    """Voer OCR uit op één afbeelding; geeft (tekst, gemiddelde confidence)."""
    if options.preprocess:
        image = preprocess_image(image, binarize=options.binarize)

    if options.engine == "easyocr":
        return _ocr_easyocr(image, options)
    if options.engine == "auto" and easyocr_available():
        tess = _ocr_tesseract(image, options)
        easy = _ocr_easyocr(image, options)
        return tess if tess[1] >= easy[1] else easy
    return _ocr_tesseract(image, options)


def _ocr_tesseract(image: Image.Image, options: OcrOptions) -> tuple[str, float]:
    langs = [l for l in options.languages if l in LANGUAGES]
    if options.auto_best and len(langs) > 1:
        candidates = [options.lang_string] + langs
        best: tuple[str, float] | None = None
        for lang in candidates:
            result = _ocr_single(image, lang, options.psm)
            if best is None or result[1] > best[1]:
                best = result
        assert best is not None
        return best

    return _ocr_single(image, options.lang_string, options.psm)


def _ocr_single(image: Image.Image, lang: str, psm: int) -> tuple[str, float]:
    config = f"--psm {psm}"
    data = pytesseract.image_to_data(
        image,
        lang=lang,
        config=config,
        output_type=pytesseract.Output.DICT,
    )

    # Tekst reconstrueren met behoud van regel- en blokstructuur.
    lines: list[str] = []
    current_key = None
    current_words: list[str] = []
    confidences: list[float] = []
    for i, word in enumerate(data["text"]):
        word = word.strip()
        if not word:
            continue
        conf = float(data["conf"][i])
        if conf >= 0:
            confidences.append(conf)
        key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
        if key != current_key:
            if current_words:
                lines.append(" ".join(current_words))
            if current_key is not None and key[:2] != current_key[:2]:
                lines.append("")  # lege regel tussen alinea's/blokken
            current_key = key
            current_words = []
        current_words.append(word)
    if current_words:
        lines.append(" ".join(current_words))

    text = "\n".join(lines).strip()
    avg_conf = sum(confidences) / len(confidences) if confidences else -1.0
    return text, avg_conf


def easyocr_available() -> bool:
    """Is het optionele easyocr-pakket geïnstalleerd?"""
    return importlib.util.find_spec("easyocr") is not None


_easyocr_readers: dict[tuple[str, ...], object] = {}


def _get_easyocr_reader(langs: list[str]):
    """EasyOCR-reader per taalcombinatie; initialisatie is duur, dus cachen."""
    import easyocr

    codes = [EASYOCR_LANG_CODES[l] for l in langs if l in EASYOCR_LANG_CODES]
    if not codes:
        codes = list(EASYOCR_LANG_CODES.values())
    key = tuple(sorted(codes))
    if key not in _easyocr_readers:
        try:
            import torch

            gpu = torch.cuda.is_available()
        except Exception:
            gpu = False
        _easyocr_readers[key] = easyocr.Reader(codes, gpu=gpu, verbose=False)
    return _easyocr_readers[key]


def _ocr_easyocr(image: Image.Image, options: OcrOptions) -> tuple[str, float]:
    """OCR via EasyOCR, met reconstructie van tekstregels uit de losse tekstvakken."""
    if not easyocr_available():
        raise RuntimeError(
            "EasyOCR is niet geïnstalleerd. Installeer het met: pip install easyocr"
        )
    import numpy as np

    reader = _get_easyocr_reader([l for l in options.languages if l in LANGUAGES])
    detections = reader.readtext(np.asarray(image.convert("RGB")))
    if not detections:
        return "", -1.0

    # Per tekstvak: (x-links, y-midden, hoogte, tekst, confidence)
    items = []
    for box, text, conf in detections:
        xs = [point[0] for point in box]
        ys = [point[1] for point in box]
        items.append((min(xs), (min(ys) + max(ys)) / 2, max(ys) - min(ys), text, conf))

    # Vakken waarvan de y-middens dicht bij elkaar liggen vormen samen één regel.
    heights = sorted(item[2] for item in items)
    line_tolerance = max(1.0, 0.6 * heights[len(heights) // 2])
    items.sort(key=lambda item: item[1])
    lines: list[list[tuple]] = []
    for item in items:
        if lines and abs(item[1] - lines[-1][-1][1]) <= line_tolerance:
            lines[-1].append(item)
        else:
            lines.append([item])

    text_lines = [
        " ".join(word[3] for word in sorted(line, key=lambda word: word[0]))
        for line in lines
    ]
    confidences = [item[4] for item in items]
    avg_conf = 100.0 * sum(confidences) / len(confidences)
    return "\n".join(text_lines).strip(), avg_conf


def load_pdf_pages(path: str, dpi: int = 300) -> Iterable[Image.Image]:
    """Render de pagina's van een PDF als afbeeldingen."""
    import pypdfium2 as pdfium

    pdf = pdfium.PdfDocument(path)
    try:
        for page in pdf:
            yield page.render(scale=dpi / 72).to_pil()
            page.close()
    finally:
        pdf.close()


def ocr_file(
    path: str,
    options: OcrOptions,
    progress: Callable[[str], None] | None = None,
) -> list[OcrResult]:
    """Voer OCR uit op een afbeelding of PDF; geeft één resultaat per pagina."""
    ext = os.path.splitext(path)[1].lower()
    name = os.path.basename(path)
    results: list[OcrResult] = []

    if ext in PDF_EXTENSIONS:
        for page_no, image in enumerate(load_pdf_pages(path, options.pdf_dpi), start=1):
            if progress:
                progress(f"{name} – pagina {page_no}…")
            text, conf = ocr_image(image, options)
            results.append(OcrResult(path, page_no, text, conf))
    elif ext in IMAGE_EXTENSIONS:
        if progress:
            progress(f"{name}…")
        with Image.open(path) as image:
            n_frames = getattr(image, "n_frames", 1)
            for frame in range(n_frames):  # multi-page TIFF
                image.seek(frame)
                text, conf = ocr_image(image.convert("RGB"), options)
                results.append(OcrResult(path, frame + 1, text, conf))
    else:
        raise ValueError(f"Niet-ondersteund bestandstype: {ext}")

    return results


def tesseract_available() -> tuple[bool, str]:
    """Controleer of Tesseract bereikbaar is; geeft (ok, versie-of-foutmelding)."""
    try:
        version = pytesseract.get_tesseract_version()
        return True, str(version)
    except Exception as exc:  # pragma: no cover - afhankelijk van systeem
        return False, str(exc)


def missing_languages() -> list[str]:
    """Welke van de gewenste taalpakketten ontbreken in de Tesseract-installatie."""
    try:
        installed = set(pytesseract.get_languages(config=""))
    except Exception:
        return []
    return [code for code in LANGUAGES if code not in installed]
