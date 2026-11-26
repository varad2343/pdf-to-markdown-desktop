import sys
"""
extract_diagrams.py - v2
------------------------
Detects and extracts ONLY diagram/figure regions from scanned Allen test series pages.

Key insight from layout analysis:
  - Text lines: wide (>30% page width) but VERY short height (~25-35px per line)
  - Diagrams/figures: moderate width but TALLER height (>100px), NOT full-width
  - The approach: small dilation to separate individual blobs, then filter by
    aspect ratio (tall-ish relative to width) and size

Strategy:
  1. Small dilation kernel to keep text lines separate from diagram blocks.
  2. Find all contours.
  3. Filter: keep boxes that are NOT thin text lines (height > 80px) AND 
     NOT spanning the full page width.
  4. For each kept box, scan the ROI for visual complexity (std deviation of 
     pixel values) to confirm it's a drawn figure, not just a math formula line.
"""

import os
import cv2
import numpy as np

# ── CONFIG ─────────────────────────────────────────────────────────────────────
IMAGES_IN = (sys.argv[1] if len(sys.argv) > 1 else r"output/images")
DIAGRAMS_OUT = (sys.argv[2] if len(sys.argv) > 2 else r"output")

# A box must be AT LEAST this tall to be considered a diagram
MIN_HEIGHT_PX  = 80     # px  (text lines are ~25-35px; formulas ~40-70px)

# Min width – ignore tiny isolated symbols
MIN_WIDTH_PX   = 50     # px

# Skip boxes wider than this fraction of page width (they are question blocks)
MAX_WIDTH_FRAC = 0.60   # diagrams are rarely wider than 60% of a column

# The ROI must have enough visual "texture" – std deviation of grayscale > this
# (pure white space = 0; uniform ink = low; real diagrams = mid-high)
MIN_STD_DEV    = 18     # 0-255 scale

# Border padding around each saved crop
PAD = 20   # px

# ── HELPERS ────────────────────────────────────────────────────────────────────

def merge_close_boxes(boxes, gap=25):
    """Merge boxes that are within `gap` pixels of each other vertically."""
    if not boxes:
        return []
    boxes = sorted(boxes, key=lambda b: b[1])  # sort by Y
    merged = [list(boxes[0])]
    for x, y, w, h in boxes[1:]:
        px, py, pw, ph = merged[-1]
        # Check vertical proximity AND horizontal overlap
        vert_close  = y < py + ph + gap
        horiz_overlap = x < px + pw and x + w > px
        if vert_close and horiz_overlap:
            nx = min(px, x)
            ny = min(py, y)
            merged[-1] = [nx, ny,
                          max(px + pw, x + w) - nx,
                          max(py + ph, y + h) - ny]
        else:
            merged.append([x, y, w, h])
    return [tuple(b) for b in merged]


def extract_diagrams_from_page(img_path, page_num, out_dir):
    img_bgr = cv2.imread(img_path)
    if img_bgr is None:
        print(f"  [SKIP] Cannot read: {os.path.basename(img_path)}")
        return 0

    H, W = img_bgr.shape[:2]
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

    # ── Threshold: dark ink on white ──────────────────────────────────────────
    _, binary = cv2.threshold(gray, 215, 255, cv2.THRESH_BINARY_INV)

    # ── Small dilation: join pixels within a character but NOT between lines ──
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (6, 3))
    dilated = cv2.dilate(binary, kernel, iterations=2)

    # ── Find contours ─────────────────────────────────────────────────────────
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    candidates = []
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)

        # Must be tall enough (not a text line)
        if h < MIN_HEIGHT_PX:
            continue
        # Must be wide enough
        if w < MIN_WIDTH_PX:
            continue
        # Must NOT span most of the page width (question blocks)
        if w > W * MAX_WIDTH_FRAC:
            continue
        # Ignore very thin tall boxes (vertical separators/borders)
        if w < 40 and h > 300:
            continue

        # Visual complexity check on the original grayscale ROI
        roi = gray[y:y+h, x:x+w]
        std_dev = float(np.std(roi))
        if std_dev < MIN_STD_DEV:
            continue

        candidates.append((x, y, w, h))

    # ── Merge nearby candidates ────────────────────────────────────────────────
    merged = merge_close_boxes(candidates, gap=30)

    # ── Second-pass: recheck merged boxes ─────────────────────────────────────
    final = []
    for (x, y, w, h) in merged:
        # After merging, boxes may have grown too wide
        if w > W * MAX_WIDTH_FRAC:
            continue
        if h < MIN_HEIGHT_PX:
            continue
        roi = gray[y:y+h, x:x+w]
        std_dev = float(np.std(roi))
        if std_dev < MIN_STD_DEV * 0.8:
            continue
        final.append((x, y, w, h))

    # ── Crop & save ───────────────────────────────────────────────────────────
    saved = 0
    for idx, (x, y, w, h) in enumerate(final, start=1):
        x1 = max(0, x - PAD)
        y1 = max(0, y - PAD)
        x2 = min(W, x + w + PAD)
        y2 = min(H, y + h + PAD)
        crop = img_bgr[y1:y2, x1:x2]
        name = f"page{page_num:02d}_diagram{idx:02d}.png"
        path = os.path.join(out_dir, name)
        cv2.imwrite(path, crop)
        kb = os.path.getsize(path) / 1024
        print(f"    -> {name}  ({w}x{h} px, {kb:.0f} KB, std={float(np.std(gray[y:y+h, x:x+w])):.1f})")
        saved += 1

    return saved


# ── MAIN ───────────────────────────────────────────────────────────────────────

def main():
    # Clear previous run
    if os.path.exists(DIAGRAMS_OUT):
        for f in os.listdir(DIAGRAMS_OUT):
            if f.endswith(".png"):
                os.remove(os.path.join(DIAGRAMS_OUT, f))
    os.makedirs(DIAGRAMS_OUT, exist_ok=True)

    page_files = sorted([
        f for f in os.listdir(IMAGES_IN)
        if f.startswith("page_") and f.endswith(".png")
    ])

    if not page_files:
        print("No page PNG files found in:", IMAGES_IN)
        return

    print(f"Scanning {len(page_files)} pages for diagrams...")
    print(f"Output: {DIAGRAMS_OUT}")
    print()

    total = 0
    for fname in page_files:
        page_num = int(fname.replace("page_", "").replace(".png", ""))
        print(f"Page {page_num:2d}: {fname}")
        n = extract_diagrams_from_page(
            os.path.join(IMAGES_IN, fname), page_num, DIAGRAMS_OUT
        )
        if n == 0:
            print(f"    (no diagrams detected)")
        total += n

    print()
    print("=" * 60)
    print(f"DONE! Total diagrams extracted: {total}")
    print(f"Saved to: {DIAGRAMS_OUT}")
    print("=" * 60)


if __name__ == "__main__":
    main()
