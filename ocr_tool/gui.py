"""Tkinter-GUI voor de OCR-tool."""

from __future__ import annotations

import os
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageTk

from . import __version__, engine

FILETYPES = [
    ("Alle ondersteunde bestanden", "*.png *.jpg *.jpeg *.tif *.tiff *.bmp *.gif *.webp *.pdf"),
    ("Afbeeldingen", "*.png *.jpg *.jpeg *.tif *.tiff *.bmp *.gif *.webp"),
    ("PDF-documenten", "*.pdf"),
    ("Alle bestanden", "*.*"),
]

PREVIEW_MAX = (520, 640)


class OcrApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"OCR-tool {__version__} – Nederlands · Engels · Frans")
        self.geometry("1200x760")
        self.minsize(900, 600)

        self.files: list[str] = []
        self.results_queue: queue.Queue = queue.Queue()
        self.worker: threading.Thread | None = None
        self.cancel_event = threading.Event()
        self._preview_photo: ImageTk.PhotoImage | None = None

        self.lang_vars = {
            code: tk.BooleanVar(value=True) for code in engine.LANGUAGES
        }
        self.preprocess_var = tk.BooleanVar(value=True)
        self.binarize_var = tk.BooleanVar(value=False)
        self.auto_best_var = tk.BooleanVar(value=True)
        self.easyocr_ok = engine.easyocr_available()
        self.engine_var = tk.StringVar(value="auto" if self.easyocr_ok else "tesseract")
        self.psm_var = tk.StringVar(value="Automatisch")
        self.dpi_var = tk.IntVar(value=300)

        self._build_ui()
        self._check_tesseract()

    # ------------------------------------------------------------------ UI --
    def _build_ui(self) -> None:
        root = ttk.Frame(self, padding=8)
        root.pack(fill="both", expand=True)

        # Linkerkolom: bestanden + opties
        left = ttk.Frame(root, width=290)
        left.pack(side="left", fill="y", padx=(0, 8))
        left.pack_propagate(False)

        files_frame = ttk.LabelFrame(left, text="Bestanden", padding=6)
        files_frame.pack(fill="both", expand=True)

        self.file_list = tk.Listbox(files_frame, selectmode="extended", activestyle="none")
        self.file_list.pack(fill="both", expand=True)
        self.file_list.bind("<<ListboxSelect>>", self._on_select_file)

        file_buttons = ttk.Frame(files_frame)
        file_buttons.pack(fill="x", pady=(6, 0))
        ttk.Button(file_buttons, text="Toevoegen…", command=self.add_files).pack(
            side="left", fill="x", expand=True
        )
        ttk.Button(file_buttons, text="Verwijderen", command=self.remove_selected).pack(
            side="left", fill="x", expand=True, padx=(6, 0)
        )

        engine_frame = ttk.LabelFrame(left, text="OCR-engine", padding=6)
        engine_frame.pack(fill="x", pady=(8, 0))
        for value, label in engine.ENGINES.items():
            state = "normal" if (self.easyocr_ok or value == "tesseract") else "disabled"
            ttk.Radiobutton(
                engine_frame, text=label, value=value, variable=self.engine_var, state=state
            ).pack(anchor="w")
        if not self.easyocr_ok:
            ttk.Label(
                engine_frame,
                text="EasyOCR niet geïnstalleerd:\npip install easyocr",
                foreground="gray",
            ).pack(anchor="w", pady=(4, 0))

        lang_frame = ttk.LabelFrame(left, text="Talen", padding=6)
        lang_frame.pack(fill="x", pady=(8, 0))
        for code, label in engine.LANGUAGES.items():
            ttk.Checkbutton(lang_frame, text=label, variable=self.lang_vars[code]).pack(
                anchor="w"
            )

        options_frame = ttk.LabelFrame(left, text="Opties", padding=6)
        options_frame.pack(fill="x", pady=(8, 0))
        ttk.Checkbutton(
            options_frame, text="Voorbewerking (aanbevolen)", variable=self.preprocess_var
        ).pack(anchor="w")
        ttk.Checkbutton(
            options_frame,
            text="Binariseren (voor scans met vlekken)",
            variable=self.binarize_var,
        ).pack(anchor="w")
        ttk.Checkbutton(
            options_frame,
            text="Beste taal automatisch kiezen (trager)",
            variable=self.auto_best_var,
        ).pack(anchor="w")

        psm_row = ttk.Frame(options_frame)
        psm_row.pack(fill="x", pady=(6, 0))
        ttk.Label(psm_row, text="Paginalayout:").pack(side="left")
        ttk.Combobox(
            psm_row,
            textvariable=self.psm_var,
            values=list(engine.PSM_MODES),
            state="readonly",
            width=16,
        ).pack(side="right")

        dpi_row = ttk.Frame(options_frame)
        dpi_row.pack(fill="x", pady=(6, 0))
        ttk.Label(dpi_row, text="PDF-resolutie (dpi):").pack(side="left")
        ttk.Spinbox(
            dpi_row, from_=150, to=600, increment=50, textvariable=self.dpi_var, width=6
        ).pack(side="right")

        self.start_button = ttk.Button(
            left, text="▶  Start OCR", command=self.start_ocr
        )
        self.start_button.pack(fill="x", pady=(10, 0))
        self.cancel_button = ttk.Button(
            left, text="Annuleren", command=self.cancel_ocr, state="disabled"
        )
        self.cancel_button.pack(fill="x", pady=(4, 0))

        self.progress = ttk.Progressbar(left, mode="determinate")
        self.progress.pack(fill="x", pady=(8, 0))

        # Rechterkant: voorbeeld + tekst
        paned = ttk.PanedWindow(root, orient="horizontal")
        paned.pack(side="left", fill="both", expand=True)

        preview_frame = ttk.LabelFrame(paned, text="Voorbeeld", padding=4)
        self.preview_label = ttk.Label(preview_frame, anchor="center")
        self.preview_label.pack(fill="both", expand=True)
        paned.add(preview_frame, weight=1)

        text_frame = ttk.LabelFrame(paned, text="Herkende tekst", padding=4)
        paned.add(text_frame, weight=2)

        self.text = tk.Text(text_frame, wrap="word", undo=True, font=("TkDefaultFont", 11))
        scrollbar = ttk.Scrollbar(text_frame, command=self.text.yview)
        self.text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.text.pack(fill="both", expand=True)

        text_buttons = ttk.Frame(text_frame)
        text_buttons.pack(fill="x", pady=(6, 0))
        ttk.Button(text_buttons, text="Kopiëren", command=self.copy_text).pack(side="left")
        ttk.Button(text_buttons, text="Opslaan als…", command=self.save_text).pack(
            side="left", padx=(6, 0)
        )
        ttk.Button(text_buttons, text="Wissen", command=lambda: self.text.delete("1.0", "end")).pack(
            side="left", padx=(6, 0)
        )

        self.status_var = tk.StringVar(value="Klaar.")
        ttk.Label(self, textvariable=self.status_var, anchor="w", padding=(8, 2)).pack(
            fill="x", side="bottom"
        )

    def _check_tesseract(self) -> None:
        ok, info = engine.tesseract_available()
        if not ok:
            messagebox.showerror(
                "Tesseract niet gevonden",
                "Tesseract OCR is niet geïnstalleerd of niet vindbaar in PATH.\n\n"
                "Installeer het via https://tesseract-ocr.github.io/ en start de tool opnieuw.\n\n"
                f"Details: {info}",
            )
            return
        missing = engine.missing_languages()
        if missing:
            names = ", ".join(engine.LANGUAGES[c] for c in missing)
            messagebox.showwarning(
                "Taalpakketten ontbreken",
                f"De volgende Tesseract-taalpakketten ontbreken: {names}.\n"
                "Installeer ze (bijv. tesseract-ocr-nld / -fra / -eng) voor de beste resultaten.",
            )
        self.status_var.set(f"Klaar. Tesseract {info} gevonden.")

    # --------------------------------------------------------------- acties --
    def add_files(self) -> None:
        paths = filedialog.askopenfilenames(title="Bestanden kiezen", filetypes=FILETYPES)
        for path in paths:
            if path not in self.files:
                self.files.append(path)
                self.file_list.insert("end", os.path.basename(path))
        self._update_status_files()

    def remove_selected(self) -> None:
        for index in reversed(self.file_list.curselection()):
            self.file_list.delete(index)
            del self.files[index]
        self._update_status_files()

    def _update_status_files(self) -> None:
        self.status_var.set(f"{len(self.files)} bestand(en) in de lijst.")

    def _on_select_file(self, _event=None) -> None:
        selection = self.file_list.curselection()
        if not selection:
            return
        path = self.files[selection[0]]
        try:
            ext = os.path.splitext(path)[1].lower()
            if ext in engine.PDF_EXTENSIONS:
                image = next(iter(engine.load_pdf_pages(path, dpi=100)))
            else:
                with Image.open(path) as img:
                    image = img.convert("RGB")
            image.thumbnail(PREVIEW_MAX, Image.LANCZOS)
            self._preview_photo = ImageTk.PhotoImage(image)
            self.preview_label.configure(image=self._preview_photo, text="")
        except Exception as exc:
            self.preview_label.configure(image="", text=f"Geen voorbeeld: {exc}")

    def _collect_options(self) -> engine.OcrOptions | None:
        languages = [code for code, var in self.lang_vars.items() if var.get()]
        if not languages:
            messagebox.showwarning("Geen taal", "Kies minstens één taal.")
            return None
        return engine.OcrOptions(
            languages=languages,
            psm=engine.PSM_MODES.get(self.psm_var.get(), 3),
            preprocess=self.preprocess_var.get(),
            binarize=self.binarize_var.get(),
            pdf_dpi=self.dpi_var.get(),
            auto_best=self.auto_best_var.get(),
            engine=self.engine_var.get(),
        )

    def start_ocr(self) -> None:
        if self.worker and self.worker.is_alive():
            return
        if not self.files:
            messagebox.showinfo("Geen bestanden", "Voeg eerst één of meer bestanden toe.")
            return
        options = self._collect_options()
        if options is None:
            return

        self.cancel_event.clear()
        self.start_button.configure(state="disabled")
        self.cancel_button.configure(state="normal")
        self.progress.configure(maximum=len(self.files), value=0)
        self.text.delete("1.0", "end")

        files = list(self.files)
        self.worker = threading.Thread(
            target=self._worker_run, args=(files, options), daemon=True
        )
        self.worker.start()
        self.after(100, self._poll_queue)

    def cancel_ocr(self) -> None:
        self.cancel_event.set()
        self.status_var.set("Bezig met annuleren…")

    def _worker_run(self, files: list[str], options: engine.OcrOptions) -> None:
        for index, path in enumerate(files, start=1):
            if self.cancel_event.is_set():
                break
            try:
                results = engine.ocr_file(
                    path,
                    options,
                    progress=lambda msg: self.results_queue.put(("status", msg)),
                )
                self.results_queue.put(("result", path, results))
            except Exception as exc:
                self.results_queue.put(("error", path, str(exc)))
            self.results_queue.put(("progress", index))
        self.results_queue.put(("done", self.cancel_event.is_set()))

    def _poll_queue(self) -> None:
        try:
            while True:
                item = self.results_queue.get_nowait()
                kind = item[0]
                if kind == "status":
                    self.status_var.set(f"Bezig: {item[1]}")
                elif kind == "progress":
                    self.progress.configure(value=item[1])
                elif kind == "result":
                    _, path, results = item
                    self._append_results(path, results)
                elif kind == "error":
                    _, path, message = item
                    self.text.insert(
                        "end", f"⚠ Fout bij {os.path.basename(path)}: {message}\n\n"
                    )
                elif kind == "done":
                    cancelled = item[1]
                    self.start_button.configure(state="normal")
                    self.cancel_button.configure(state="disabled")
                    self.status_var.set(
                        "Geannuleerd." if cancelled else "Klaar. Alle bestanden verwerkt."
                    )
                    return
        except queue.Empty:
            pass
        self.after(100, self._poll_queue)

    def _append_results(self, path: str, results: list[engine.OcrResult]) -> None:
        name = os.path.basename(path)
        multiple = len(self.files) > 1 or len(results) > 1
        for result in results:
            if multiple:
                header = name if len(results) == 1 else f"{name} – pagina {result.page}"
                if result.confidence >= 0:
                    header += f"  (betrouwbaarheid {result.confidence:.0f}%)"
                self.text.insert("end", f"───── {header} ─────\n")
            self.text.insert("end", (result.text or "(geen tekst gevonden)") + "\n\n")
        self.text.see("end")

    def copy_text(self) -> None:
        content = self.text.get("1.0", "end-1c")
        if not content:
            return
        self.clipboard_clear()
        self.clipboard_append(content)
        self.status_var.set("Tekst gekopieerd naar het klembord.")

    def save_text(self) -> None:
        content = self.text.get("1.0", "end-1c")
        if not content:
            messagebox.showinfo("Niets op te slaan", "Er is nog geen herkende tekst.")
            return
        path = filedialog.asksaveasfilename(
            title="Tekst opslaan",
            defaultextension=".txt",
            filetypes=[("Tekstbestand", "*.txt"), ("Alle bestanden", "*.*")],
        )
        if not path:
            return
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(content)
        self.status_var.set(f"Opgeslagen als {path}")


def main() -> None:
    app = OcrApp()
    app.mainloop()


if __name__ == "__main__":
    main()
