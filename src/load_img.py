import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
from PIL import Image, ImageTk
TYPES = [("Изображения", "*.jpg *.jpeg *.png *.bmp *.gif *.webp *.tif *.tiff"), ("Все файлы", "*.*")]
BG, FG, DIM = "#111111", "#e8e8e8", "#8a8a8a"
MIN_ZOOM, MAX_ZOOM, STEP = 1.0, 8.0, 1.2
def fit_scale(w, h, bw, bh):
    """Масштаб «фото целиком в окне»; маленькие фото не растягиваются."""
    return min(bw / w, bh / h, 1.0) if min(w, h, bw, bh) > 0 else 1.0
class Viewer(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Просмотр фото")
        self.geometry("900x650")
        self.minsize(420, 320)
        self.configure(bg=BG)
        self.img = self.tk_img = self.path = self.job = self.drag = None
        self.zoom = MIN_ZOOM
        self.cx = self.cy = 0.0
        bar = tk.Frame(self, bg=BG)
        bar.pack(fill="x", padx=10, pady=(10, 6))
        tk.Button(bar, text="Открыть…", command=self.open, bg="#2d2d2d", fg=FG,
                  activebackground="#3d3d3d", activeforeground=FG, relief="flat",
                  padx=14, pady=6, cursor="hand2").pack(side="left")
        tk.Label(bar, text="колесо — зум · перетаскивание — сдвиг · 0 — вписать · Esc — закрыть",
                 bg=BG, fg=DIM).pack(side="left", padx=12)
        self.cv = tk.Canvas(self, bg=BG, highlightthickness=0)
        self.cv.pack(fill="both", expand=True, padx=10, pady=6)
        self.st = tk.Label(self, text="Файл не выбран", bg=BG, fg=DIM, anchor="w")
        self.st.pack(fill="x", padx=10, pady=(0, 8))
        self.tip = self.cv.create_text(0, 0, text="Нажмите «Открыть…», чтобы выбрать фото",
                                       fill="#5c5c5c", font=("Segoe UI", 12))
        center = lambda e: self.zoom_at(self.cv.winfo_width() / 2, self.cv.winfo_height() / 2, e)
        for seq, fn in [
            ("<Escape>", lambda e: self.destroy()),
            ("<Control-o>", lambda e: self.open()),
            ("<Double-Button-1>", lambda e: self.reset()),
            ("<KeyPress-0>", lambda e: self.reset()),
            ("<KeyPress-plus>", lambda e: center(STEP)),
            ("<KeyPress-equal>", lambda e: center(STEP)),
            ("<KeyPress-minus>", lambda e: center(1 / STEP)),
            ("<MouseWheel>", self.wheel),
            ("<Button-4>", lambda e: self.zoom_at(e.x, e.y, STEP)),
            ("<Button-5>", lambda e: self.zoom_at(e.x, e.y, 1 / STEP)),
            ("<ButtonPress-1>", lambda e: setattr(self, "drag", (e.x, e.y))),
            ("<B1-Motion>", self.pan),
        ]:
            self.bind(seq, fn)
        self.cv.bind("<Configure>", self.on_resize)
    # - файл
    def open(self):
        p = filedialog.askopenfilename(parent=self, title="Выберите фото", filetypes=TYPES)
        if p:
            self.load(p)
    def load(self, path):
        p = Path(path)
        try:
            with Image.open(p) as im:
                im.load()
                self.img = im.copy()
        except Exception as exc:  # noqa: BLE001 — любую ошибку показываем пользователю
            messagebox.showerror("Не удалось открыть", f"{p.name}\n\n{exc}", parent=self)
            return
        self.path, self.zoom = p, MIN_ZOOM
        self.cx, self.cy = self.img.width / 2, self.img.height / 2
        self.title(f"{p.name} — просмотр фото")
        self.redraw()
    # - геометрия
    def geom(self):
        """Масштаб, размер видимой части и её центр — единственное место с расчётами."""
        cw, ch = max(1, self.cv.winfo_width()), max(1, self.cv.winfo_height())
        s = fit_scale(self.img.width, self.img.height, cw, ch) * self.zoom
        vw, vh = min(self.img.width, cw / s), min(self.img.height, ch / s)
        cx = min(max(self.cx, vw / 2), self.img.width - vw / 2)
        cy = min(max(self.cy, vh / 2), self.img.height - vh / 2)
        return cw, ch, s, vw, vh, cx, cy
    def to_image(self, sx, sy):
        """Координата окна → координата фото (чтобы точка под курсором не убегала)."""
        cw, ch, s, vw, vh, cx, cy = self.geom()
        left, top = (cw - vw * s) / 2, (ch - vh * s) / 2
        return (sx - left) / s + cx - vw / 2, (sy - top) / s + cy - vh / 2
    # - зум и сдвиг
    def wheel(self, e):
        if e.delta:
            self.zoom_at(e.x, e.y, STEP ** (e.delta / 120))
    def zoom_at(self, sx, sy, f):
        if self.img is None:
            return
        z = min(max(self.zoom * f, MIN_ZOOM), MAX_ZOOM)
        if abs(z - self.zoom) < 1e-9:
            return
        ix, iy = self.to_image(sx, sy)   # точка под курсором до зума
        self.zoom = z
        cw, ch, s, *_ = self.geom()
        self.cx, self.cy = ix + (cw / 2 - sx) / s, iy + (ch / 2 - sy) / s
        self.redraw()
    def pan(self, e):
        if self.img is None or not self.drag:
            return
        s = self.geom()[2]
        self.cx -= (e.x - self.drag[0]) / s
        self.cy -= (e.y - self.drag[1]) / s
        self.drag = (e.x, e.y)
        self.redraw()
    def reset(self):
        if self.img is not None:
            self.zoom, self.cx, self.cy = MIN_ZOOM, self.img.width / 2, self.img.height / 2
            self.redraw()
    # - отрисовка
    def on_resize(self, _e):
        if self.img is None:
            self.cv.coords(self.tip, self.cv.winfo_width() // 2, self.cv.winfo_height() // 2)
            return
        if self.job:
            self.after_cancel(self.job)
        self.job = self.after(80, self.redraw)
    def redraw(self):
        self.job = None
        if self.img is None:
            return
        cw, ch, s, vw, vh, cx, cy = self.geom()
        iw, ih = self.img.size
        box = (max(0, round(cx - vw / 2)), max(0, round(cy - vh / 2)),
               min(iw, round(cx + vw / 2)), min(ih, round(cy + vh / 2)))
        crop = self.img.crop(box)
        size = max(1, round((box[2] - box[0]) * s)), max(1, round((box[3] - box[1]) * s))
        resample = Image.Resampling.LANCZOS if s < 1 else Image.Resampling.BICUBIC
        self.tk_img = ImageTk.PhotoImage(crop.resize(size, resample))
        self.cv.delete("all")
        self.cv.create_image(cw // 2, ch // 2, image=self.tk_img, anchor="center")
        fmt = self.img.format or self.path.suffix.lstrip(".").upper()
        self.st.configure(text=f"{self.path.name} · {self.img.width}×{self.img.height} px · "
                               f"{fmt} · зум {round(self.zoom * 100)}%")
if __name__ == "__main__":
    Viewer().mainloop()