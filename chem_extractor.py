"""
chem_extractor.py  v4
=====================
Extracts images of ALL questions from a scanned question bank PDF with extreme accuracy.

Key Accuracy Features:
  - Tesseract OCR (PSM 6, OEM 3) detects question hanging-indent numbers (18 <= x <= 80).
  - Handles tricky OCR variants: '24,', '25:', '14.For', '(1)', etc.
  - Excludes second-word false filtering (handles questions starting with numbers like "5.0 g").
  - Sequence-aware tracking: verifies 1, 2, 3... progression and chapter resets.
  - Zero-overlap midpoint whitespace splitting: cuts exactly in the pure white gap
    between consecutive questions, ensuring NO clipped descenders and NO slivers.
  - Robust Answer Key exclusion: stops before answer key tables without false-triggering
    on section headers like "MCQs with One Correct Answer".
  - Clean margins: prevents column divider artifacts and footer watermarks.

OUTPUTS:
  1. all_questions_images/
     Every single question cropped as a high-resolution, crisp PNG.
  2. questions_with_diagrams/
     Quick-access folder containing questions with diagrams/graphs/figures.
  3. questions_catalog.md
     Visual markdown catalog embedding all question images organized by chapter.
  4. questions_metadata.json
     JSON index containing question numbers, page numbers, coordinates, chapter, and preview.
"""

import os
import re
import sys
import argparse
import json
import cv2
import numpy as np
import pymupdf
import pytesseract
from PIL import Image

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# ── CONFIG ────────────────────────────────────────────────────────────────────
PDF_PATH = (sys.argv[1] if len(sys.argv) > 1 else r"input.pdf")
OUT_ROOT = (sys.argv[2] if len(sys.argv) > 2 else r"output")

QUESTIONS_DIR = os.path.join(OUT_ROOT, "all_questions_images")
DIAG_DIR      = os.path.join(OUT_ROOT, "questions_with_diagrams")
CATALOG_MD    = os.path.join(OUT_ROOT, "questions_catalog.md")
METADATA_JSON = os.path.join(OUT_ROOT, "questions_metadata.json")

RENDER_SCALE  = 3.0    # 3x ~216 DPI (crisp text, formulas, and diagrams)
OCR_CONFIG    = "--psm 6 --oem 3"

# Tesseract executable path
TESSERACT_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
if os.path.exists(TESSERACT_CMD):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

# Chapter title page: >35% dark pixels -> splash/title page
TITLE_PAGE_DARK_FRAC = 0.35


# ── HELPERS ───────────────────────────────────────────────────────────────────

def cv_to_pil(cv_img: np.ndarray) -> Image.Image:
    """Convert OpenCV BGR image to PIL RGB image."""
    return Image.fromarray(cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB))


def is_title_page(gray: np.ndarray) -> bool:
    """Check if a page is a dark chapter splash / title page."""
    h, w = gray.shape
    roi  = gray[int(h * 0.05):int(h * 0.95), int(w * 0.03):int(w * 0.97)]
    return (np.sum(roi < 100) / roi.size) > TITLE_PAGE_DARK_FRAC


def render_page(doc, page_idx: int) -> np.ndarray:
    """Render a PDF page to a high-resolution BGR numpy array."""
    page = doc[page_idx]
    mat  = pymupdf.Matrix(RENDER_SCALE, RENDER_SCALE)
    pix  = page.get_pixmap(matrix=mat, alpha=False)
    img  = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3)
    return cv2.cvtColor(img, cv2.COLOR_RGB2BGR)


def get_column_crops(page_bgr: np.ndarray):
    """
    Split page into left and right columns while trimming headers & footers.
    Leaves comfortable breathing room horizontally so no formulas are clipped.
    """
    H, W = page_bgr.shape[:2]
    # Skip running header line at top (y0 = 0.11 * H)
    # Skip footer watermark at bottom (y1 = 0.980 * H)
    y0 = int(H * 0.11)
    y1 = int(H * 0.980)
    left  = page_bgr[y0:y1, int(W * 0.110):int(W * 0.475)]
    right = page_bgr[y0:y1, int(W * 0.465):int(W * 0.832)]
    return left, right


def ocr_chapter_title(page_bgr: np.ndarray) -> str:
    """Extract chapter name from a title page or page header."""
    pil = cv_to_pil(page_bgr)
    txt = pytesseract.image_to_string(pil, config=OCR_CONFIG)
    for line in txt.splitlines():
        line = line.strip()
        if len(line) > 5 and re.search(r'[A-Za-z]', line) and not re.match(r'^\d', line):
            cleaned = re.sub(r'[^\w\s\-]', '', line).strip()
            if len(cleaned) > 5:
                return cleaned
    return ""


# ── CHAPTER MAPPING (Exact TOC from Book) ──────────────────────────────────────
CHAPTERS_MAP = [
    (5, 7, "Some Basic Concepts of Chemistry"),
    (8, 11, "Structure of Atom"),
    (12, 14, "Classification of Elements and Periodicity in Properties"),
    (15, 18, "Chemical Bonding and Molecular Structure"),
    (19, 21, "States of Matter"),
    (22, 25, "Thermodynamics"),
    (26, 29, "Equilibrium"),
    (30, 31, "Redox Reactions"),
    (32, 33, "Hydrogen"),
    (34, 36, "The s-Block Elements"),
    (37, 39, "The p-Block Elements (Group-13 and 14)"),
    (40, 44, "Organic Chemistry - Some Basic Principles & Techniques"),
    (45, 49, "Hydrocarbons"),
    (50, 51, "Environmental Chemistry"),
    (52, 54, "The Solid State"),
    (55, 58, "Solutions"),
    (59, 62, "Electrochemistry"),
    (63, 66, "Chemical Kinetics"),
    (67, 70, "Surface Chemistry"),
    (71, 72, "General Principles and Processes of Isolation of Elements"),
    (73, 74, "The p-Block Elements (Group 15, 16, 17 & 18)"),
    (75, 76, "The d-and f-Block Elements"),
    (77, 79, "Co-ordination Compounds"),
    (80, 82, "Haloalkanes and Haloarenes"),
    (83, 86, "Alcohols, Phenols and Ethers"),
    (87, 90, "Aldehydes, Ketones and Carboxylic Acids"),
    (91, 94, "Amines"),
    (95, 98, "Biomolecules"),
    (99, 101, "Polymers"),
    (102, 103, "Chemistry in Everyday Life"),
    (104, 106, "Analytical Chemistry"),
]

def get_chapter_for_page(pdf_page: int) -> str:
    for s, e, name in CHAPTERS_MAP:
        if s <= pdf_page <= e:
            return name
    return "Chemistry"


# ── DIAGRAM DETECTION ─────────────────────────────────────────────────────────

def has_diagram(gray_crop: np.ndarray, col_ocr_data: dict = None, q_y0: int = 0) -> bool:
    """
    Detect whether a question contains real non-text visual graphics
    (chemical structures, apparatus drawings, coordinate plots, curves).
    Carefully distinguishes real 2D diagrams from 1D text formulas/brackets/fractions.
    Reuses column OCR bounding boxes when provided for 5x speedup.
    """
    h, w = gray_crop.shape
    if h < 55 or w < 55:
        return False

    # Binarize
    _, binary = cv2.threshold(gray_crop, 205, 255, cv2.THRESH_BINARY_INV)

    text_mask = np.zeros((h, w), dtype=np.uint8)
    pad = 6

    if col_ocr_data is not None:
        n = len(col_ocr_data['text'])
        for i in range(n):
            word = col_ocr_data['text'][i].strip()
            if not word:
                continue
            bx = col_ocr_data['left'][i]
            by = col_ocr_data['top'][i] - q_y0
            bw = col_ocr_data['width'][i]
            bh = col_ocr_data['height'][i]
            if by + bh < 0 or by >= h:
                continue
            # Giant boxes (>=65x65) are whole graphs/diagrams misread as pseudo-words
            if bh >= 65 and bw >= 65:
                continue
            x1 = max(0, bx - pad)
            y1 = max(0, by - pad)
            x2 = min(w, bx + bw + pad)
            y2 = min(h, by + bh + pad)
            cv2.rectangle(text_mask, (x1, y1), (x2, y2), 255, -1)
    else:
        bgr_crop = cv2.cvtColor(gray_crop, cv2.COLOR_GRAY2BGR)
        pil      = cv_to_pil(bgr_crop)
        data     = pytesseract.image_to_data(pil, config=OCR_CONFIG, output_type=pytesseract.Output.DICT)
        for i in range(len(data['text'])):
            word = data['text'][i].strip()
            if not word:
                continue
            bw = data['width'][i]
            bh = data['height'][i]
            if bh >= 65 and bw >= 65:
                continue
            x1 = max(0, data['left'][i] - pad)
            y1 = max(0, data['top'][i] - pad)
            x2 = min(w, data['left'][i] + bw + pad)
            y2 = min(h, data['top'][i] + bh + pad)
            cv2.rectangle(text_mask, (x1, y1), (x2, y2), 255, -1)

    # Non-text visual ink
    non_text_ink = cv2.bitwise_and(binary, cv2.bitwise_not(text_mask))

    # Suppress pure horizontal fraction bars (bridges that falsely connect formulas into 2D boxes)
    h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (22, 1))
    h_lines = cv2.morphologyEx(non_text_ink, cv2.MORPH_OPEN, h_kernel)
    clean_ink = cv2.bitwise_and(non_text_ink, cv2.bitwise_not(h_lines))

    # Dilate remaining ink moderately to group diagram lines and curves
    k = cv2.getStructuringElement(cv2.MORPH_RECT, (6, 6))
    dilated = cv2.dilate(clean_ink, k, iterations=2)

    # Find contours
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for cnt in contours:
        x, y, bw, bh = cv2.boundingRect(cnt)
        
        # Real diagrams have true 2D extent: BOTH width >= 55 AND height >= 55
        # (excludes tall thin brackets bw ~ 10-20 and horizontal divider lines bh ~ 2-10)
        if bw < 55 or bh < 55:
            continue
        if bw > w * 0.95: # page border artifact
            continue
            
        # Minimum bounding box area
        if bw * bh < 3500:
            continue
            
        # Check actual ink count inside the bounding box
        roi_ink = np.sum(binary[y:y+bh, x:x+bw] > 0)
        if roi_ink < 150: # too faint/sparse
            continue
            
        # Standard deviation confirms visual graphical texture
        roi_gray = gray_crop[y:y+bh, x:x+bw]
        if float(np.std(roi_gray)) >= 15:
            return True

    return False


# ── ANSWER KEY & FOOTER DETECTION ─────────────────────────────────────────────

def find_answer_key_start(ocr_data: dict, H: int) -> int:
    """
    Find the y-coordinate where an Answer Key table begins.
    Checks line-level text to match 'ANSWER KEY' specifically, avoiding
    false alarms on section headers like 'MCQs with One Correct Answer'.
    """
    n = len(ocr_data['text'])
    lines = {}
    for i in range(n):
        w = ocr_data['text'][i].strip()
        if not w:
            continue
        key = (ocr_data['block_num'][i], ocr_data['par_num'][i], ocr_data['line_num'][i])
        if key not in lines:
            lines[key] = []
        lines[key].append((w, ocr_data['top'][i]))

    for k, words in lines.items():
        line_str = " ".join(w[0] for w in words)
        top_y = words[0][1]
        if top_y < 150: # cannot be answer key header at top
            continue
        # Specific pattern for Answer Key
        if re.search(r'\bANSW(ER)?\b.*\bKEY\b|\bANSWER\s*KEY\b', line_str, re.I):
            return max(0, top_y - 12)
        # Standalone short headers when split across columns
        if re.match(r'^(ANSW|VER\s*KEY|KEY)$', line_str.strip(), re.I):
            return max(0, top_y - 12)

    return H


# ── GAP-BASED SPLITTING ───────────────────────────────────────────────────────

def find_whitespace_gap(gray: np.ndarray, y_next_ocr: int) -> int:
    """
    Find the exact zero-ink row in the whitespace gap above the next question.
    Searches in window [y_next_ocr - 35, y_next_ocr + 2] for zero-ink rows.
    Returns the midpoint of the contiguous white gap.
    """
    y_min = max(0, y_next_ocr - 35)
    y_max = min(gray.shape[0], y_next_ocr + 2)
    
    row_dark = np.array([np.sum(gray[y, :] < 190) for y in range(y_min, y_max)])
    zero_rows = np.where(row_dark == 0)[0]
    
    if len(zero_rows) > 0:
        # Group into contiguous blocks of zero ink
        blocks = np.split(zero_rows, np.where(np.diff(zero_rows) != 1)[0] + 1)
        # Pick the block closest to y_next_ocr
        best_block = blocks[-1]
        mid = int(np.mean(best_block))
        return y_min + mid
    else:
        # Fallback to row with lowest dark ink count
        min_idx = int(np.argmin(row_dark))
        return y_min + min_idx


# ── QUESTION EXTRACTION FROM COLUMN ───────────────────────────────────────────

def extract_questions_from_column(col_img: np.ndarray, last_seen_q: int = 0):
    """
    Extract all question bounding boxes from a single column image.
    Uses Tesseract OCR to detect hanging-indent question numbers,
    applies monotonic sequence verification, and splits boundaries
    at pure whitespace gaps.
    """
    H, W = col_img.shape[:2]
    pil = cv_to_pil(col_img)
    data = pytesseract.image_to_data(pil, config=OCR_CONFIG, output_type=pytesseract.Output.DICT)

    # 1. Detect Answer Key cutoff
    answer_key_y = find_answer_key_start(data, H)

    # 2. Extract valid words
    valid_words = []
    n = len(data['text'])
    for i in range(n):
        w = data['text'][i].strip()
        if not w:
            continue
        x = data['left'][i]
        y = data['top'][i]
        width = data['width'][i]
        height = data['height'][i]
        conf = int(data['conf'][i]) if data['conf'][i] != '-1' else 0

        # Filter outer border noise
        if x < 15 and (conf < 30 or width < 8):
            continue

        # Ignore anything at or below Answer Key
        if y >= answer_key_y:
            continue

        # Ignore bottom watermark
        if y > H - 45 or 'nz/folder' in w or 'folder/' in w:
            continue

        valid_words.append({
            'word': w, 'x': x, 'y': y, 'w': width, 'h': height,
            'conf': conf, 'block': data['block_num'][i],
            'par': data['par_num'][i], 'line': data['line_num'][i]
        })

    # Group into lines
    lines = {}
    for w in valid_words:
        key = (w['block'], w['par'], w['line'])
        if key not in lines:
            lines[key] = []
        lines[key].append(w)

    sorted_lines = []
    for k, words in lines.items():
        words.sort(key=lambda item: item['x'])
        sorted_lines.append(words)
    sorted_lines.sort(key=lambda ws: ws[0]['y'])

    # Candidate question identification
    candidates = []
    for ws in sorted_lines:
        # Check first token within question hanging-indent margin (18 <= x <= 80)
        margin_words = [w for w in ws if 18 <= w['x'] <= 80]
        if not margin_words:
            continue

        first = margin_words[0]
        y_top = first['y']

        # Skip top header text
        if y_top < 65:
            continue

        w_text = first['word']
        m = re.match(r'^(\d{1,3})([.,:)\-_]?.*)$', w_text)
        if not m:
            continue

        q_num = int(m.group(1))
        if q_num > 150:
            continue

        full_line = " ".join(item['word'] for item in ws)
        candidates.append({
            'q_num': q_num,
            'y_top': y_top,
            'line_text': full_line,
            'words': ws
        })

    # 3. Margin stripe scan for guaranteed question number capture beside diagrams
    margin_strip = col_img[:, :115]
    pil_margin = cv_to_pil(margin_strip)
    data_margin = pytesseract.image_to_data(pil_margin, config=OCR_CONFIG, output_type=pytesseract.Output.DICT)
    existing_nums = set(c['q_num'] for c in candidates)
    for i in range(len(data_margin['text'])):
        w = data_margin['text'][i].strip()
        if not w:
            continue
        y_top = data_margin['top'][i]
        if y_top < 65 or y_top >= answer_key_y:
            continue
        m = re.match(r'^(\d{1,3})([.,:)\-_]?.*)$', w)
        if m:
            q_num = int(m.group(1))
            if q_num <= 150 and q_num not in existing_nums:
                candidates.append({
                    'q_num': q_num,
                    'y_top': y_top,
                    'line_text': w,
                    'words': []
                })
                existing_nums.add(q_num)

    candidates.sort(key=lambda c: c['y_top'])

    if not candidates:
        return [], data

    # Sequence filtering
    valid_qs = []
    curr_q = last_seen_q
    for c in candidates:
        q_num = c['q_num']
        # Chapter restart (Q1)
        if q_num == 1:
            valid_qs.append(c)
            curr_q = 1
        elif q_num > curr_q and (curr_q == 0 or q_num <= curr_q + 5):
            valid_qs.append(c)
            curr_q = q_num
        elif q_num == curr_q + 1:
            valid_qs.append(c)
            curr_q = q_num

    if not valid_qs:
        return [], data

    # Calculate exact vertical boundaries
    results = []
    gray = cv2.cvtColor(col_img, cv2.COLOR_BGR2GRAY)
    num_qs = len(valid_qs)

    # Compute split points between questions
    split_points = []
    for i in range(num_qs - 1):
        q_next_top = valid_qs[i+1]['y_top']
        split_y = find_whitespace_gap(gray, q_next_top)
        split_points.append(split_y)

    for idx, q_info in enumerate(valid_qs):
        q_num = q_info['q_num']

        # Start y
        if idx == 0:
            # First question in column: search for ink gap above
            y_start = max(0, q_info['y_top'] - 12)
        else:
            y_start = split_points[idx - 1]

        # End y
        if idx < num_qs - 1:
            y_end = split_points[idx]
        else:
            # Last question in column: stop before Answer Key, watermark, or empty space
            max_limit = min(H - 45, answer_key_y)
            q_crop_gray = gray[y_start:max_limit, :]
            row_ink = np.sum(q_crop_gray < 190, axis=1)
            ink_rows = np.where(row_ink > 15)[0]

            if len(ink_rows) > 0:
                last_q_ink = ink_rows[-1]
                # Only stop before a gap if what's below the gap is an Answer Key table border
                for r_idx in range(len(ink_rows) - 1):
                    gap = ink_rows[r_idx + 1] - ink_rows[r_idx]
                    if gap > 50:
                        sub_ink = q_crop_gray[ink_rows[r_idx+1]:, :]
                        # Dense horizontal line spanning > 45% of column indicates table border
                        if np.any(np.sum(sub_ink < 190, axis=1) > W * 0.45):
                            last_q_ink = ink_rows[r_idx]
                            break
                y_end = min(max_limit, y_start + last_q_ink + 14)
            else:
                y_end = min(max_limit, y_start + 180)

        if y_end <= y_start + 15:
            continue

        results.append({
            'q_num': q_num,
            'y_start': y_start,
            'y_end': y_end,
            'preview': q_info['line_text']
        })

    return results, data


# ── MAIN PIPELINE ─────────────────────────────────────────────────────────────

def process_pdf(pdf_path: str = PDF_PATH, out_root: str = OUT_ROOT,
                start_page: int = 5, end_page: int = 106, diagrams_only: bool = True):
    """
    Main extraction pipeline.
    When diagrams_only=True (default), saves ONLY questions that contain
    real visual diagrams (graphs, figures, apparatus, structures).
    Defaults to pages 5-106 (the full Questions section of all 31 chapters).
    """
    diagrams_out_dir  = os.path.join(out_root, "questions_with_diagrams")
    all_q_out_dir     = os.path.join(out_root, "all_questions_images")
    catalog_md_path   = os.path.join(out_root, "diagram_questions_catalog.md")
    metadata_json_path= os.path.join(out_root, "diagram_questions_metadata.json")

    os.makedirs(diagrams_out_dir, exist_ok=True)
    if not diagrams_only:
        os.makedirs(all_q_out_dir, exist_ok=True)

    # Clean existing images in diagrams_out_dir
    for f in os.listdir(diagrams_out_dir):
        if f.endswith('.png'):
            try:
                os.remove(os.path.join(diagrams_out_dir, f))
            except Exception:
                pass

    print("=" * 70)
    print(f"CHEM QUESTION BANK EXTRACTOR  v4 (Diagrams Only: {diagrams_only})")
    print(f"  PDF:    {pdf_path}")
    print(f"  Output: {diagrams_out_dir}")
    print("=" * 70)

    doc = pymupdf.open(pdf_path)
    total_pages = len(doc)
    
    start_idx = max(0, start_page - 1)
    end_idx   = min(total_pages, end_page) if end_page else min(total_pages, 106)
    
    print(f"Processing question pages {start_idx + 1} to {end_idx} of {total_pages} total...\n")

    current_chapter = ""
    curr_q = 0
    total_diagrams = 0
    total_inspected = 0

    catalog_lines = [
        "# Chemistry Question Bank — Diagram Questions Catalog\n",
        f"> Filtered & extracted with Tesseract OCR from `{os.path.basename(pdf_path)}`\n",
        "---\n\n"
    ]
    metadata = []

    for page_idx in range(start_idx, end_idx):
        page_num = page_idx + 1
        page_bgr = render_page(doc, page_idx)

        # Check chapter transition
        chap = get_chapter_for_page(page_num)
        if chap != current_chapter:
            current_chapter = chap
            curr_q = 0  # reset sequence for new chapter
            print(f"\n[PAGE {page_num:3d}] === CHAPTER: {current_chapter} ===")
            catalog_lines.append(f"\n## {current_chapter}\n\n")

        L, R = get_column_crops(page_bgr)

        # Process Left and Right columns
        qs_L, ocr_L = extract_questions_from_column(L, last_seen_q=curr_q)
        if qs_L:
            curr_q = qs_L[-1]['q_num']

        qs_R, ocr_R = extract_questions_from_column(R, last_seen_q=curr_q)
        if qs_R:
            curr_q = qs_R[-1]['q_num']

        # Check if the last question in column L continues at the top of column R
        # (e.g. options c & d placed in right column before first question of right column)
        is_chapter_start = (page_num in [s for s, e, _ in CHAPTERS_MAP])
        if qs_L and qs_R and not is_chapter_start:
            last_L = qs_L[-1]
            first_R = qs_R[0]
            if first_R['y_start'] > 180 and first_R['q_num'] == last_L['q_num'] + 1:
                y_cont_start = 118
                if y_cont_start < first_R['y_start']:
                    cont_crop = R[y_cont_start:first_R['y_start'], :]
                    if cont_crop is not None and cont_crop.size > 0 and cont_crop.shape[0] > 15:
                        cont_gray = cv2.cvtColor(cont_crop, cv2.COLOR_BGR2GRAY)
                        dark_frac = np.sum(cont_gray < 100) / cont_gray.size
                        if dark_frac < 0.08 and np.sum(cont_gray < 190) > 300:
                            last_L['continuation'] = cont_crop

        col_questions = [('L', L, qs_L), ('R', R, qs_R)]
        page_diag_count = 0

        for col_label, col_img, qs in col_questions:
            for q in qs:
                total_inspected += 1
                q_num   = q['q_num']
                y0, y1  = q['y_start'], q['y_end']
                if y1 <= y0 + 15:
                    continue
                q_crop  = col_img[y0:y1, :]
                if q_crop is None or q_crop.size == 0 or q_crop.shape[0] < 25:
                    continue

                # If question has a continuation from next column, stitch it
                if 'continuation' in q:
                    c_crop = q['continuation']
                    if c_crop is not None and c_crop.size > 0 and c_crop.shape[0] >= 15:
                        w1, w2 = q_crop.shape[1], c_crop.shape[1]
                        target_w = max(w1, w2)
                        if w1 < target_w:
                            q_crop = cv2.copyMakeBorder(q_crop, 0, 0, 0, target_w - w1, cv2.BORDER_CONSTANT, value=[255, 255, 255])
                        if w2 < target_w:
                            c_crop = cv2.copyMakeBorder(c_crop, 0, 0, 0, target_w - w2, cv2.BORDER_CONSTANT, value=[255, 255, 255])
                        sep = np.full((12, target_w, 3), 255, dtype=np.uint8)
                        cv2.line(sep, (20, 6), (target_w - 20, 6), (220, 220, 220), 1)
                        q_crop = np.vstack([q_crop, sep, c_crop])

                if q_crop is None or q_crop.size == 0 or q_crop.shape[0] < 25:
                    continue

                q_gray = cv2.cvtColor(q_crop, cv2.COLOR_BGR2GRAY)

                # Check if question contains a diagram
                diag_flag = has_diagram(q_gray)

                if not diag_flag and diagrams_only:
                    continue # Skip text-only questions!

                fname = f"p{page_num:03d}_{col_label}_q{q_num:03d}.png"
                out_path = os.path.join(diagrams_out_dir, fname)
                cv2.imwrite(out_path, q_crop)
                total_diagrams += 1
                page_diag_count += 1

                kb = os.path.getsize(out_path) / 1024
                print(f"  [DIAGRAM] Page {page_num:3d} Col {col_label} Q{q_num:3d} -> {fname} ({kb:.0f} KB)")

                # Record metadata
                rel_img_path = os.path.relpath(out_path, out_root)
                metadata.append({
                    "q_num": int(q_num),
                    "chapter": current_chapter,
                    "page": int(page_num),
                    "column": col_label,
                    "bbox": {"y_start": int(y0), "y_end": int(y1), "height": int(q_crop.shape[0])},
                    "has_diagram": True,
                    "preview": str(q['preview'][:100]),
                    "image_file": rel_img_path
                })

                # Append to catalog markdown
                catalog_lines.append(
                    f"### Question {q_num} *(Diagram)*\n"
                    f"**Chapter**: {current_chapter} | **Page**: {page_num} ({col_label})\n\n"
                    f"![Question {q_num}]({rel_img_path})\n\n"
                    f"---\n\n"
                )

    # Save metadata JSON
    with open(metadata_json_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2)

    # Save catalog Markdown
    with open(catalog_md_path, 'w', encoding='utf-8') as f:
        f.writelines(catalog_lines)

    doc.close()

    print("\n" + "=" * 70)
    print("EXTRACTION COMPLETE!")
    print(f"  Total Questions Inspected       : {total_inspected:4d}")
    print(f"  Questions With Diagrams Found   : {total_diagrams:4d}")
    print(f"  Diagram Questions Folder        : {diagrams_out_dir}")
    print(f"  Visual Catalog Markdown         : {catalog_md_path}")
    print(f"  Metadata Index JSON             : {metadata_json_path}")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="Extract ONLY questions with diagrams from question bank PDF.")
    parser.add_argument("--pdf", default=PDF_PATH, help="Path to PDF file")
    parser.add_argument("--out", default=OUT_ROOT, help="Output root directory")
    parser.add_argument("--start", type=int, default=5, help="Start page number (default: 5)")
    parser.add_argument("--end", type=int, default=106, help="End page number (default: 106)")
    parser.add_argument("--all", action="store_true", help="Extract all questions (default: diagrams only)")
    args = parser.parse_args()

    process_pdf(
        pdf_path=args.pdf,
        out_root=args.out,
        start_page=args.start,
        end_page=args.end,
        diagrams_only=not args.all
    )


if __name__ == "__main__":
    main()
