import sys
from pathlib import Path
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox

FILE_TYPES = {
    "Images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg", ".ico",".jfif"],
    "Videos": [".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm"],
    "Music": [".mp3", ".wav", ".aac", ".flac", ".ogg", ".wma"],
    "Documents": [".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".rtf", ".odt"],
    "Archives": [".zip", ".rar", ".7z", ".tar", ".gz"],
    "Code": [".py", ".js", ".html", ".css", ".java", ".c", ".cpp", ".php", ".json", ".xml"],
    "Programs": [".exe", ".msi", ".bat", ".cmd"],
    "System": [".dll", ".sys", ".ini", ".reg"],
    "Database": [".db", ".sql", ".sqlite", ".mdb", ".accdb"],
    "Mobile": [".apk", ".jar", ".war"],
    "Others": [".iso", ".bin", ".dat", ".log", ".tmp"]
}

selected_folder = None

def choose_folder():
    global selected_folder
    folder = filedialog.askdirectory()
    if folder:
        selected_folder = Path(folder)
        label_folder.config(text=f"📁 {selected_folder}")

def organize_files():
    if not selected_folder:
        messagebox.showwarning("Warning", "اختر مجلد أولاً")
        return

    try:
        for file in selected_folder.iterdir():
            if file.is_file():
                suffix = file.suffix.lower()
                moved = False

                for category, extensions in FILE_TYPES.items():
                    if suffix in extensions:
                        dest = selected_folder / category
                        dest.mkdir(exist_ok=True)
                        shutil.move(file, dest / file.name)
                        moved = True
                        break

                if not moved:
                    unknown = selected_folder / "Unknown"
                    unknown.mkdir(exist_ok=True)
                    shutil.move(file, unknown / file.name)

        messagebox.showinfo("Success", "تم التنظيم بنجاح")

    except Exception as e:
        messagebox.showerror("Error", str(e))

# GUI
root = tk.Tk()
root.title("File Organizer Pro")
root.geometry("400x250")

title = tk.Label(root, text="📂 File Organizer", font=("Arial", 16))
title.pack(pady=10)

btn_select = tk.Button(root, text="Choose Folder", command=choose_folder)
btn_select.pack(pady=5)

label_folder = tk.Label(root, text="No folder selected")
label_folder.pack(pady=5)

btn_run = tk.Button(root, text="Organize Files", command=organize_files)
btn_run.pack(pady=20)

root.mainloop()
