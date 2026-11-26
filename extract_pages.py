import sys
"""
extract_pages.py - Extract all pages of a scanned PDF as high-quality PNG images.
"""
import pymupdf
import os

pdf_path = (sys.argv[1] if len(sys.argv) > 1 else r"input.pdf")
out_dir = (sys.argv[2] if len(sys.argv) > 2 else r"output/images")
os.makedirs(out_dir, exist_ok=True)

print(f"Opening: {os.path.basename(pdf_path)}")
doc = pymupdf.open(pdf_path)
print(f"Total pages: {len(doc)}")
print(f"Output folder: {out_dir}")
print()

# Render at 2x zoom (144 DPI equivalent) for clean images
mat = pymupdf.Matrix(2.0, 2.0)

for i, page in enumerate(doc):
    pix = page.get_pixmap(matrix=mat, alpha=False)
    img_path = os.path.join(out_dir, f"page_{i+1:03d}.png")
    pix.save(img_path)
    size_kb = os.path.getsize(img_path) / 1024
    print(f"  Page {i+1:2d} -> {os.path.basename(img_path)}  ({size_kb:.0f} KB)")

doc.close()
print()
print(f"Done! {len(doc)} page images saved to:")
print(f"  {out_dir}")

# Also try to extract any embedded images within pages
print()
print("Checking for embedded images in PDF...")
doc2 = pymupdf.open(pdf_path)
total_embedded = 0
for page_num in range(len(doc2)):
    page = doc2[page_num]
    img_list = page.get_images(full=True)
    for img_index, img in enumerate(img_list):
        xref = img[0]
        base_image = doc2.extract_image(xref)
        img_bytes = base_image["image"]
        img_ext = base_image["ext"]
        out_path = os.path.join(out_dir, f"embedded_p{page_num+1:03d}_img{img_index+1:02d}.{img_ext}")
        with open(out_path, "wb") as f:
            f.write(img_bytes)
        size_kb = len(img_bytes) / 1024
        print(f"  Embedded img: page {page_num+1}, img {img_index+1} -> {os.path.basename(out_path)} ({size_kb:.0f} KB)")
        total_embedded += 1
doc2.close()

if total_embedded == 0:
    print("  No separate embedded images found (pages are fully rasterized).")
else:
    print(f"  Total embedded images extracted: {total_embedded}")
