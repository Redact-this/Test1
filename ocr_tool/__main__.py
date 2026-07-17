"""Startpunt: `python -m ocr_tool` opent de GUI.

Met bestandsargumenten draait de tool headless en print hij de tekst:
    python -m ocr_tool scan.pdf foto.jpg --lang nld+fra
"""

from __future__ import annotations

import argparse
import sys

from . import engine


def run_cli(
    paths: list[str],
    lang: str,
    psm: int,
    no_preprocess: bool,
    dpi: int,
    auto_best: bool,
    ocr_engine: str,
) -> int:
    options = engine.OcrOptions(
        languages=lang.split("+"),
        psm=psm,
        preprocess=not no_preprocess,
        pdf_dpi=dpi,
        auto_best=auto_best,
        engine=ocr_engine,
    )
    exit_code = 0
    for path in paths:
        try:
            for result in engine.ocr_file(path, options):
                if len(paths) > 1 or result.page > 1:
                    print(f"===== {path} – pagina {result.page} =====", file=sys.stderr)
                print(result.text)
        except Exception as exc:
            print(f"Fout bij {path}: {exc}", file=sys.stderr)
            exit_code = 1
    return exit_code


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="ocr_tool",
        description="OCR-tool voor Nederlands, Engels en Frans. Zonder argumenten opent de GUI.",
    )
    parser.add_argument("paths", nargs="*", help="afbeeldingen of PDF's (headless modus)")
    parser.add_argument("--lang", default="nld+eng+fra", help="talen, bijv. nld+fra")
    parser.add_argument("--psm", type=int, default=3, help="Tesseract page segmentation mode")
    parser.add_argument("--no-preprocess", action="store_true", help="voorbewerking uitschakelen")
    parser.add_argument("--dpi", type=int, default=300, help="renderresolutie voor PDF's")
    parser.add_argument(
        "--auto-best",
        action="store_true",
        help="probeer elke taal apart en kies het betrouwbaarste resultaat",
    )
    parser.add_argument(
        "--engine",
        choices=list(engine.ENGINES),
        default="tesseract",
        help="OCR-engine: auto draait Tesseract én EasyOCR en kiest het beste resultaat",
    )
    args = parser.parse_args()

    if args.paths:
        return run_cli(
            args.paths,
            args.lang,
            args.psm,
            args.no_preprocess,
            args.dpi,
            args.auto_best,
            args.engine,
        )

    from .gui import main as gui_main

    gui_main()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
