---
title: WebP_Thumbnail_Creator
app_file: app.py
sdk: gradio
sdk_version: 6.26.0
---
# 🖼️ Python WebP Thumbnail Creator

A lightweight, fast command-line tool for creating **web-optimized WebP thumbnails** from common image formats (PNG, JPG, JPEG, WEBP, BMP, GIF, TIFF).

---

## 📦 Installation

### 1. Install Python (if not already installed)
Requires **Python 3.10+** (uses the `int | None` type hint syntax).

```bash
python3 --version
```

### 2. Install Pillow

```bash
pip install Pillow
```

Or inside a virtual environment (recommended):

```bash
python3 -m venv .venv
source .venv/bin/activate   # On Windows: .venv\Scripts\activate
pip install Pillow
```

---

## 🚀 Usage

### Basic Syntax

```bash
python3 thumbnail.py [OPTIONS]
```

### All Arguments

| Argument | Short | Default | Description |
|---|---|---|---|
| `--input FILE` | `-i` | *(required)* | Source image path |
| `--input-dir DIR` | — | — | Batch mode: folder of images |
| `--output FILE` | `-o` | `<name>-thumbnail.webp` | Output filename |
| `--output-dir DIR` | — | Same as `--input-dir` | Batch output folder |
| `--width PX` | `-w` | `150` | Target width in pixels |
| `--height PX` | — | Auto (aspect ratio) | Force exact height |
| `--quality 1-100` | `-q` | `1` | WebP quality (lower = smaller file) |
| `--max-size KB` | — | Off | Auto-reduce until under this size |
| `--quiet` | — | Off | Suppress per-attempt output |

---

## 📋 Examples

### 1. Simple resize with quality control
```bash
python3 thumbnail.py -i banner.png -w 120 -q 1
```
Resizes `banner.png` to 120px wide (auto height), quality 1 → saves `banner-thumbnail.webp`.

---

### 2. Target a maximum file size (1 KB)
```bash
python3 thumbnail.py -i banner.png --max-size 1
```
Automatically reduces quality and/or dimensions in a loop until the output is ≤ 1 KB.

---

### 3. Custom output filename
```bash
python3 thumbnail.py -i photo.jpg -o hero-thumb.webp -w 300 -q 50
```

---

### 4. Force exact dimensions (may distort aspect ratio)
```bash
python3 thumbnail.py -i banner.png -w 200 --height 200 -q 10
```

---

### 5. Batch process a folder
```bash
python3 thumbnail.py --input-dir ./originals --output-dir ./thumbnails -w 150
```
Processes all supported images in `./originals/`, saves results to `./thumbnails/`.

---

### 6. Batch with max-size and quiet mode
```bash
python3 thumbnail.py --input-dir ./originals --output-dir ./thumbs --max-size 2 --quiet
```

---

## 📊 Sample Output

```
Processing: banner.png

→ Targeting max size: 1 KB
    Attempt 1: quality=1, size=0.78 KB (800 bytes)
  ✓ Target achieved at quality=1

  Input : banner.png  (24576 bytes (24.00 KB))
  Output: banner-thumbnail.webp  (800 bytes (0.78 KB))
  Dims  : 120×45 px  | Quality: 1
  Saved : 96.7% reduction

✓ Saved to: /your/path/banner-thumbnail.webp
```

---

## 🗂️ Supported Formats

| Format | Extension |
|---|---|
| PNG | `.png` |
| JPEG | `.jpg`, `.jpeg` |
| WebP | `.webp` |
| BMP | `.bmp` |
| GIF | `.gif` |
| TIFF | `.tiff` |

---

## 💡 Tips

- **Quality 1** produces the smallest files — great for tiny web thumbnails.
- Use `--max-size` when you have a strict byte budget (e.g., favicon, OG image, banner).
- In batch mode, non-image files are **skipped gracefully** with a notice.
- Output is always **WebP** — the most efficient format for web use.

---

## 📁 Project Structure

```
python-thumnail-create/
├── thumbnail.py   ← The complete tool (single file)
└── README.md      ← This file
```

---

## 🔧 Requirements

- Python 3.10+
- Pillow >= 9.0
