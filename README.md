# OCR-tool – Nederlands · Engels · Frans

Een OCR-tool met grafische interface (Tkinter) die tekst herkent uit
afbeeldingen **en PDF's**, gericht op Nederlands, Engels en Frans.
Gebouwd op [Tesseract 5](https://tesseract-ocr.github.io/) met automatische
beeldvoorbewerking voor betere resultaten.

## Functies

- **Afbeeldingen én PDF's**: PNG, JPG, TIFF (ook multi-page), BMP, GIF, WebP en PDF.
- **Twee OCR-engines, drie standen**:
  - *Automatisch* — draait Tesseract én EasyOCR en houdt per pagina het
    resultaat met de hoogste betrouwbaarheid over (nauwkeurigst, trager);
  - *Tesseract* — snel en licht, ideaal voor nette scans van gedrukte tekst;
  - *EasyOCR* — neuraal model, sterker bij foto's en moeilijke scans
    (optioneel; werkt pas na `pip install easyocr`).
- **Drie talen, ook gecombineerd**: vink Nederlands, Engels en/of Frans aan;
  gemengde documenten worden met meerdere talen tegelijk herkend.
- **Beste taal automatisch kiezen**: probeert elke aangevinkte taal ook apart
  en houdt het betrouwbaarste resultaat over — nauwkeuriger bij accenten
  (ç, é, ï) als meerdere talen aangevinkt zijn.
- **Batchverwerking**: meerdere bestanden in één keer, met voortgangsbalk en
  annuleerknop; de OCR draait in een aparte thread zodat het venster niet bevriest.
- **Slimme voorbewerking**: EXIF-rotatie, grijswaarden, opschalen van kleine
  afbeeldingen, contrastnormalisatie en verscherping. Optioneel Otsu-binarisatie
  voor vlekkerige scans.
- **Layoutbehoud**: regels en alinea's blijven behouden in de uitvoer, met per
  bestand/pagina een betrouwbaarheidsscore.
- **Voorbeeldweergave** van het geselecteerde bestand (ook de eerste PDF-pagina).
- **Exporteren**: tekst kopiëren naar het klembord of opslaan als .txt.
- **Ook headless bruikbaar**: geef bestandsnamen mee op de commandline en de
  tekst wordt naar stdout geschreven.

## Installatie

### 1. Tesseract OCR + taalpakketten

- **Windows**: installer via <https://github.com/UB-Mannheim/tesseract/wiki>
  (kies bij de installatie de talen *Dutch*, *French*; *English* zit er standaard bij).
- **macOS**: `brew install tesseract tesseract-lang`
- **Debian/Ubuntu**: `sudo apt install tesseract-ocr tesseract-ocr-nld tesseract-ocr-fra`

### 2. Python-afhankelijkheden

Python 3.10+ met Tkinter (zit standaard bij de meeste Python-installaties;
op Debian/Ubuntu: `sudo apt install python3-tk`).

```bash
pip install -r requirements.txt
```

### 3. Optioneel: EasyOCR (voor de standen *Automatisch* en *EasyOCR*)

```bash
pip install easyocr
```

Let op: dit haalt ook PyTorch binnen (een grote download). Bij het eerste
gebruik downloadt EasyOCR bovendien eenmalig zijn modelbestanden (~100 MB);
daarvoor is een internetverbinding nodig. Zonder GPU is EasyOCR duidelijk
trager dan Tesseract — de tool werkt ook prima zonder deze stap, dan is
alleen de Tesseract-engine beschikbaar.

## Gebruik

```bash
python -m ocr_tool
```

1. Klik op **Toevoegen…** en kies één of meer afbeeldingen/PDF's.
2. Vink de talen aan die in de documenten voorkomen.
3. Klik op **▶ Start OCR**.
4. Kopieer of sla de herkende tekst op.

### Headless (zonder GUI)

```bash
python -m ocr_tool scan.pdf foto.jpg --lang nld+fra --engine auto
```

## Tips voor betere resultaten

- Scan of fotografeer op **300 dpi of hoger**, recht van boven, bij goed licht.
- **Nette scans?** Kies de engine *Tesseract*: vrijwel even nauwkeurig en een
  stuk sneller. **Foto's of slechte scans?** Kies *EasyOCR* of *Automatisch*.
- Vink alleen de talen aan die écht in het document staan — minder talen
  betekent doorgaans nauwkeurigere herkenning.
- Kies **Binariseren** bij vergeelde of vlekkerige scans.
- Zet **Paginalayout** op *Eén tekstblok* voor eenvoudige documenten zonder
  kolommen, of *Eén tekstregel* voor bijvoorbeeld een los bonnetje.
