"""
run_convert.py - CLI script to convert a single PDF to Markdown with images extracted.
"""
import converter
import os
import sys

pdf_path = (sys.argv[1] if len(sys.argv) > 1 else r"input.pdf")
out_dir = (sys.argv[2] if len(sys.argv) > 2 else r"output")

pdf_base = os.path.splitext(os.path.basename(pdf_path))[0]
images_folder = os.path.join(out_dir, pdf_base + "_images")

print("Reading PDF info...")
try:
    info = converter.get_pdf_info(pdf_path)
    print(f"  File    : {info['file_name']}")
    print(f"  Pages   : {info['page_count']}")
    print(f"  Size    : {info['file_size_formatted']}")
    print(f"  Title   : {info['title']}")
    print(f"  Author  : {info['author']}")
except Exception as e:
    print(f"ERROR reading PDF: {e}")
    sys.exit(1)

print()
print("Converting PDF -> Markdown (with image extraction)...")
try:
    md_text, stats = converter.convert_pdf_to_markdown(
        pdf_path=pdf_path,
        write_images=True,
        images_folder=images_folder,
        page_separators=True,
        table_output="markdown",
    )
except Exception as e:
    print(f"ERROR during conversion: {e}")
    sys.exit(1)

out_md = os.path.join(out_dir, pdf_base + ".md")
with open(out_md, "w", encoding="utf-8") as f:
    f.write(md_text)

# Count extracted images
img_count = 0
if os.path.exists(images_folder):
    img_count = len([
        x for x in os.listdir(images_folder)
        if os.path.isfile(os.path.join(images_folder, x))
    ])

print()
print("=" * 60)
print("CONVERSION COMPLETE!")
print("=" * 60)
print(f"  Markdown file : {out_md}")
print(f"  Images folder : {images_folder}")
print(f"  Pages conv.   : {stats['pages_converted']} / {stats['total_pages']}")
print(f"  Words         : {stats['word_count']:,}")
print(f"  Characters    : {stats['char_count']:,}")
print(f"  Est. Tokens   : ~{stats['estimated_tokens']:,}")
print(f"  Images saved  : {img_count}")
print(f"  Time taken    : {stats['elapsed_seconds']:.2f}s")
print("=" * 60)
