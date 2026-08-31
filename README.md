<p align="center"><img src="https://github.com/eremita-oficial/comic2kindle/blob/main/comic2kindle.png" width="200" height="auto"></p>
<h1 align="center"><b>comic2kindle</b></h1>
<h4 align="center">A comic to PDF converter optimized for Kindle devices.</h4>

</p>

<div align="center">

**Português**: [*PT-BR*](https://github.com/eremita-oficial/comic2kindle/blob/main/README_PT-BR.md)

**•**
</div>

## What it does

**comic2kindle**  is a desktop application that converts comic book pages (from folders, CBR, or CBZ files) into PDFs optimized for reading on Kindle devices. The tool automatically splits each page into multiple panels and rotates them for optimal landscape viewing on Kindle Paperwhite, Kindle Colorsoft, and other Kindle models.

Despite the name, the generated PDFs are standard format and can be viewed on any e-reader or PDF reader, not just Kindle devices. The optimization focuses on the 1264x1680 pixel format that works beautifully on Kindle devices, but the output remains fully compatible with all PDF readers, including Kobo, PocketBook, Android tablets, and desktop PDF viewers.

The application provides a complete workflow for preparing your digital comics for the best possible reading experience on Kindle:

- **Import** comics from image folders, CBR (Comic Book RAR), or CBZ (Comic Book Zip) archives
- **Edit** pages with visual cropping tools, margin detection, and page marking (cover/full page)
- **Export** to PDF with automatic panel splitting and rotation for Kindle-optimized landscape viewing

*Plugin preview*
![Kindle Paperwhite](comic2kindle_paperwhite.jpg)
![Kindle Colorsoft](comic2kindle_colorsoft.jpg)

## Download

Get the latest builds from the [download page](https://github.com/eremita-oficial/comic2kindle/releases).

| Platform | Builds |
|----------|--------|
| Windows x64 | Portable `.exe` |
| Linux x64 | AppImage |
| Source | `.zip`, or clone this repository |

---

## Features

- **Multi-format Support**: Import from image folders, CBR, and CBZ files
- **Smart Panel Splitting**: Automatically splits each page into 3 panels for optimal Kindle reading
- **Intelligent Rotation**: Rotates panels -90° for landscape viewing on Kindle devices
- **Page Management**: Mark pages as covers or full-page spreads (no splitting)
- **Visual Cropping**: Interactive margin cropping with auto-trim and percentage-based options
- **Project Management**: Save/load projects in full or lightweight modes
- **Quality Control**: Export with high-quality (95%) or space-saving (80%) JPEG compression
- **Metadata Support**: Add title and author information to exported PDFs
- **User-Friendly Interface**: Intuitive GUI with thumbnail navigation and zoom controls

---

## Installation

### Prerequisites

- Python 3.8 or higher
- For CBR support: `unrar` or `rar` command-line tool
  - **Ubuntu/Debian**: `sudo apt-get install unrar`
  - **Manjaro/Arch**: `sudo pamac install unrar`
  - **macOS**: `brew install unrar`
  - **Windows**: Install WinRAR or 7-Zip and add to PATH

### From Source

```bash
# Clone the repository
git clone https://github.com/yourusername/comic2kindle.git
cd comic2kindle

# Install dependencies
pip install -r requirements.txt

# Run the application
python gui.py
```

### Dependencies

```bash
pip install pillow opencv-python numpy reportlab img2pdf
```

---

## Usage

1. **Launch the application**: Run `python gui.py` or use the provided executable
2. **Import your comic**: Click `File → Open Folder`, `Open CBR`, or `Open CBZ`
3. **Edit pages** (optional):
   - Use `Detect Margins` for auto-cropping
   - Mark pages as `Cover` or `Full Page`
   - Manually crop pages with the visual editor
4. **Export to PDF**: Select `Export PDF (3 panels)` or `Export PDF (full pages)`
5. **Add metadata**: Enter title and author when prompted
6. **Choose save location**: Select where to save your optimized PDF

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `← / →` | Previous/Next page |
| `Ctrl+O` | Open folder/CBR/CBZ |
| `Ctrl+S` | Save full project |
| `Ctrl+Shift+S` | Save lightweight project |
| `Ctrl+Shift+O` | Open project |
| `ESC` | Cancel crop mode |
| `Del` | Crop marked margins |
| `Ctrl+Delete` | Remove current page |
| `Ctrl++ / Ctrl+-` | Zoom in/out |
| `Ctrl+0` | Fit to height |
| `Ctrl+9` | 100% zoom |
| `Ctrl+Q` | Quit |

---

### License

<b>comic2kindle</b> is licensed under the [Creative Commons Zero v1.0 Universal](https://creativecommons.org/publicdomain/zero/1.0/deed.en) License.

*Made with ❤️ for comic lovers and Kindle readers everywhere.*
