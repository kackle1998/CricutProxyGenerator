import os
import sys
import math
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageEnhance
import numpy as np

# ========= EDIT ME (background path) =========
BACKGROUND_FILENAME = "CricutTMPL.png"

def resource_path(relative_path: str) -> str:
    try:
        base_path = sys._MEIPASS  # PyInstaller
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

BACKGROUND_PATH = resource_path(BACKGROUND_FILENAME)
# ============================================

portraitX, portraitY = 763, 1058
landscapeX, landscapeY = 1058, 763

# Grid slots (6 max per page)
slots = [
    (165, 552,  165+landscapeX, 552+landscapeY),       # LeftTop
    (165, 1412, 165+landscapeX, 1412+landscapeY),     # LeftMid
    (268, 2274,  268+landscapeX, 2274+landscapeY),     # LeftBot
    
    (1224, 262,  1224+landscapeX, 262+landscapeY),     # RightTop
    (1327, 1122,  1327+landscapeX, 1122+landscapeY),   # RightMid
    (1327, 1983,  1327+landscapeX, 1983+landscapeY)    # RightBot
]

# 0.5 mm bleed at 300 DPI ≈ 6 px
BLEED_PX = 6


# --- Helper: add bleed by extending outermost pixels ---
def add_bleed(img, bleed_px):
    w, h = img.size
    new_img = Image.new("RGB", (w + 2*bleed_px, h + 2*bleed_px))
    new_img.paste(img, (bleed_px, bleed_px))

    # Top edge
    top = img.crop((0, 0, w, 1)).resize((w, bleed_px))
    new_img.paste(top, (bleed_px, 0))

    # Bottom edge
    bottom = img.crop((0, h-1, w, h)).resize((w, bleed_px))
    new_img.paste(bottom, (bleed_px, h+bleed_px))

    # Left edge
    left = img.crop((0, 0, 1, h)).resize((bleed_px, h))
    new_img.paste(left, (0, bleed_px))

    # Right edge
    right = img.crop((w-1, 0, w, h)).resize((bleed_px, h))
    new_img.paste(right, (w+bleed_px, bleed_px))

    # Corners
    tl = img.getpixel((0, 0))
    tr = img.getpixel((w-1, 0))
    bl = img.getpixel((0, h-1))
    br = img.getpixel((w-1, h-1))

    new_img.paste(Image.new("RGB", (bleed_px, bleed_px), tl), (0, 0))
    new_img.paste(Image.new("RGB", (bleed_px, bleed_px), tr), (w+bleed_px, 0))
    new_img.paste(Image.new("RGB", (bleed_px, bleed_px), bl), (0, h+bleed_px))
    new_img.paste(Image.new("RGB", (bleed_px, bleed_px), br), (w+bleed_px, h+bleed_px))

    return new_img


class CardGridApp:
    def __init__(self, root):
        self.root = root
        self.root.title("MTG Card Grid Generator")

        try:
            self.background_original = Image.open(BACKGROUND_PATH).convert("RGB")
        except Exception as e:
            messagebox.showerror(
                "Background not found",
                f"Could not load background at:\n{BACKGROUND_PATH}\n\n{e}"
            )
            self.background_original = None

        self.card_entries = []

        # --- Header ---
        head = tk.Frame(root)
        head.pack(pady=6, fill="x")
        tk.Label(head, text="Background:").pack(side="left")
        tk.Label(head, text=BACKGROUND_PATH, fg="#444").pack(side="left", padx=6)

        # --- Adjustment controls ---
        controls = tk.LabelFrame(root, text="Card Adjustments", padx=6, pady=6)
        controls.pack(padx=8, pady=8, fill="x")

        self.saturation_var = tk.DoubleVar(value=1.0)
        self.gamma_var = tk.DoubleVar(value=1.0)
        self.brightness_var = tk.DoubleVar(value=1.0)
        self.contrast_var = tk.DoubleVar(value=1.0)
        self.blackpoint_var = tk.DoubleVar(value=0.0)
        self.warmth_var = tk.DoubleVar(value=0.0)  # -1.0 (cool) to +1.0 (warm)

        self._make_control(controls, "Saturation", self.saturation_var, 0.0, 2.0, 0.1)
        self._make_control(controls, "Gamma", self.gamma_var, 0.1, 3.0, 0.1)
        self._make_control(controls, "Brightness", self.brightness_var, 0.0, 2.0, 0.1)
        self._make_control(controls, "Contrast", self.contrast_var, 0.0, 2.0, 0.1)
        self._make_control(controls, "Blackpoint", self.blackpoint_var, -50, 50, 1)
        self._make_control(controls, "Warmth", self.warmth_var, -1.0, 1.0, 0.05)

        # --- Buttons ---
        btns = tk.Frame(root)
        btns.pack(pady=6)
        tk.Button(btns, text="Add Cards", command=self.load_cards).pack(side="left", padx=4)
        tk.Button(btns, text="Clear All", command=self.clear_all).pack(side="left", padx=4)
        tk.Button(btns, text="Generate Output", command=self.generate_output).pack(side="left", padx=4)

        # --- Card list area ---
        self.card_frame = tk.Frame(root, borderwidth=1, relief="groove")
        self.card_frame.pack(padx=8, pady=8, fill="both", expand=True)

        # Fixed headers
        hdr = tk.Frame(self.card_frame)
        hdr.pack(fill="x", pady=(6,2))
        tk.Label(hdr, text="File", width=40, anchor="w").pack(side="left", padx=6)
        tk.Label(hdr, text="Copies").pack(side="left", padx=6)

        # Scrollable canvas + frame
        canvas = tk.Canvas(self.card_frame)
        scrollbar = tk.Scrollbar(self.card_frame, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        self.entries_container = tk.Frame(canvas)
        self.entries_container.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        self.entries_container_window = canvas.create_window((0,0), window=self.entries_container, anchor="nw")

        def _resize_entries_container(event):
            canvas.itemconfig(self.entries_container_window, width=event.width)
        canvas.bind("<Configure>", _resize_entries_container)

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

    # --- Helper to create a control row ---
    def _make_control(self, parent, label, var, frm, to, step):
        row = tk.Frame(parent)
        row.pack(fill="x", pady=2)
        tk.Label(row, text=label, width=12, anchor="w").pack(side="left")
        spin = tk.Spinbox(row, textvariable=var, from_=frm, to=to, increment=step, width=6)
        spin.pack(side="left")

    # --- Card management ---
    def load_cards(self):
        paths = filedialog.askopenfilenames(
            title="Select card images",
            filetypes=[("Image files", "*.png;*.jpg;*.jpeg;*.bmp")]
        )
        for path in paths:
            if path:
                self.add_card_entry(path)

    def add_card_entry(self, path: str):
        row_index = len(self.card_entries)
        bg_color = "#f9f9f9" if row_index % 2 == 0 else "#ffffff"

        frame = tk.Frame(self.entries_container, bg=bg_color)
        frame.pack(fill="x", pady=1)

        tk.Label(frame, text=os.path.basename(path), width=40, anchor="w", bg=bg_color).pack(side="left", padx=6)

        spinbox = tk.Spinbox(frame, from_=1, to=99, width=5)
        spinbox.pack(side="left", padx=(6,2))

        remove_btn = tk.Button(frame, text="❌ Remove", command=lambda: self.remove_card_entry(frame, path))
        remove_btn.pack(side="left", padx=2)

        self.card_entries.append((path, spinbox, frame))

    def remove_card_entry(self, frame: tk.Frame, path: str):
        for entry in self.card_entries:
            if entry[0] == path and entry[2] == frame:
                self.card_entries.remove(entry)
                break
        frame.destroy()

    def clear_all(self):
        for _, _, frame in self.card_entries:
            frame.destroy()
        self.card_entries.clear()

    # --- Image adjustments ---
    def adjust_card_image(self, img):
        img = ImageEnhance.Color(img).enhance(self.saturation_var.get())
        img = ImageEnhance.Brightness(img).enhance(self.brightness_var.get())
        img = ImageEnhance.Contrast(img).enhance(self.contrast_var.get())

        gamma = self.gamma_var.get()
        if gamma != 1.0:
            lut = [pow(i/255., 1.0/gamma)*255 for i in range(256)]
            lut = lut*3
            img = img.point(lut)

        black_shift = self.blackpoint_var.get()
        if black_shift != 0:
            arr = np.array(img, dtype=np.int16)
            arr = np.clip(arr + black_shift, 0, 255).astype(np.uint8)
            img = Image.fromarray(arr, mode="RGB")

        warmth = self.warmth_var.get()
        if warmth != 0.0:
            arr = np.array(img, dtype=np.float32)
            r, g, b = arr[:,:,0], arr[:,:,1], arr[:,:,2]
            if warmth > 0:
                r = np.clip(r * (1 + warmth*0.3), 0, 255)
                b = np.clip(b * (1 - warmth*0.3), 0, 255)
            else:
                r = np.clip(r * (1 + warmth*0.3), 0, 255)
                b = np.clip(b * (1 - warmth*0.3), 0, 255)
            arr[:,:,0], arr[:,:,2] = r, b
            img = Image.fromarray(arr.astype(np.uint8), mode="RGB")
        return img

    # --- Image composition ---
    def build_page(self, paths):
        bg = self.background_original.copy()
        for path, slot in zip(paths, slots):
            x1, y1, x2, y2 = slot
            w, h = x2 - x1, y2 - y1

            img = Image.open(path).convert("RGB")
            iw, ih = img.size

            slot_is_landscape = w > h
            img_is_landscape = iw > ih
            if slot_is_landscape != img_is_landscape:
                img = img.rotate(90, expand=True)

            img_resized = img.resize((w, h), Image.LANCZOS)
            img_adjusted = self.adjust_card_image(img_resized)

            img_with_bleed = add_bleed(img_adjusted, BLEED_PX)

            bg.paste(img_with_bleed, (x1 - BLEED_PX, y1 - BLEED_PX))
        return bg

    def generate_output(self):
        if self.background_original is None:
            messagebox.showerror("Error", "Background image is not loaded. Fix BACKGROUND_PATH and restart.")
            return

        if not self.card_entries:
            messagebox.showerror("Error", "Please add at least one card.")
            return

        expanded_paths = []
        for path, spinbox, _ in self.card_entries:
            try:
                count = max(0, int(spinbox.get()))
            except ValueError:
                count = 1
            expanded_paths.extend([path] * count)

        if not expanded_paths:
            messagebox.showerror("Error", "No copies selected.")
            return

        pages = math.ceil(len(expanded_paths) / 6)

        save_path = filedialog.asksaveasfilename(
            title="Save PDF",
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")]
        )
        if not save_path:
            return

        page_images = []
        for page in range(pages):
            batch = expanded_paths[page*6:(page+1)*6]
            composed = self.build_page(batch)
            page_images.append(composed)

        page_images[0].save(
            save_path, save_all=True, append_images=page_images[1:], resolution=300
        )

        messagebox.showinfo("Done", f"Exported {pages}-page PDF successfully!")


if __name__ == "__main__":
    root = tk.Tk()
    app = CardGridApp(root)
    root.mainloop()
