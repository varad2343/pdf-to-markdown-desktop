"""
converter.py - Core PDF to Markdown conversion engine powered by PyMuPDF4LLM.
"""

import os
import re
import time
from typing import Dict, Any, List, Optional, Tuple
import pymupdf
import pymupdf4llm


def format_file_size(size_bytes: int) -> str:
    """Format bytes to human readable string (KB, MB, GB)."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def get_pdf_info(pdf_path: str) -> Dict[str, Any]:
    """
    Extract key document properties and metadata from a PDF file.
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    file_size = os.path.getsize(pdf_path)
    file_name = os.path.basename(pdf_path)

    try:
        doc = pymupdf.open(pdf_path)
        is_encrypted = doc.is_encrypted
        page_count = len(doc)
        meta = doc.metadata or {}

        info = {
            "file_name": file_name,
            "file_path": pdf_path,
            "file_size": file_size,
            "file_size_formatted": format_file_size(file_size),
            "page_count": page_count,
            "is_encrypted": is_encrypted,
            "title": meta.get("title", "") or "Untitled",
            "author": meta.get("author", "") or "Unknown",
            "creator": meta.get("creator", "") or "Unknown",
            "format": meta.get("format", "PDF"),
        }
        doc.close()
        return info
    except Exception as e:
        raise RuntimeError(f"Failed to read PDF metadata: {str(e)}")


def parse_page_range(range_str: str, total_pages: int) -> List[int]:
    """
    Parse a human-friendly page range string into a list of 0-based page indices.
    Examples:
        "1" -> [0]
        "1-3" -> [0, 1, 2]
        "1-3, 5, 8-10" -> [0, 1, 2, 4, 7, 8, 9]
    """
    if not range_str or not range_str.strip():
        # Empty string means all pages
        return list(range(total_pages))

    cleaned = range_str.strip()
    pages_set = set()
    parts = [p.strip() for p in cleaned.split(",") if p.strip()]

    for part in parts:
        # Check range pattern: X-Y
        if "-" in part:
            sub = part.split("-")
            if len(sub) != 2:
                raise ValueError(f"Invalid range specification: '{part}'")
            try:
                start_p = int(sub[0].strip())
                end_p = int(sub[1].strip())
            except ValueError:
                raise ValueError(f"Page numbers must be integers in range: '{part}'")

            if start_p < 1 or end_p < 1:
                raise ValueError(f"Page numbers must be 1 or greater in '{part}'")
            if start_p > end_p:
                raise ValueError(f"Start page {start_p} cannot be greater than end page {end_p}")

            for p in range(start_p, end_p + 1):
                if p <= total_pages:
                    pages_set.add(p - 1)
        else:
            try:
                p = int(part)
            except ValueError:
                raise ValueError(f"Invalid page number: '{part}'")
            if p < 1:
                raise ValueError(f"Page numbers must be 1 or greater: '{p}'")
            if p <= total_pages:
                pages_set.add(p - 1)

    if not pages_set:
        raise ValueError(f"No pages in range '{range_str}' match the document (Total pages: {total_pages})")

    return sorted(list(pages_set))


def estimate_tokens(text: str) -> int:
    """
    Estimate LLM token count using standard ~4 characters per token heuristic.
    """
    if not text:
        return 0
    # Rule of thumb for English / Markdown text: ~4 chars per token
    return max(1, int(len(text) / 3.9))


def count_words(text: str) -> int:
    """Count words in text."""
    if not text:
        return 0
    return len(re.findall(r"\b\w+\b", text))


def convert_pdf_to_markdown(
    pdf_path: str,
    page_range_str: Optional[str] = None,
    write_images: bool = False,
    images_folder: Optional[str] = None,
    page_separators: bool = True,
    table_output: str = "markdown",
) -> Tuple[str, Dict[str, Any]]:
    """
    Convert a PDF file to LLM-ready Markdown using pymupdf4llm.
    
    Returns:
        (markdown_text, stats_dict)
    """
    start_time = time.time()
    info = get_pdf_info(pdf_path)
    total_pages = info["page_count"]

    # Determine pages to convert
    if page_range_str and page_range_str.strip():
        pages = parse_page_range(page_range_str, total_pages)
    else:
        pages = None  # All pages

    actual_converted_count = len(pages) if pages is not None else total_pages

    # Set up images folder if requested
    img_path = None
    if write_images:
        if not images_folder:
            base_dir = os.path.dirname(os.path.abspath(pdf_path))
            pdf_base_name = os.path.splitext(os.path.basename(pdf_path))[0]
            img_path = os.path.join(base_dir, f"{pdf_base_name}_images")
        else:
            img_path = images_folder
        os.makedirs(img_path, exist_ok=True)

    # Perform conversion with pymupdf4llm
    md_text = pymupdf4llm.to_markdown(
        doc=pdf_path,
        pages=pages,
        write_images=write_images,
        image_path=img_path if write_images else None,
        image_format="png",
        page_separators=page_separators,
        table_output=table_output,
    )

    elapsed_time = time.time() - start_time
    char_count = len(md_text)
    word_count = count_words(md_text)
    token_count = estimate_tokens(md_text)

    stats = {
        "elapsed_seconds": elapsed_time,
        "pages_converted": actual_converted_count,
        "total_pages": total_pages,
        "char_count": char_count,
        "word_count": word_count,
        "estimated_tokens": token_count,
        "images_extracted": write_images,
        "images_folder": img_path if write_images else None,
    }

    return md_text, stats
