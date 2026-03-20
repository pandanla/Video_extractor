import os
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
import cv2


# ── Core logic ────────────────────────────────────────────────────────────────

def extract_one_frame_per_second(video_path, output_folder, progress_cb=None):
    """Extract one frame per second from a video file."""
    os.makedirs(output_folder, exist_ok=True)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video file:\n{video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps == 0:
        cap.release()
        raise RuntimeError("FPS is zero – cannot process this file.")

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frame_interval = max(1, int(fps))

    frame_id = 0
    saved_id = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_id % frame_interval == 0:
            filename = os.path.join(output_folder, f"frame_{saved_id:04d}.png")
            cv2.imwrite(filename, frame)
            saved_id += 1

        frame_id += 1

        if progress_cb and total_frames > 0:
            progress_cb(frame_id / total_frames)

    cap.release()
    return saved_id


# ── GUI ───────────────────────────────────────────────────────────────────────

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Frame Extractor")
        self.resizable(False, False)
        self._build_ui()
        self._center()

    # ── Layout ────────────────────────────────────────────────────────────────

    def _build_ui(self):
        PAD = 18
        W   = 520

        self.configure(bg="#1a1a2e")

        # ── Header
        header = tk.Frame(self, bg="#16213e", pady=14)
        header.pack(fill="x")
        tk.Label(
            header, text="🎞  Frame Extractor",
            font=("Helvetica", 17, "bold"),
            fg="#e2c074", bg="#16213e"
        ).pack()
        tk.Label(
            header, text="Extracts one PNG per second from any video",
            font=("Helvetica", 10), fg="#8899aa", bg="#16213e"
        ).pack()

        body = tk.Frame(self, bg="#1a1a2e", padx=PAD, pady=PAD, width=W)
        body.pack(fill="x")

        # ── Video file picker
        self._make_label(body, "Video file")
        row1 = tk.Frame(body, bg="#1a1a2e")
        row1.pack(fill="x", pady=(4, 12))

        self.video_var = tk.StringVar()
        self._entry(row1, self.video_var).pack(side="left", fill="x", expand=True)
        self._button(row1, "Browse…", self._pick_video, small=True).pack(side="left", padx=(8, 0))

        # ── Output folder picker
        self._make_label(body, "Output folder")
        row2 = tk.Frame(body, bg="#1a1a2e")
        row2.pack(fill="x", pady=(4, 20))

        self.folder_var = tk.StringVar()
        self._entry(row2, self.folder_var).pack(side="left", fill="x", expand=True)
        self._button(row2, "Browse…", self._pick_folder, small=True).pack(side="left", padx=(8, 0))

        # ── Progress bar (hidden until processing starts)
        self.progress_frame = tk.Frame(body, bg="#1a1a2e")
        self.progress_frame.pack(fill="x", pady=(0, 12))
        self.progress_canvas = tk.Canvas(
            self.progress_frame, height=8,
            bg="#0f3460", highlightthickness=0
        )
        self.progress_canvas.pack(fill="x")
        self.progress_bar = self.progress_canvas.create_rectangle(
            0, 0, 0, 8, fill="#e2c074", outline=""
        )
        self.progress_frame.pack_forget()   # hide initially

        # ── Status label
        self.status_var = tk.StringVar(value="")
        self.status_lbl = tk.Label(
            body, textvariable=self.status_var,
            font=("Helvetica", 10), fg="#8899aa", bg="#1a1a2e",
            wraplength=W - PAD * 2, justify="left"
        )
        self.status_lbl.pack(fill="x", pady=(0, 14))

        # ── Run button
        self.run_btn = self._button(body, "Extract Frames", self._run)
        self.run_btn.pack(fill="x")

        # ── Footer
        tk.Label(
            self, text="Frames are saved as frame_0000.png, frame_0001.png …",
            font=("Helvetica", 9), fg="#4a5568", bg="#1a1a2e"
        ).pack(pady=(0, 14))

    # ── Widget helpers ────────────────────────────────────────────────────────

    def _make_label(self, parent, text):
        tk.Label(
            parent, text=text,
            font=("Helvetica", 10, "bold"),
            fg="#a0aec0", bg="#1a1a2e", anchor="w"
        ).pack(fill="x")

    def _entry(self, parent, var):
        return tk.Entry(
            parent, textvariable=var,
            font=("Helvetica", 11),
            bg="#0f3460", fg="#e2e8f0",
            insertbackground="#e2c074",
            relief="flat",
            bd=6
        )

    def _button(self, parent, text, cmd, small=False):
        return tk.Button(
            parent, text=text, command=cmd,
            font=("Helvetica", 10 if small else 12, "bold"),
            bg="#e2c074", fg="#1a1a2e",
            activebackground="#f0d080", activeforeground="#1a1a2e",
            relief="flat", cursor="hand2",
            padx=10, pady=6 if small else 10
        )

    # ── File / folder pickers ─────────────────────────────────────────────────

    def _pick_video(self):
        path = filedialog.askopenfilename(
            title="Select a video file",
            filetypes=[
                ("Video files", "*.mp4 *.mov *.avi *.mkv *.wmv *.flv *.webm"),
                ("All files",   "*.*")
            ]
        )
        if path:
            self.video_var.set(path)
            # Auto-suggest output folder next to the video
            if not self.folder_var.get():
                default_out = os.path.join(os.path.dirname(path), "frames_output")
                self.folder_var.set(default_out)

    def _pick_folder(self):
        path = filedialog.askdirectory(title="Select output folder")
        if path:
            self.folder_var.set(path)

    # ── Processing ────────────────────────────────────────────────────────────

    def _run(self):
        video  = self.video_var.get().strip()
        folder = self.folder_var.get().strip()

        if not video:
            messagebox.showwarning("Missing input", "Please select a video file first.")
            return
        if not os.path.isfile(video):
            messagebox.showerror("File not found", f"Cannot find:\n{video}")
            return
        if not folder:
            messagebox.showwarning("Missing output", "Please select an output folder.")
            return

        self.run_btn.config(state="disabled", text="Processing…")
        self.status_var.set("Starting…")
        self.progress_frame.pack(fill="x", pady=(0, 12))
        self._set_progress(0)

        thread = threading.Thread(target=self._worker, args=(video, folder), daemon=True)
        thread.start()

    def _worker(self, video, folder):
        try:
            n = extract_one_frame_per_second(
                video, folder,
                progress_cb=lambda p: self.after(0, self._set_progress, p)
            )
            self.after(0, self._done, n, folder)
        except Exception as exc:
            self.after(0, self._error, str(exc))

    def _done(self, n, folder):
        self._set_progress(1.0)
        self.status_var.set(f"✅  Done — {n} frame{'s' if n != 1 else ''} saved to:\n{folder}")
        self.status_lbl.config(fg="#68d391")
        self.run_btn.config(state="normal", text="Extract Frames")

    def _error(self, msg):
        self.progress_frame.pack_forget()
        self.status_var.set(f"❌  {msg}")
        self.status_lbl.config(fg="#fc8181")
        self.run_btn.config(state="normal", text="Extract Frames")

    def _set_progress(self, ratio):
        w = self.progress_canvas.winfo_width()
        self.progress_canvas.coords(self.progress_bar, 0, 0, int(w * ratio), 8)

    # ── Centering ─────────────────────────────────────────────────────────────

    def _center(self):
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        w  = self.winfo_width()
        h  = self.winfo_height()
        self.geometry(f"+{(sw - w) // 2}+{(sh - h) // 2}")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = App()
    app.mainloop()
