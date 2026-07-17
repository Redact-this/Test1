# OCR-tool – Nederlands · Engels · Frans

Een OCR-tool met grafische interface (Tkinter) die tekst herkent uit
afbeeldingen **en PDF's**, gericht op Nederlands, Engels en Frans.
Gebouwd op [Tesseract 5](https://tesseract-ocr.github.io/) met automatische
beeldvoorbewerking voor betere resultaten.

## Functies

- **Afbeeldingen én PDF's**: PNG, JPG, TIFF (ook multi-page), BMP, GIF, WebP en PDF.
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
python -m ocr_tool scan.pdf foto.jpg --lang nld+fra
```

## Tips voor betere resultaten

- Scan of fotografeer op **300 dpi of hoger**, recht van boven, bij goed licht.
- Vink alleen de talen aan die écht in het document staan — minder talen
  betekent doorgaans nauwkeurigere herkenning.
- Kies **Binariseren** bij vergeelde of vlekkerige scans.
- Zet **Paginalayout** op *Eén tekstblok* voor eenvoudige documenten zonder
  kolommen, of *Eén tekstregel* voor bijvoorbeeld een los bonnetje.
