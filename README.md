# 📑 PDF to Markdown Converter (PyMuPDF4LLM)

A modern, native Windows Desktop application to convert PDF documents into clean, structured, **LLM-ready Markdown** powered by [`pymupdf4llm`](https://pymupdf.readthedocs.io/en/latest/pymupdf4llm/) and [`CustomTkinter`](https://customtkinter.tomschimansky.com/).

---

## ✨ Features

- 🎨 **Modern Windows GUI**: Built with CustomTkinter featuring Dark, Light, and System themes.
- ⚡ **High-Fidelity Markdown**: Preserves complex reading order, tables, headers, bullet points, and code blocks.
- 📑 **Single File Conversion**:
  - Live Markdown preview in an embedded editor.
  - Word count, character count, and **Estimated LLM Token Count**.
  - One-click **Copy to Clipboard** and **Save as .md**.
- 📚 **Batch Processing**:
  - Queue multiple PDF files or an entire folder.
  - Batch convert all documents into individual `.md` files in seconds.
- 🎯 **Flexible Page Range Selection**:
  - Convert all pages or specify ranges (e.g. `1-3, 5, 8-10`).
- 🖼️ **Image Extraction**:
  - Automatically extract and save embedded diagrams and images.
- 📊 **Table Handling**:
  - Output tables as standard GitHub Markdown tables or HTML tables for complex merged cells.
- 🧵 **Multi-threaded**:
  - Conversions run asynchronously in the background so the interface never freezes.

---

## 🚀 Quick Start

### 1. Launch the App
Simply double-click the included batch launcher:
```cmd
run.bat
```
Or start via PowerShell / Command Prompt:
```powershell
python app.py
```

---

## 📦 Installed Dependencies

Dependencies:
- `pymupdf4llm`
- `pymupdf`
- `customtkinter`
- `pyperclip`
- `darkdetect`

To reinstall or replicate in a new virtual environment:
```powershell
pip install -r requirements.txt
```

---

## 💻 Programmatic Usage

You can also use the converter directly in your own Python scripts:

```python
import converter

# Convert entire PDF or specific pages
markdown_text, stats = converter.convert_pdf_to_markdown(
    pdf_path="document.pdf",
    page_range_str="1-5, 8",
    write_images=True,
    table_output="markdown"
)

print(f"Converted {stats['pages_converted']} pages in {stats['elapsed_seconds']:.2f}s")
print(f"Estimated LLM Tokens: ~{stats['estimated_tokens']}")
```

## Question-paper extractors
Helper scripts that split exam PDFs into per-question Markdown and PNG crops (with diagram detection and optional Tesseract OCR):
`mhtcet_extractor.py`, `chem_extractor.py`, `extract_pages.py`, `extract_diagrams.py`.
Run them as `python mhtcet_extractor.py <input.pdf> <output_folder>`. No exam papers are included in this repo.

## Author
Varad Bhoir, ENTC
