
"""
File Organizer Pro — CustomTkinter Edition
A professional, feature-rich file sorting utility for Windows.

Requirements:
    pip install customtkinter
"""

import sys
import os
import shutil
import threading
import time
import json
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk

# ── Theme ─────────────────────────────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ── File type registry ─────────────────────────────────────────────────────────
DEFAULT_FILE_TYPES: dict[str, list[str]] = {
    "Images":    [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg",
                  ".ico", ".jfif", ".tiff", ".raw", ".heic"],
    "Videos":    [".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm",
                  ".m4v", ".3gp"],
    "Music":     [".mp3", ".wav", ".aac", ".flac", ".ogg", ".wma", ".m4a",
                  ".opus"],
    "Documents": [".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
                  ".txt", ".rtf", ".odt", ".ods", ".odp", ".csv", ".md"],
    "Archives":  [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz"],
    "Code":      [".py", ".js", ".ts", ".html", ".css", ".java", ".c", ".cpp",
                  ".h", ".php", ".json", ".xml", ".yaml", ".yml", ".sh",
                  ".ps1", ".rb", ".go", ".rs", ".swift"],
    "Programs":  [".exe", ".msi", ".bat", ".cmd", ".com"],
    "System":    [".dll", ".sys", ".ini", ".reg", ".inf"],
    "Database":  [".db", ".sql", ".sqlite", ".mdb", ".accdb"],
    "Mobile":    [".apk", ".jar", ".war", ".ipa"],
    "Fonts":     [".ttf", ".otf", ".woff", ".woff2"],
    "Others":    [".iso", ".bin", ".dat", ".log", ".tmp", ".bak"],
}

CONFIG_FILE = Path.home() / ".file_organizer_pro.json"


# ── Helpers ───────────────────────────────────────────────────────────────────
def load_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"file_types": DEFAULT_FILE_TYPES, "last_folder": ""}


def save_config(config: dict) -> None:
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
    except Exception:
        pass


def human_size(size_bytes: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"


# ── Main Application ──────────────────────────────────────────────────────────
class FileOrganizerApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.config_data = load_config()
        self.file_types: dict[str, list[str]] = self.config_data.get(
            "file_types", DEFAULT_FILE_TYPES
        )
        self.selected_folder: Path | None = None
        self.preview_items: list[tuple[str, str]] = []   # (src_path, category)
        self.is_running = False
        self.undo_log: list[tuple[str, str]] = []        # (dest, src)

        self._build_ui()
        last = self.config_data.get("last_folder", "")
        if last and Path(last).is_dir():
            self._set_folder(Path(last))

    # ── UI Construction ───────────────────────────────────────────────────────
    def _build_ui(self):
        self.title("File Organizer Pro")
        self.geometry("900x680")
        self.minsize(780, 580)
        self.resizable(True, True)

        # ── Grid layout: left sidebar | right main ──────────────────────────
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_main()

    # ── Sidebar ───────────────────────────────────────────────────────────────
    def _build_sidebar(self):
        sidebar = ctk.CTkFrame(self, width=210, corner_radius=0)
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_rowconfigure(8, weight=1)
        sidebar.grid_propagate(False)

        # Logo / title
        logo_lbl = ctk.CTkLabel(
            sidebar, text="📂  Organizer",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        logo_lbl.grid(row=0, column=0, padx=20, pady=(24, 4))

        version_lbl = ctk.CTkLabel(
            sidebar, text="Pro Edition",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        version_lbl.grid(row=1, column=0, padx=20, pady=(0, 20))

        ctk.CTkFrame(sidebar, height=1, fg_color="#2a2a3e").grid(row=2, column=0, sticky="ew", padx=10, pady=2)

        # Navigation buttons
        nav_items = [
            ("🗂  Organize",      self._tab_organize),
            ("👁  Preview",       self._tab_preview),
            ("↩  Undo Last",     self._do_undo),
            ("⚙  File Types",    self._tab_filetypes),
            ("📊  Statistics",    self._tab_statistics),
        ]
        for i, (label, cmd) in enumerate(nav_items):
            btn = ctk.CTkButton(
                sidebar, text=label, anchor="w",
                font=ctk.CTkFont(size=13),
                fg_color="transparent",
                hover_color=("gray85", "gray25"),
                text_color=("gray10", "gray90"),
                command=cmd,
                height=38,
            )
            btn.grid(row=3 + i, column=0, padx=10, pady=2, sticky="ew")

        # Appearance toggle at bottom
        ctk.CTkFrame(sidebar, height=1, fg_color="#2a2a3e").grid(row=9, column=0, sticky="ew", padx=10, pady=2)
        mode_menu = ctk.CTkOptionMenu(
            sidebar,
            values=["Dark", "Light", "System"],
            command=lambda m: ctk.set_appearance_mode(m),
            width=120,
        )
        mode_menu.set("Dark")
        mode_menu.grid(row=10, column=0, padx=20, pady=(8, 20))

    # ── Main area ─────────────────────────────────────────────────────────────
    def _build_main(self):
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=16, pady=16)
        self.main_frame.grid_rowconfigure(1, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)

        # ── Folder picker bar ─────────────────────────────────────────────
        folder_bar = ctk.CTkFrame(self.main_frame)
        folder_bar.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        folder_bar.grid_columnconfigure(1, weight=1)

        ctk.CTkButton(
            folder_bar, text="Choose Folder",
            width=130, command=self._pick_folder,
            font=ctk.CTkFont(weight="bold"),
        ).grid(row=0, column=0, padx=(12, 8), pady=10)

        self.folder_label = ctk.CTkLabel(
            folder_bar, text="No folder selected",
            font=ctk.CTkFont(size=12),
            text_color="gray",
            anchor="w",
        )
        self.folder_label.grid(row=0, column=1, sticky="ew", padx=4)

        ctk.CTkButton(
            folder_bar, text="📋 Scan",
            width=80, command=self._do_scan,
        ).grid(row=0, column=2, padx=4, pady=10)

        ctk.CTkButton(
            folder_bar, text="▶ Run",
            width=80, command=self._do_organize,
            fg_color="#1f6aa5",
        ).grid(row=0, column=3, padx=(4, 12), pady=10)

        # ── Content area (tabbed via self._content) ───────────────────────
        self.content_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.content_frame.grid(row=1, column=0, sticky="nsew")
        self.content_frame.grid_rowconfigure(0, weight=1)
        self.content_frame.grid_columnconfigure(0, weight=1)

        # ── Status bar ────────────────────────────────────────────────────
        status_bar = ctk.CTkFrame(self.main_frame, height=32)
        status_bar.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        status_bar.grid_columnconfigure(0, weight=1)
        status_bar.grid_propagate(False)

        self.status_label = ctk.CTkLabel(
            status_bar, text="Ready.",
            font=ctk.CTkFont(size=11),
            text_color="gray",
            anchor="w",
        )
        self.status_label.grid(row=0, column=0, sticky="w", padx=12)

        self.progress_bar = ctk.CTkProgressBar(status_bar, width=160, height=8)
        self.progress_bar.set(0)
        self.progress_bar.grid(row=0, column=1, padx=(0, 12))

        # Show organize tab by default
        self._tab_organize()

    # ── Tab: Organize ─────────────────────────────────────────────────────────
    def _tab_organize(self):
        self._clear_content()
        frame = ctk.CTkScrollableFrame(self.content_frame, label_text="Category Filters")
        frame.grid(row=0, column=0, sticky="nsew")
        frame.grid_columnconfigure((0, 1, 2), weight=1)

        self.category_vars: dict[str, ctk.BooleanVar] = {}
        self.category_rename: dict[str, ctk.StringVar] = {}

        colors = ["#1a6b3f", "#1f6aa5", "#7a3bb5", "#b55a00",
                  "#b50050", "#2e6e6e", "#6e3010", "#1a5080",
                  "#506e00", "#5e1a6e", "#6e5000"]

        for idx, (cat, exts) in enumerate(self.file_types.items()):
            var = ctk.BooleanVar(value=True)
            self.category_vars[cat] = var

            col = idx % 3
            row = idx // 3

            card = ctk.CTkFrame(frame)
            card.grid(row=row, column=col, padx=6, pady=6, sticky="nsew")

            check = ctk.CTkCheckBox(
                card, text=cat, variable=var,
                font=ctk.CTkFont(weight="bold"),
                checkbox_width=18, checkbox_height=18,
            )
            check.grid(row=0, column=0, padx=10, pady=(10, 4), sticky="w")

            ext_text = "  ".join(exts[:5])
            if len(exts) > 5:
                ext_text += f" +{len(exts) - 5}"
            ctk.CTkLabel(
                card, text=ext_text,
                font=ctk.CTkFont(size=10),
                text_color="gray",
                wraplength=180, justify="left"
            ).grid(row=1, column=0, padx=12, pady=(0, 10), sticky="w")

        # Options row
        opt_frame = ctk.CTkFrame(frame)
        opt_frame.grid(
            row=(len(self.file_types) // 3) + 1, column=0,
            columnspan=3, sticky="ew", padx=6, pady=(12, 6)
        )
        opt_frame.grid_columnconfigure((0, 1, 2), weight=1)

        self.skip_hidden_var = ctk.BooleanVar(value=True)
        self.skip_existing_var = ctk.BooleanVar(value=True)
        self.dry_run_var = ctk.BooleanVar(value=False)

        ctk.CTkCheckBox(opt_frame, text="Skip hidden files",
                         variable=self.skip_hidden_var).grid(
            row=0, column=0, padx=12, pady=8, sticky="w")
        ctk.CTkCheckBox(opt_frame, text="Skip if file already exists",
                         variable=self.skip_existing_var).grid(
            row=0, column=1, padx=12, pady=8, sticky="w")
        ctk.CTkCheckBox(opt_frame, text="Dry run (no actual moves)",
                         variable=self.dry_run_var).grid(
            row=0, column=2, padx=12, pady=8, sticky="w")

    # ── Tab: Preview ─────────────────────────────────────────────────────────
    def _tab_preview(self):
        self._clear_content()
        outer = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        outer.grid(row=0, column=0, sticky="nsew")
        outer.grid_rowconfigure(1, weight=1)
        outer.grid_columnconfigure(0, weight=1)

        info = ctk.CTkLabel(
            outer,
            text="Click  📋 Scan  in the toolbar to preview files before moving them.",
            font=ctk.CTkFont(size=12), text_color="gray"
        )
        info.grid(row=0, column=0, pady=(0, 8), sticky="w")

        scroll = ctk.CTkScrollableFrame(outer, label_text="Files to be moved")
        scroll.grid(row=1, column=0, sticky="nsew")
        scroll.grid_columnconfigure((0, 1, 2, 3), weight=1)

        if not self.preview_items:
            ctk.CTkLabel(scroll, text="No scan results yet.",
                          text_color="gray").grid(row=0, column=0,
                                                  columnspan=4, pady=20)
            return

        headers = ("File name", "Category", "Size", "Modified")
        for col, h in enumerate(headers):
            ctk.CTkLabel(
                scroll, text=h,
                font=ctk.CTkFont(weight="bold", size=12),
                text_color="gray"
            ).grid(row=0, column=col, padx=10, pady=(4, 2), sticky="w")

        for row_i, (src, cat) in enumerate(self.preview_items, start=1):
            p = Path(src)
            try:
                stat = p.stat()
                size_str = human_size(stat.st_size)
                mtime = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
            except Exception:
                size_str = "?"
                mtime = "?"

            bg = ("gray93", "gray18") if row_i % 2 == 0 else ("gray98", "gray15")

            for col, text in enumerate((p.name, cat, size_str, mtime)):
                ctk.CTkLabel(
                    scroll, text=text,
                    font=ctk.CTkFont(size=11),
                    anchor="w",
                    fg_color=bg,
                ).grid(row=row_i, column=col, padx=2, pady=1, sticky="ew")

    # ── Tab: File Types ───────────────────────────────────────────────────────
    def _tab_filetypes(self):
        self._clear_content()
        frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        frame.grid(row=0, column=0, sticky="nsew")
        frame.grid_rowconfigure(1, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        top = ctk.CTkFrame(frame, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", pady=(0, 8))

        ctk.CTkLabel(
            top, text="Manage extension-to-category mappings:",
            font=ctk.CTkFont(size=12)
        ).pack(side="left")

        ctk.CTkButton(top, text="+ Add Category",
                       command=self._add_category, width=130).pack(side="right")
        ctk.CTkButton(top, text="Reset Defaults",
                       command=self._reset_defaults,
                       width=120, fg_color="gray30").pack(side="right", padx=8)

        scroll = ctk.CTkScrollableFrame(frame, label_text="Extension Mappings")
        scroll.grid(row=1, column=0, sticky="nsew")
        scroll.grid_columnconfigure(1, weight=1)

        self._ext_widgets: dict[str, ctk.CTkEntry] = {}

        for row_i, (cat, exts) in enumerate(self.file_types.items()):
            ctk.CTkLabel(
                scroll, text=cat,
                font=ctk.CTkFont(weight="bold", size=12),
                width=100, anchor="w"
            ).grid(row=row_i, column=0, padx=(8, 4), pady=5, sticky="w")

            ent = ctk.CTkEntry(scroll, font=ctk.CTkFont(size=11))
            ent.insert(0, "  ".join(exts))
            ent.grid(row=row_i, column=1, padx=4, pady=5, sticky="ew")
            self._ext_widgets[cat] = ent

            ctk.CTkButton(
                scroll, text="✓", width=32,
                command=lambda c=cat: self._save_category(c),
            ).grid(row=row_i, column=2, padx=(4, 2), pady=5)

            ctk.CTkButton(
                scroll, text="✕", width=32,
                fg_color="gray30",
                command=lambda c=cat: self._delete_category(c),
            ).grid(row=row_i, column=3, padx=(2, 8), pady=5)

    # ── Tab: Statistics ───────────────────────────────────────────────────────
    def _tab_statistics(self):
        self._clear_content()
        frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        frame.grid(row=0, column=0, sticky="nsew")
        frame.grid_columnconfigure((0, 1, 2), weight=1)

        if not self.selected_folder:
            ctk.CTkLabel(frame, text="Select a folder first.",
                          text_color="gray").grid(row=0, column=0, columnspan=3, pady=40)
            return

        self._set_status("Counting files…")
        counts: dict[str, int] = {}
        total_size = 0
        total_files = 0

        ext_to_cat = {
            ext: cat
            for cat, exts in self.file_types.items()
            for ext in exts
        }

        try:
            for f in self.selected_folder.iterdir():
                if f.is_file():
                    total_files += 1
                    try:
                        total_size += f.stat().st_size
                    except Exception:
                        pass
                    cat = ext_to_cat.get(f.suffix.lower(), "Unknown")
                    counts[cat] = counts.get(cat, 0) + 1
        except Exception as e:
            self._set_status(f"Error: {e}")
            return

        # Summary cards
        summary = [
            ("Total Files", str(total_files)),
            ("Total Size", human_size(total_size)),
            ("Categories", str(len(counts))),
        ]
        for col, (label, val) in enumerate(summary):
            card = ctk.CTkFrame(frame)
            card.grid(row=0, column=col, padx=8, pady=8, sticky="nsew")
            ctk.CTkLabel(card, text=val,
                          font=ctk.CTkFont(size=28, weight="bold")).pack(pady=(14, 0))
            ctk.CTkLabel(card, text=label,
                          font=ctk.CTkFont(size=12), text_color="gray").pack(pady=(0, 14))

        # Bar chart (canvas)
        chart_frame = ctk.CTkFrame(frame)
        chart_frame.grid(row=1, column=0, columnspan=3,
                          padx=8, pady=12, sticky="nsew")
        frame.grid_rowconfigure(1, weight=1)

        canvas = tk.Canvas(
            chart_frame, bg="#1a1a2e", highlightthickness=0, height=260
        )
        canvas.pack(fill="both", expand=True, padx=12, pady=12)
        canvas.bind("<Configure>", lambda e: self._draw_bars(
            canvas, counts, e.width, e.height
        ))
        self._draw_bars(canvas, counts, 700, 260)
        self._set_status(f"Statistics: {total_files} files  |  {human_size(total_size)}")

    def _draw_bars(self, canvas: tk.Canvas, counts: dict, w: int, h: int):
        canvas.delete("all")
        if not counts:
            return
        margin_l, margin_b, margin_t = 50, 50, 20
        bar_area_w = w - margin_l - 20
        bar_area_h = h - margin_b - margin_t
        sorted_items = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:12]
        max_val = max(v for _, v in sorted_items) or 1
        n = len(sorted_items)
        slot_w = bar_area_w / n
        bar_w = max(8, slot_w * 0.6)

        palette = ["#4e9af1", "#42c88a", "#f1c84e", "#f15c80",
                   "#a04ef1", "#f17c4e", "#4ef1e5", "#f14ea4",
                   "#7af14e", "#f14e4e", "#4e78f1", "#c8f14e"]

        for i, (cat, val) in enumerate(sorted_items):
            x_center = margin_l + i * slot_w + slot_w / 2
            bar_h = (val / max_val) * bar_area_h
            x0 = x_center - bar_w / 2
            x1 = x_center + bar_w / 2
            y0 = margin_t + bar_area_h - bar_h
            y1 = margin_t + bar_area_h
            color = palette[i % len(palette)]
            canvas.create_rectangle(x0, y0, x1, y1, fill=color, outline="")
            canvas.create_text(
                x_center, y0 - 6,
                text=str(val), fill="white",
                font=("Helvetica", 9, "bold")
            )
            # Rotated label (approximate with short clipping)
            label = cat[:8]
            canvas.create_text(
                x_center, y1 + 10,
                text=label, fill="#aaaaaa",
                font=("Helvetica", 8), angle=30
            )

        # Y-axis line
        canvas.create_line(
            margin_l, margin_t, margin_l, margin_t + bar_area_h,
            fill="#444", width=1
        )

    # ── Actions ───────────────────────────────────────────────────────────────
    def _pick_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self._set_folder(Path(folder))

    def _set_folder(self, path: Path):
        self.selected_folder = path
        self.folder_label.configure(
            text=str(path), text_color=("gray10", "gray90")
        )
        self.config_data["last_folder"] = str(path)
        save_config(self.config_data)
        self._set_status(f"Folder: {path}")

    def _do_scan(self):
        if not self.selected_folder:
            messagebox.showwarning("No Folder", "Please choose a folder first.")
            return
        self.preview_items = []
        ext_to_cat = {
            ext: cat
            for cat, exts in self.file_types.items()
            for ext in exts
        }
        try:
            enabled = {
                cat for cat, var in getattr(self, "category_vars", {}).items()
                if var.get()
            } or set(self.file_types.keys())

            for f in self.selected_folder.iterdir():
                if not f.is_file():
                    continue
                if getattr(self, "skip_hidden_var", None) and \
                        self.skip_hidden_var.get() and f.name.startswith("."):
                    continue
                cat = ext_to_cat.get(f.suffix.lower(), "Unknown")
                if cat in enabled or cat == "Unknown":
                    self.preview_items.append((str(f), cat))
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return

        count = len(self.preview_items)
        self._set_status(f"Scan complete — {count} file(s) found.")
        self._tab_preview()

    def _do_organize(self):
        if not self.selected_folder:
            messagebox.showwarning("No Folder", "Please choose a folder first.")
            return
        if self.is_running:
            return

        dry = getattr(self, "dry_run_var", None) and self.dry_run_var.get()
        enabled_cats = {
            cat for cat, var in getattr(self, "category_vars", {}).items()
            if var.get()
        } or set(self.file_types.keys())

        ext_to_cat = {
            ext: cat
            for cat, exts in self.file_types.items()
            for ext in exts
        }

        def worker():
            self.is_running = True
            self.undo_log.clear()
            moved = skipped = errors = 0

            try:
                all_files = [
                    f for f in self.selected_folder.iterdir()
                    if f.is_file()
                ]
                total = len(all_files)

                for idx, file in enumerate(all_files):
                    # Skip hidden files
                    if getattr(self, "skip_hidden_var", None) and \
                            self.skip_hidden_var.get() and file.name.startswith("."):
                        skipped += 1
                        continue

                    suffix = file.suffix.lower()
                    cat = ext_to_cat.get(suffix, "Unknown")

                    if cat != "Unknown" and cat not in enabled_cats:
                        skipped += 1
                        continue

                    dest_dir = self.selected_folder / cat
                    dest_file = dest_dir / file.name

                    if getattr(self, "skip_existing_var", None) and \
                            self.skip_existing_var.get() and dest_file.exists():
                        skipped += 1
                        continue

                    try:
                        if not dry:
                            dest_dir.mkdir(exist_ok=True)
                            shutil.move(str(file), str(dest_file))
                            self.undo_log.append((str(dest_file), str(file)))
                        moved += 1
                    except Exception:
                        errors += 1

                    # Update progress
                    progress = (idx + 1) / total
                    self.progress_bar.set(progress)
                    self._set_status(
                        f"{'[DRY RUN] ' if dry else ''}Processing {idx + 1}/{total}…"
                    )
                    time.sleep(0.002)   # slight delay for visual feedback

            except Exception as e:
                messagebox.showerror("Error", str(e))
            finally:
                self.is_running = False
                tag = "[DRY RUN] " if dry else ""
                summary = (
                    f"{tag}Done — Moved: {moved}  |  "
                    f"Skipped: {skipped}  |  Errors: {errors}"
                )
                self._set_status(summary)
                self.progress_bar.set(1 if moved else 0)
                if not dry:
                    messagebox.showinfo("Complete", summary)

        threading.Thread(target=worker, daemon=True).start()

    def _do_undo(self):
        if not self.undo_log:
            messagebox.showinfo("Undo", "Nothing to undo.")
            return
        restored = 0
        for dest, src in reversed(self.undo_log):
            try:
                shutil.move(dest, src)
                restored += 1
            except Exception:
                pass
        self.undo_log.clear()
        self._set_status(f"Undo complete — {restored} file(s) restored.")
        messagebox.showinfo("Undo", f"{restored} file(s) moved back to original location.")

    # ── File Type Management ──────────────────────────────────────────────────
    def _save_category(self, cat: str):
        raw = self._ext_widgets[cat].get()
        exts = [e.strip() for e in raw.split() if e.strip()]
        # Ensure leading dot
        exts = [e if e.startswith(".") else f".{e}" for e in exts]
        self.file_types[cat] = exts
        self.config_data["file_types"] = self.file_types
        save_config(self.config_data)
        self._set_status(f"Category '{cat}' saved with {len(exts)} extension(s).")

    def _delete_category(self, cat: str):
        if messagebox.askyesno("Delete", f"Remove category '{cat}'?"):
            self.file_types.pop(cat, None)
            self.config_data["file_types"] = self.file_types
            save_config(self.config_data)
            self._tab_filetypes()

    def _add_category(self):
        dialog = ctk.CTkInputDialog(
            text="New category name:", title="Add Category"
        )
        name = dialog.get_input()
        if name and name.strip():
            name = name.strip()
            if name not in self.file_types:
                self.file_types[name] = []
                self.config_data["file_types"] = self.file_types
                save_config(self.config_data)
            self._tab_filetypes()

    def _reset_defaults(self):
        if messagebox.askyesno("Reset", "Reset all categories to defaults?"):
            self.file_types = dict(DEFAULT_FILE_TYPES)
            self.config_data["file_types"] = self.file_types
            save_config(self.config_data)
            self._tab_filetypes()

    # ── Utilities ─────────────────────────────────────────────────────────────
    def _clear_content(self):
        for w in self.content_frame.winfo_children():
            w.destroy()

    def _set_status(self, msg: str):
        try:
            self.status_label.configure(text=msg)
        except Exception:
            pass


# ── Entry point ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = FileOrganizerApp()
    app.mainloop()



















