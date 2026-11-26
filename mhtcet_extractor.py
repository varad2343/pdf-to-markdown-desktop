import sys
"""
mhtcet_extractor.py  v2
========================
Extracts MHT-CET 2020 PYQS questions into two outputs:

  OUTPUT 1: questions_with_diagrams/
    One PNG per question that contains an embedded image/diagram.
    The crop covers the full question region (text + diagram).

  OUTPUT 2: questions_text_only.md
    Clean Markdown of every question that has NO diagram.

Key improvements in v2:
  - Proper two-column layout detection (left col x<280, right col x>280)
  - Each column processed independently so questions don't interleave
  - Cleaner option labelling (A/B/C/D bullets detected from bbox indentation)
  - Answer-key rows filtered out
  - Subject/Chapter header section tracking
"""

import os
import re
import pymupdf

# ── CONFIG ────────────────────────────────────────────────────────────────────
PDF_PATH = (sys.argv[1] if len(sys.argv) > 1 else r"input.pdf")
OUT_ROOT = (sys.argv[2] if len(sys.argv) > 2 else r"output")

DIAG_DIR  = os.path.join(OUT_ROOT, "questions_with_diagrams")
TEXT_MD   = os.path.join(OUT_ROOT, "questions_text_only.md")

MIN_CHARS       = 400    # skip non-content pages below this char count
RENDER_SCALE    = 2.5    # PNG DPI multiplier (2.5 ≈ 180 DPI)
CROP_PAD        = 10     # pts padding around each question crop
COL_SPLIT_X     = 295    # x coordinate that splits left/right columns (PDF pts)
HEADER_MAX_Y    = 80     # blocks above this y-value are page headers

# ── HELPERS ───────────────────────────────────────────────────────────────────

Q_NUM_RE  = re.compile(r'^\s*\((\d{1,3})\)')
OPTION_RE = re.compile(r'^([A-D])\s*[\)\.]?\s*')  # "A  foo" or "A) foo"

def spans_text(block) -> str:
    return ''.join(
        span['text']
        for line in block['lines']
        for span in line['spans']
    )

def clean(txt: str) -> str:
    txt = txt.replace('\uf0b7', '\u2022')   # bullet
    txt = re.sub(r'[ \t]+', ' ', txt)
    return txt.strip()

def bbox_union(boxes):
    x0 = min(b[0] for b in boxes)
    y0 = min(b[1] for b in boxes)
    x1 = max(b[2] for b in boxes)
    y1 = max(b[3] for b in boxes)
    return (x0, y0, x1, y1)


def get_page_header(blocks) -> str:
    """Return subject+chapter from the top-most text block."""
    for b in sorted(blocks, key=lambda b: b['bbox'][1]):
        if b['type'] == 0 and b['bbox'][1] < HEADER_MAX_Y:
            txt = clean(spans_text(b))
            if len(txt) > 3:
                return txt
    return ""


def extract_column_questions(col_text_blocks, col_image_blocks, col_label):
    """
    Given sorted text & image blocks for ONE column, return list of question dicts:
      { q_num, text_blocks, image_blocks, bbox }
    """
    questions = []
    current_q = None

    for b in col_text_blocks:
        txt = clean(spans_text(b))
        if not txt:
            continue

        m = Q_NUM_RE.match(txt)
        if m:
            # Save previous question
            if current_q:
                questions.append(current_q)
            current_q = {
                'q_num': int(m.group(1)),
                'text_blocks': [b],
                'image_blocks': [],
                'bbox': b['bbox'],
            }
        else:
            if current_q:
                current_q['text_blocks'].append(b)
                # Expand bbox
                x0 = min(current_q['bbox'][0], b['bbox'][0])
                y0 = min(current_q['bbox'][1], b['bbox'][1])
                x1 = max(current_q['bbox'][2], b['bbox'][2])
                y1 = max(current_q['bbox'][3], b['bbox'][3])
                current_q['bbox'] = (x0, y0, x1, y1)

    if current_q:
        questions.append(current_q)

    # Assign images to questions by Y-overlap
    for q in questions:
        qy0, qy1 = q['bbox'][1], q['bbox'][3]
        tol = 15
        q['image_blocks'] = [
            ib for ib in col_image_blocks
            if not (ib['bbox'][3] < qy0 - tol or ib['bbox'][1] > qy1 + tol)
        ]
        # Expand bbox to include images
        if q['image_blocks']:
            all_bboxes = [q['bbox']] + [ib['bbox'] for ib in q['image_blocks']]
            q['bbox'] = bbox_union(all_bboxes)

    return questions


def question_to_markdown(q: dict) -> str:
    """Reconstruct clean markdown text from a question's text blocks."""
    blocks = sorted(
        q['text_blocks'],
        key=lambda b: (round(b['bbox'][1] / 12) * 12, b['bbox'][0])
    )
    lines = []
    for b in blocks:
        txt = clean(spans_text(b))
        if not txt:
            continue
        # Skip lone page numbers like "[95]" or answer key rows
        if re.fullmatch(r'\[\d+\]', txt):
            continue
        if re.search(r'Question Number.*Correct Answer', txt, re.I):
            continue
        lines.append(txt)

    if not lines:
        return ""

    # Merge into one string, then reformat A/B/C/D options onto new lines
    merged = ' '.join(lines)
    # Insert newline before A/B/C/D option markers: space + capital letter + space
    merged = re.sub(r'\s+([A-D])\s+(?=[A-Z0-9\-\(])', r'\n    \1) ', merged)
    return merged.strip()


def render_question_png(page, q: dict, out_path: str):
    """Render a question region to PNG."""
    pw, ph = page.rect.width, page.rect.height
    x0, y0, x1, y1 = q['bbox']
    x0 = max(0, x0 - CROP_PAD)
    y0 = max(0, y0 - CROP_PAD)
    x1 = min(pw, x1 + CROP_PAD)
    y1 = min(ph, y1 + CROP_PAD)
    clip = pymupdf.Rect(x0, y0, x1, y1)
    mat  = pymupdf.Matrix(RENDER_SCALE, RENDER_SCALE)
    pix  = page.get_pixmap(matrix=mat, clip=clip, alpha=False)
    pix.save(out_path)


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    # Clean previous run
    os.makedirs(DIAG_DIR, exist_ok=True)
    for f in os.listdir(DIAG_DIR):
        if f.endswith('.png'):
            os.remove(os.path.join(DIAG_DIR, f))

    print(f"Opening: {os.path.basename(PDF_PATH)}")
    doc = pymupdf.open(PDF_PATH)
    print(f"Pages: {len(doc)}  |  Output: {OUT_ROOT}")
    print()

    md_lines = [
        "# MHT-CET 2020 PYQS — Text-Only Questions\n",
        "> Questions with diagrams are saved as PNG images in `questions_with_diagrams/`\n",
        "---\n",
    ]

    prev_section = ""
    total_img_q  = 0
    total_txt_q  = 0
    total_skip   = 0

    for page_idx in range(len(doc)):
        page     = doc[page_idx]
        raw_text = page.get_text().strip()

        # Skip non-content pages
        if len(raw_text) < MIN_CHARS:
            total_skip += 1
            continue
        if re.search(r'Question Number\s*Correct Answer', raw_text, re.I):
            total_skip += 1
            continue

        blocks = page.get_text('dict')['blocks']

        # ── Detect header ──────────────────────────────────────────────────
        header = get_page_header(blocks)
        # Parse "Physics  Laws of Motion" -> subject + chapter
        parts = re.split(r'\s{2,}', header, maxsplit=1)
        subject = parts[0].strip() if parts else ""
        chapter = parts[1].strip() if len(parts) > 1 else ""
        section = f"## {subject}" + (f" — {chapter}" if chapter else "")

        # ── Split blocks into two columns ──────────────────────────────────
        left_text,  right_text  = [], []
        left_imgs,  right_imgs  = [], []

        for b in blocks:
            if b['bbox'][1] < HEADER_MAX_Y:    # skip header row
                continue
            if b['bbox'][3] > page.rect.height - 30:  # skip footer
                continue
            cx = (b['bbox'][0] + b['bbox'][2]) / 2    # centre x

            if b['type'] == 0:
                txt = clean(spans_text(b))
                if len(txt) < 2:
                    continue
                b['_text'] = txt
                if cx < COL_SPLIT_X:
                    left_text.append(b)
                else:
                    right_text.append(b)
            elif b['type'] == 1:
                if b['width'] >= 20 and b['height'] >= 20:
                    if cx < COL_SPLIT_X:
                        left_imgs.append(b)
                    else:
                        right_imgs.append(b)

        # Sort each column top-to-bottom
        for lst in (left_text, right_text, left_imgs, right_imgs):
            lst.sort(key=lambda b: b['bbox'][1])

        # ── Extract questions per column ───────────────────────────────────
        left_qs  = extract_column_questions(left_text,  left_imgs,  'L')
        right_qs = extract_column_questions(right_text, right_imgs, 'R')
        all_qs   = left_qs + right_qs

        if not all_qs:
            continue

        # ── Process each question ──────────────────────────────────────────
        section_written = False
        for q in all_qs:
            has_img = len(q['image_blocks']) > 0

            if has_img:
                fname    = f"p{page_idx+1:03d}_q{q['q_num']:03d}.png"
                out_path = os.path.join(DIAG_DIR, fname)
                render_question_png(page, q, out_path)
                kb = os.path.getsize(out_path) / 1024
                print(f"  [IMG] pg{page_idx+1:3d} Q{q['q_num']:3d}  {fname}  ({kb:.0f} KB)")
                total_img_q += 1

            else:
                md_txt = question_to_markdown(q)
                if not md_txt:
                    continue

                if section != prev_section:
                    md_lines.append(f"\n{section}\n")
                    prev_section = section
                    section_written = True

                md_lines.append(f"\n**({q['q_num']})** {md_txt}\n")
                total_txt_q += 1

    # Write markdown file
    with open(TEXT_MD, 'w', encoding='utf-8') as f:
        f.write('\n'.join(md_lines))

    doc.close()

    print()
    print("=" * 65)
    print("DONE!")
    print(f"  Questions with diagrams  : {total_img_q:4d}  ->  {DIAG_DIR}")
    print(f"  Text-only questions      : {total_txt_q:4d}  ->  {TEXT_MD}")
    print(f"  Pages skipped (non-Q)    : {total_skip:4d}")
    print("=" * 65)


if __name__ == "__main__":
    main()
