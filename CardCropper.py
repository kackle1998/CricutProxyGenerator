import os
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image
import numpy as np

def crop_card(image: Image.Image) -> Image.Image:
    """Crop MTG card image by 9.5% width and 6.8% height (centered)."""
    w, h = image.size
    # compute crop margins
    left = int(w * 0.095 / 2)
    right = w - left
    top = int(h * 0.068 / 2)
    bottom = h - top
    return image.crop((left, top, right, bottom))

def process_files(filepaths):
    if not filepaths:
        messagebox.showwarning("No files", "No images selected.")
        return
    
    out_dir = os.path.join(os.path.dirname(filepaths[0]), "cropped")
    os.makedirs(out_dir, exist_ok=True)

    for path in filepaths:
        try:
            img = Image.open(path)
            cropped = crop_card(img)
            base = os.path.basename(path)
            out_path = os.path.join(out_dir, base)
            cropped.save(out_path)
        except Exception as e:
            print(f"Failed to process {path}: {e}")

    messagebox.showinfo("Done", f"Cropped images saved in:\n{out_dir}")

def select_files():
    filepaths = filedialog.askopenfilenames(
        title="Select card images",
        filetypes=[("Image Files", "*.png *.jpg *.jpeg *.bmp *.tiff")]
    )
    process_files(filepaths)

def main():
    root = tk.Tk()
    root.title("MTG Card Cropper")
    root.geometry("300x150")

    lbl = tk.Label(root, text="Crop MTG card borders by 9.5% / 6.8%")
    lbl.pack(pady=20)

    btn = tk.Button(root, text="Select Images", command=select_files)
    btn.pack(pady=10)

    root.mainloop()

if __name__ == "__main__":
    main()
