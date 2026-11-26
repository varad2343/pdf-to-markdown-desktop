"""
app.py - Modern Desktop GUI for PDF to Markdown Converter
Powered by CustomTkinter & PyMuPDF4LLM
"""

import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
import pyperclip

import converter

# Configure CustomTkinter default styling
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class PDFConverterApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Window setup
        self.title("PDF to Markdown Converter — LLM Ready")
        self.geometry("1100;740".replace(";", "x"))
        self.minsize(960, 680)

        # State variables - Single File
        self.current_pdf_path = ""
        self.current_pdf_info = None
        self.converted_markdown = ""
        self.last_saved_path = ""
        self.is_converting = False

        # State variables - Batch
        self.batch_files = []
        self.batch_output_folder = ""
        self.is_batch_converting = False

        # Build UI layout
        self.setup_layout()
        self.show_single_tab()

    def setup_layout(self):
        # Configure root grid
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # ============================================================
        # 1. Left Sidebar
        # ============================================================
        self.sidebar_frame = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(5, weight=1)

        # App Brand
        self.logo_label = ctk.CTkLabel(
            self.sidebar_frame,
            text="📑 PDF Converter",
            font=ctk.CTkFont(size=20, weight="bold"),
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 5))

        self.subtitle_label = ctk.CTkLabel(
            self.sidebar_frame,
            text="PDF ➔ Markdown (LLM)",
            font=ctk.CTkFont(size=12),
            text_color="gray",
        )
        self.subtitle_label.grid(row=1, column=0, padx=20, pady=(0, 20))

        # Navigation Buttons
        self.btn_nav_single = ctk.CTkButton(
            self.sidebar_frame,
            text="📄 Single File",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=38,
            anchor="w",
            command=self.show_single_tab,
        )
        self.btn_nav_single.grid(row=2, column=0, padx=15, pady=6, sticky="ew")

        self.btn_nav_batch = ctk.CTkButton(
            self.sidebar_frame,
            text="📚 Batch Converter",
            font=ctk.CTkFont(size=14),
            height=38,
            anchor="w",
            fg_color="transparent",
            text_color=("gray10", "gray90"),
            command=self.show_batch_tab,
        )
        self.btn_nav_batch.grid(row=3, column=0, padx=15, pady=6, sticky="ew")

        self.btn_nav_help = ctk.CTkButton(
            self.sidebar_frame,
            text="💡 Help & Tips",
            font=ctk.CTkFont(size=14),
            height=38,
            anchor="w",
            fg_color="transparent",
            text_color=("gray10", "gray90"),
            command=self.show_help_tab,
        )
        self.btn_nav_help.grid(row=4, column=0, padx=15, pady=6, sticky="ew")

        # Bottom Sidebar: Theme & Scaling controls
        self.theme_label = ctk.CTkLabel(
            self.sidebar_frame, text="Appearance Mode:", font=ctk.CTkFont(size=11)
        )
        self.theme_label.grid(row=6, column=0, padx=20, pady=(10, 0), sticky="w")

        self.theme_option = ctk.CTkOptionMenu(
            self.sidebar_frame,
            values=["Dark", "Light", "System"],
            command=self.change_appearance_mode,
        )
        self.theme_option.set("Dark")
        self.theme_option.grid(row=7, column=0, padx=20, pady=(5, 20), sticky="ew")

        # ============================================================
        # 2. Main Content Container
        # ============================================================
        self.content_container = ctk.CTkFrame(self, fg_color="transparent")
        self.content_container.grid(row=0, column=1, sticky="nsew", padx=15, pady=15)
        self.content_container.grid_rowconfigure(0, weight=1)
        self.content_container.grid_columnconfigure(0, weight=1)

        # Build the 3 tabs
        self.build_single_tab()
        self.build_batch_tab()
        self.build_help_tab()

    # ================================================================
    # TAB 1: Single File Converter
    # ================================================================
    def build_single_tab(self):
        self.single_frame = ctk.CTkFrame(self.content_container, fg_color="transparent")
        self.single_frame.grid(row=0, column=0, sticky="nsew")
        self.single_frame.grid_rowconfigure(2, weight=1)
        self.single_frame.grid_columnconfigure(0, weight=1)

        # Card 1: File Selection Card
        file_card = ctk.CTkFrame(self.single_frame, corner_radius=10)
        file_card.grid(row=0, column=0, sticky="ew", pady=(0, 10), padx=5)
        file_card.grid_columnconfigure(1, weight=1)

        self.btn_select_file = ctk.CTkButton(
            file_card,
            text="📂 Browse PDF File",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.browse_single_pdf,
            width=160,
            height=36,
        )
        self.btn_select_file.grid(row=0, column=0, padx=12, pady=12)

        self.lbl_selected_file = ctk.CTkLabel(
            file_card,
            text="No PDF file selected. Click 'Browse PDF File' to choose one.",
            font=ctk.CTkFont(size=13),
            anchor="w",
            text_color="gray",
        )
        self.lbl_selected_file.grid(row=0, column=1, padx=10, pady=12, sticky="ew")

        # Badges row for metadata
        self.meta_frame = ctk.CTkFrame(file_card, fg_color="transparent")
        self.meta_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=12, pady=(0, 10))

        self.lbl_meta_pages = ctk.CTkLabel(
            self.meta_frame,
            text="Pages: —",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=("gray85", "gray25"),
            corner_radius=6,
            padx=10,
            pady=3,
        )
        self.lbl_meta_pages.pack(side="left", padx=(0, 10))

        self.lbl_meta_size = ctk.CTkLabel(
            self.meta_frame,
            text="Size: —",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=("gray85", "gray25"),
            corner_radius=6,
            padx=10,
            pady=3,
        )
        self.lbl_meta_size.pack(side="left", padx=(0, 10))

        self.lbl_meta_title = ctk.CTkLabel(
            self.meta_frame,
            text="Title: —",
            font=ctk.CTkFont(size=12),
            text_color="gray",
        )
        self.lbl_meta_title.pack(side="left", padx=5)

        # Card 2: Options & Action Controls
        opt_card = ctk.CTkFrame(self.single_frame, corner_radius=10)
        opt_card.grid(row=1, column=0, sticky="ew", pady=(0, 10), padx=5)
        opt_card.grid_columnconfigure((0, 1, 2), weight=1)

        # Left: Page selection
        page_box = ctk.CTkFrame(opt_card, fg_color="transparent")
        page_box.grid(row=0, column=0, padx=12, pady=10, sticky="nw")

        self.page_choice_var = ctk.StringVar(value="all")
        self.radio_all = ctk.CTkRadioButton(
            page_box,
            text="All Pages",
            variable=self.page_choice_var,
            value="all",
            command=self.toggle_page_range_entry,
        )
        self.radio_all.pack(anchor="w", pady=(0, 5))

        self.radio_custom = ctk.CTkRadioButton(
            page_box,
            text="Specific Pages:",
            variable=self.page_choice_var,
            value="custom",
            command=self.toggle_page_range_entry,
        )
        self.radio_custom.pack(anchor="w", pady=(0, 5))

        self.entry_pages = ctk.CTkEntry(
            page_box,
            placeholder_text="e.g. 1-3, 5, 8-10",
            width=160,
            state="disabled",
        )
        self.entry_pages.pack(anchor="w")

        # Center: Formatting options
        fmt_box = ctk.CTkFrame(opt_card, fg_color="transparent")
        fmt_box.grid(row=0, column=1, padx=12, pady=10, sticky="nw")

        self.chk_images_var = ctk.BooleanVar(value=False)
        self.chk_images = ctk.CTkCheckBox(
            fmt_box,
            text="Extract & save images",
            variable=self.chk_images_var,
        )
        self.chk_images.pack(anchor="w", pady=(0, 8))

        self.chk_separators_var = ctk.BooleanVar(value=True)
        self.chk_separators = ctk.CTkCheckBox(
            fmt_box,
            text="Include page separator tags",
            variable=self.chk_separators_var,
        )
        self.chk_separators.pack(anchor="w", pady=(0, 8))

        # Tables output dropdown
        table_label = ctk.CTkLabel(fmt_box, text="Tables Format:", font=ctk.CTkFont(size=12))
        table_label.pack(anchor="w")
        self.table_output_option = ctk.CTkOptionMenu(
            fmt_box,
            values=["Markdown Tables", "HTML Tables"],
            height=28,
            width=150,
        )
        self.table_output_option.set("Markdown Tables")
        self.table_output_option.pack(anchor="w", pady=(2, 0))

        # Right: Convert Action & Progress
        action_box = ctk.CTkFrame(opt_card, fg_color="transparent")
        action_box.grid(row=0, column=2, padx=12, pady=10, sticky="ne")

        self.btn_convert = ctk.CTkButton(
            action_box,
            text="⚡ Convert to Markdown",
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=("#1f6aa5", "#144870"),
            hover_color=("#144870", "#0e314d"),
            height=44,
            width=200,
            command=self.start_single_conversion,
        )
        self.btn_convert.pack(pady=(0, 8))

        self.progress_bar = ctk.CTkProgressBar(action_box, width=200)
        self.progress_bar.pack(pady=(0, 5))
        self.progress_bar.set(0)

        self.lbl_status = ctk.CTkLabel(
            action_box,
            text="Ready",
            font=ctk.CTkFont(size=12),
            text_color="gray",
        )
        self.lbl_status.pack()

        # Card 3: Live Preview & Action Buttons
        preview_card = ctk.CTkFrame(self.single_frame, corner_radius=10)
        preview_card.grid(row=2, column=0, sticky="nsew", padx=5, pady=(0, 5))
        preview_card.grid_rowconfigure(1, weight=1)
        preview_card.grid_columnconfigure(0, weight=1)

        # Header of preview: stats + action buttons
        prev_head = ctk.CTkFrame(preview_card, fg_color="transparent")
        prev_head.grid(row=0, column=0, sticky="ew", padx=12, pady=8)
        prev_head.grid_columnconfigure(0, weight=1)

        # Stats on left
        self.lbl_stats = ctk.CTkLabel(
            prev_head,
            text="📝 Markdown Preview  |  Words: 0  •  Chars: 0  •  Est. LLM Tokens: 0",
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w",
        )
        self.lbl_stats.grid(row=0, column=0, sticky="w")

        # Action buttons on right
        btn_box = ctk.CTkFrame(prev_head, fg_color="transparent")
        btn_box.grid(row=0, column=1, sticky="e")

        self.btn_copy = ctk.CTkButton(
            btn_box,
            text="📋 Copy",
            width=90,
            height=30,
            command=self.copy_markdown_to_clipboard,
        )
        self.btn_copy.pack(side="left", padx=5)

        self.btn_save = ctk.CTkButton(
            btn_box,
            text="💾 Save .md",
            width=100,
            height=30,
            command=self.save_markdown_dialog,
        )
        self.btn_save.pack(side="left", padx=5)

        self.btn_open_folder = ctk.CTkButton(
            btn_box,
            text="📂 Open Folder",
            width=110,
            height=30,
            fg_color="transparent",
            border_width=1,
            command=self.open_output_folder,
        )
        self.btn_open_folder.pack(side="left", padx=5)

        # Markdown Text Area
        self.txt_preview = ctk.CTkTextbox(
            preview_card,
            wrap="word",
            font=ctk.CTkFont(family="Consolas", size=13),
            corner_radius=8,
        )
        self.txt_preview.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))

    # ================================================================
    # TAB 2: Batch Processing
    # ================================================================
    def build_batch_tab(self):
        self.batch_frame = ctk.CTkFrame(self.content_container, fg_color="transparent")
        self.batch_frame.grid_rowconfigure(2, weight=1)
        self.batch_frame.grid_columnconfigure(0, weight=1)

        # Batch Header & Controls
        batch_head = ctk.CTkFrame(self.batch_frame, corner_radius=10)
        batch_head.grid(row=0, column=0, sticky="ew", pady=(0, 10), padx=5)
        batch_head.grid_columnconfigure(3, weight=1)

        btn_add_files = ctk.CTkButton(
            batch_head,
            text="➕ Add PDF Files",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.batch_add_files,
            height=36,
        )
        btn_add_files.grid(row=0, column=0, padx=10, pady=12)

        btn_add_folder = ctk.CTkButton(
            batch_head,
            text="📁 Add Folder",
            font=ctk.CTkFont(size=13),
            command=self.batch_add_folder,
            height=36,
        )
        btn_add_folder.grid(row=0, column=1, padx=5, pady=12)

        btn_clear = ctk.CTkButton(
            batch_head,
            text="🗑️ Clear List",
            font=ctk.CTkFont(size=13),
            fg_color="transparent",
            border_width=1,
            command=self.batch_clear_list,
            height=36,
        )
        btn_clear.grid(row=0, column=2, padx=5, pady=12)

        self.lbl_batch_count = ctk.CTkLabel(
            batch_head,
            text="0 files queued",
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="e",
        )
        self.lbl_batch_count.grid(row=0, column=3, padx=15, pady=12, sticky="e")

        # Output Folder Picker Card
        folder_card = ctk.CTkFrame(self.batch_frame, corner_radius=10)
        folder_card.grid(row=1, column=0, sticky="ew", pady=(0, 10), padx=5)
        folder_card.grid_columnconfigure(1, weight=1)

        btn_out_folder = ctk.CTkButton(
            folder_card,
            text="📂 Output Folder",
            command=self.batch_choose_output_folder,
            height=34,
            width=140,
        )
        btn_out_folder.grid(row=0, column=0, padx=10, pady=10)

        self.lbl_batch_out_folder = ctk.CTkLabel(
            folder_card,
            text="Default: Same folder as each PDF file",
            font=ctk.CTkFont(size=12),
            anchor="w",
            text_color="gray",
        )
        self.lbl_batch_out_folder.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        # Queue List Box
        self.batch_list_card = ctk.CTkFrame(self.batch_frame, corner_radius=10)
        self.batch_list_card.grid(row=2, column=0, sticky="nsew", padx=5, pady=(0, 10))
        self.batch_list_card.grid_rowconfigure(1, weight=1)
        self.batch_list_card.grid_columnconfigure(0, weight=1)

        queue_title = ctk.CTkLabel(
            self.batch_list_card,
            text="Queued PDF Documents",
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w",
        )
        queue_title.grid(row=0, column=0, sticky="w", padx=12, pady=(10, 5))

        self.batch_scroll_list = ctk.CTkScrollableFrame(self.batch_list_card, corner_radius=8)
        self.batch_scroll_list.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))

        # Batch Action Footer
        batch_foot = ctk.CTkFrame(self.batch_frame, corner_radius=10)
        batch_foot.grid(row=3, column=0, sticky="ew", padx=5, pady=(0, 5))
        batch_foot.grid_columnconfigure(1, weight=1)

        self.btn_start_batch = ctk.CTkButton(
            batch_foot,
            text="⚡ Convert All to Markdown",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=42,
            width=220,
            command=self.start_batch_conversion,
        )
        self.btn_start_batch.grid(row=0, column=0, padx=12, pady=12)

        self.batch_progress_bar = ctk.CTkProgressBar(batch_foot)
        self.batch_progress_bar.grid(row=0, column=1, padx=15, pady=12, sticky="ew")
        self.batch_progress_bar.set(0)

        self.lbl_batch_status = ctk.CTkLabel(
            batch_foot,
            text="Ready",
            font=ctk.CTkFont(size=12),
            text_color="gray",
        )
        self.lbl_batch_status.grid(row=0, column=2, padx=15, pady=12)

    # ================================================================
    # TAB 3: Help & Tips
    # ================================================================
    def build_help_tab(self):
        self.help_frame = ctk.CTkFrame(self.content_container, fg_color="transparent")
        self.help_frame.grid_rowconfigure(0, weight=1)
        self.help_frame.grid_columnconfigure(0, weight=1)

        help_scroll = ctk.CTkScrollableFrame(self.help_frame, corner_radius=10)
        help_scroll.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        help_text = """
# 📑 PDF to Markdown Converter (PyMuPDF4LLM)

Welcome to your native Windows PDF to Markdown conversion desktop app!

---

### 🌟 Why PyMuPDF4LLM?
Traditional PDF text extractors lose reading order, tables, headers, and code snippets.
**PyMuPDF4LLM** is purpose-built to produce structured, clean Markdown ideal for:
- 🤖 **LLMs & AI Workflows**: Feed high-fidelity documents to ChatGPT, Claude, Gemini, or local models.
- 🔍 **RAG Pipelines**: Perfect for chunking documents into vector databases without scrambled text.
- 📊 **Table Extraction**: Retains complex table layouts in pristine Markdown or HTML grid syntax.
- 🖼️ **Image References**: Automatically extracts embedded diagrams/charts and inserts image links.

---

### 🎯 Features & Guide

1. **Single File Conversion**:
   - Click **Browse PDF File** to load any PDF.
   - Choose **All Pages** or enter specific pages/ranges like `1-5, 8, 12-15`.
   - Optionally toggle **Extract & save images** to extract figures into a folder.
   - Choose between **Markdown Tables** (standard) or **HTML Tables** (for complex merged cells).
   - Click **Convert to Markdown** to view real-time converted text with estimated token counts!

2. **Batch Processing**:
   - Add multiple files or entire folders of PDFs.
   - Process dozens of PDFs concurrently into individual `.md` files.

3. **Page Range Syntax**:
   - `1` : Page 1 only
   - `1-5` : Pages 1 through 5
   - `1-3, 7, 10-12` : Pages 1, 2, 3, 7, 10, 11, 12

---

### 💡 Pro-Tips for LLMs
- **Token Estimator**: The preview displays an estimated token count so you can easily verify if a document fits within your model's context window.
- **Page Separators**: Keeping page separators enabled makes it easy to ask LLMs questions referencing specific page numbers (e.g. *"Summarize the chart on page 4"*).
"""
        txt_help = ctk.CTkTextbox(
            help_scroll,
            wrap="word",
            font=ctk.CTkFont(size=13),
            fg_color="transparent",
        )
        txt_help.insert("1.0", help_text.strip())
        txt_help.configure(state="disabled")
        txt_help.pack(fill="both", expand=True, padx=15, pady=15)

    # ================================================================
    # Navigation Handlers
    # ================================================================
    def show_single_tab(self):
        self.batch_frame.grid_forget()
        self.help_frame.grid_forget()
        self.single_frame.grid(row=0, column=0, sticky="nsew")

        self.btn_nav_single.configure(fg_color=("#1f6aa5", "#144870"), text_color=("white", "white"))
        self.btn_nav_batch.configure(fg_color="transparent", text_color=("gray10", "gray90"))
        self.btn_nav_help.configure(fg_color="transparent", text_color=("gray10", "gray90"))

    def show_batch_tab(self):
        self.single_frame.grid_forget()
        self.help_frame.grid_forget()
        self.batch_frame.grid(row=0, column=0, sticky="nsew")

        self.btn_nav_batch.configure(fg_color=("#1f6aa5", "#144870"), text_color=("white", "white"))
        self.btn_nav_single.configure(fg_color="transparent", text_color=("gray10", "gray90"))
        self.btn_nav_help.configure(fg_color="transparent", text_color=("gray10", "gray90"))

    def show_help_tab(self):
        self.single_frame.grid_forget()
        self.batch_frame.grid_forget()
        self.help_frame.grid(row=0, column=0, sticky="nsew")

        self.btn_nav_help.configure(fg_color=("#1f6aa5", "#144870"), text_color=("white", "white"))
        self.btn_nav_single.configure(fg_color="transparent", text_color=("gray10", "gray90"))
        self.btn_nav_batch.configure(fg_color="transparent", text_color=("gray10", "gray90"))

    def change_appearance_mode(self, mode: str):
        ctk.set_appearance_mode(mode.lower())

    def toggle_page_range_entry(self):
        if self.page_choice_var.get() == "custom":
            self.entry_pages.configure(state="normal")
            self.entry_pages.focus()
        else:
            self.entry_pages.configure(state="disabled")

    # ================================================================
    # Single File Operations
    # ================================================================
    def browse_single_pdf(self):
        path = filedialog.askopenfilename(
            title="Select PDF Document",
            filetypes=[("PDF Documents", "*.pdf"), ("All Files", "*.*")],
        )
        if not path:
            return

        self.current_pdf_path = path
        self.lbl_selected_file.configure(text=os.path.basename(path), text_color=("gray10", "gray90"))

        try:
            info = converter.get_pdf_info(path)
            self.current_pdf_info = info
            self.lbl_meta_pages.configure(text=f"Pages: {info['page_count']}")
            self.lbl_meta_size.configure(text=f"Size: {info['file_size_formatted']}")
            title_text = info['title'] if info['title'] != "Untitled" else os.path.basename(path)
            self.lbl_meta_title.configure(text=f"Title: {title_text[:40]}")
            self.lbl_status.configure(text=f"Loaded {os.path.basename(path)}")
        except Exception as e:
            messagebox.showerror("Error Reading PDF", str(e))

    def start_single_conversion(self):
        if not self.current_pdf_path:
            messagebox.showwarning("No File Selected", "Please select a PDF file first by clicking 'Browse PDF File'.")
            return

        if self.is_converting:
            return

        self.is_converting = True
        self.btn_convert.configure(state="disabled", text="Converting...")
        self.progress_bar.configure(mode="indeterminate")
        self.progress_bar.start()
        self.lbl_status.configure(text="Extracting text & formatting...")

        # Run conversion in a separate thread so GUI never freezes
        threading.Thread(target=self._run_single_conversion_worker, daemon=True).start()

    def _run_single_conversion_worker(self):
        try:
            page_range = None
            if self.page_choice_var.get() == "custom":
                page_range = self.entry_pages.get()

            write_images = self.chk_images_var.get()
            page_separators = self.chk_separators_var.get()
            table_fmt = "html" if self.table_output_option.get() == "HTML Tables" else "markdown"

            md_text, stats = converter.convert_pdf_to_markdown(
                pdf_path=self.current_pdf_path,
                page_range_str=page_range,
                write_images=write_images,
                page_separators=page_separators,
                table_output=table_fmt,
            )

            self.after(0, lambda: self._on_single_conversion_success(md_text, stats))
        except Exception as e:
            err_msg = str(e)
            self.after(0, lambda: self._on_single_conversion_error(err_msg))

    def _on_single_conversion_success(self, md_text: str, stats: dict):
        self.is_converting = False
        self.progress_bar.stop()
        self.progress_bar.configure(mode="determinate")
        self.progress_bar.set(1.0)
        self.btn_convert.configure(state="normal", text="⚡ Convert to Markdown")

        self.converted_markdown = md_text

        # Update preview textbox
        self.txt_preview.delete("1.0", "end")
        self.txt_preview.insert("1.0", md_text)

        # Update stats
        words = stats["word_count"]
        chars = stats["char_count"]
        tokens = stats["estimated_tokens"]
        pages = stats["pages_converted"]
        sec = stats["elapsed_seconds"]

        self.lbl_stats.configure(
            text=f"📝 Markdown Preview  |  Words: {words:,}  •  Chars: {chars:,}  •  Est. Tokens: ~{tokens:,}"
        )
        self.lbl_status.configure(
            text=f"✓ Done! Converted {pages} page(s) in {sec:.2f}s"
        )

    def _on_single_conversion_error(self, err_msg: str):
        self.is_converting = False
        self.progress_bar.stop()
        self.progress_bar.configure(mode="determinate")
        self.progress_bar.set(0)
        self.btn_convert.configure(state="normal", text="⚡ Convert to Markdown")
        self.lbl_status.configure(text="Conversion failed")
        messagebox.showerror("Conversion Failed", f"An error occurred during conversion:\n\n{err_msg}")

    def copy_markdown_to_clipboard(self):
        text = self.txt_preview.get("1.0", "end").strip()
        if not text:
            messagebox.showinfo("Nothing to Copy", "Convert a PDF file first to generate Markdown text.")
            return

        pyperclip.copy(text)
        old_text = self.btn_copy.cget("text")
        self.btn_copy.configure(text="✓ Copied!")
        self.after(1500, lambda: self.btn_copy.configure(text=old_text))

    def save_markdown_dialog(self):
        text = self.txt_preview.get("1.0", "end").strip()
        if not text:
            messagebox.showinfo("Nothing to Save", "Convert a PDF file first before saving.")
            return

        default_name = "converted.md"
        initial_dir = ""
        if self.current_pdf_path:
            base = os.path.splitext(os.path.basename(self.current_pdf_path))[0]
            default_name = f"{base}.md"
            initial_dir = os.path.dirname(self.current_pdf_path)

        out_path = filedialog.asksaveasfilename(
            title="Save Markdown File",
            defaultextension=".md",
            initialdir=initial_dir,
            initialfile=default_name,
            filetypes=[("Markdown Document", "*.md"), ("Text Document", "*.txt"), ("All Files", "*.*")],
        )

        if not out_path:
            return

        try:
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(text)
            self.last_saved_path = out_path
            self.lbl_status.configure(text=f"Saved to {os.path.basename(out_path)}")
            messagebox.showinfo("Saved Successfully", f"Markdown successfully saved to:\n{out_path}")
        except Exception as e:
            messagebox.showerror("Error Saving File", str(e))

    def open_output_folder(self):
        target = ""
        if self.last_saved_path and os.path.exists(self.last_saved_path):
            target = os.path.dirname(self.last_saved_path)
        elif self.current_pdf_path and os.path.exists(self.current_pdf_path):
            target = os.path.dirname(self.current_pdf_path)

        if target and os.path.exists(target):
            os.startfile(target)
        else:
            messagebox.showinfo("Folder Not Found", "No file has been saved or opened yet.")

    # ================================================================
    # Batch Processing Operations
    # ================================================================
    def batch_add_files(self):
        files = filedialog.askopenfilenames(
            title="Select PDF Files for Batch Conversion",
            filetypes=[("PDF Documents", "*.pdf")],
        )
        if not files:
            return

        for f in files:
            if f not in self.batch_files:
                self.batch_files.append(f)

        self.refresh_batch_ui()

    def batch_add_folder(self):
        folder = filedialog.askdirectory(title="Select Folder Containing PDFs")
        if not folder:
            return

        found = 0
        for root, _, files in os.walk(folder):
            for file in files:
                if file.lower().endswith(".pdf"):
                    full_p = os.path.join(root, file)
                    if full_p not in self.batch_files:
                        self.batch_files.append(full_p)
                        found += 1

        self.refresh_batch_ui()
        if found == 0:
            messagebox.showinfo("No PDFs Found", f"No PDF files found in:\n{folder}")

    def batch_clear_list(self):
        if self.is_batch_converting:
            return
        self.batch_files.clear()
        self.refresh_batch_ui()

    def batch_choose_output_folder(self):
        folder = filedialog.askdirectory(title="Select Output Folder for Markdown Files")
        if folder:
            self.batch_output_folder = folder
            self.lbl_batch_out_folder.configure(
                text=folder, text_color=("gray10", "gray90")
            )

    def refresh_batch_ui(self):
        # Clear existing rows in scrollable frame
        for widget in self.batch_scroll_list.winfo_children():
            widget.destroy()

        self.lbl_batch_count.configure(text=f"{len(self.batch_files)} file(s) queued")

        if not self.batch_files:
            empty_lbl = ctk.CTkLabel(
                self.batch_scroll_list,
                text="No files added yet. Click 'Add PDF Files' or 'Add Folder' to start.",
                text_color="gray",
            )
            empty_lbl.pack(pady=20)
            return

        for idx, fpath in enumerate(self.batch_files):
            row = ctk.CTkFrame(self.batch_scroll_list, fg_color=("gray90", "gray20"), corner_radius=6)
            row.pack(fill="x", expand=True, pady=3, padx=5)
            row.grid_columnconfigure(1, weight=1)

            num_lbl = ctk.CTkLabel(row, text=f"{idx+1}.", width=30)
            num_lbl.grid(row=0, column=0, padx=5, pady=6)

            name_lbl = ctk.CTkLabel(row, text=os.path.basename(fpath), anchor="w")
            name_lbl.grid(row=0, column=1, padx=5, pady=6, sticky="ew")

            status_lbl = ctk.CTkLabel(
                row,
                text="Pending",
                font=ctk.CTkFont(size=11),
                text_color="gray",
                width=80,
            )
            status_lbl.grid(row=0, column=2, padx=10, pady=6)

    def start_batch_conversion(self):
        if not self.batch_files:
            messagebox.showwarning("No Files", "Please add at least one PDF file to convert.")
            return

        if self.is_batch_converting:
            return

        self.is_batch_converting = True
        self.btn_start_batch.configure(state="disabled", text="Converting Batch...")
        self.batch_progress_bar.set(0)
        self.lbl_batch_status.configure(text=f"Converting 0 / {len(self.batch_files)}...")

        threading.Thread(target=self._run_batch_worker, daemon=True).start()

    def _run_batch_worker(self):
        total = len(self.batch_files)
        success_count = 0
        error_count = 0

        for i, pdf_path in enumerate(self.batch_files):
            try:
                base_name = os.path.splitext(os.path.basename(pdf_path))[0]
                if self.batch_output_folder:
                    out_dir = self.batch_output_folder
                else:
                    out_dir = os.path.dirname(pdf_path)

                out_md_path = os.path.join(out_dir, f"{base_name}.md")

                md_text, _ = converter.convert_pdf_to_markdown(pdf_path=pdf_path)
                with open(out_md_path, "w", encoding="utf-8") as f:
                    f.write(md_text)

                success_count += 1
            except Exception as e:
                error_count += 1

            progress = (i + 1) / total
            self.after(0, lambda p=progress, current=i+1: self._update_batch_progress(p, current, total))

        self.after(0, lambda: self._on_batch_finish(success_count, error_count))

    def _update_batch_progress(self, progress: float, current: int, total: int):
        self.batch_progress_bar.set(progress)
        self.lbl_batch_status.configure(text=f"Processed {current} of {total}")

    def _on_batch_finish(self, success_count: int, error_count: int):
        self.is_batch_converting = False
        self.btn_start_batch.configure(state="normal", text="⚡ Convert All to Markdown")
        self.lbl_batch_status.configure(text=f"Finished! {success_count} succeeded, {error_count} failed")

        msg = f"Batch conversion complete!\n\nSuccessfully converted: {success_count}\nFailed: {error_count}"
        if self.batch_output_folder:
            msg += f"\n\nFiles saved in: {self.batch_output_folder}"
        messagebox.showinfo("Batch Conversion Complete", msg)


if __name__ == "__main__":
    app = PDFConverterApp()
    app.mainloop()
