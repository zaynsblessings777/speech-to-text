import os
import time
import threading
import tkinter as tk
import speech_recognition as sr
from tkinter import filedialog, messagebox, ttk

from transcribe import convert_to_wav, transcribe_long_file_segments, listen_live


# --- Color palette ---
BG = "#f4f5f7"
CARD = "#ffffff"
BORDER = "#e2e4e9"
TEXT = "#1c1e21"
SUBTEXT = "#6b7280"
ACCENT = "#4f46e5"
ACCENT_HOVER = "#4338ca"
SUCCESS = "#16a34a"
ERROR = "#dc2626"
WARN = "#d97706"
LIVE_RED = "#c0392b"
PLACEHOLDER_FG = "#9aa0aa"
SEARCH_HL = "#fde68a"


def format_timestamp(seconds):
    seconds = int(seconds)
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def truncate_middle(text, max_len=48):
    if len(text) <= max_len:
        return text
    keep = max_len - 3
    head = keep // 2
    tail = keep - head
    return text[:head] + "..." + text[-tail:]


PLACEHOLDER_MSG = "Nothing transcribed yet. Choose a file or start live listening, then hit Transcribe."


class TranscriptApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Audio to Text Transcriber")
        self.root.geometry("780x640")
        self.root.minsize(600, 480)
        self.root.configure(bg=BG)

        self._listening = False
        self._transcribing = False
        self._placeholder_active = True
        self._live_start_time = None

        self._init_styles()

        self.audio_path = tk.StringVar()
        self.status_text = tk.StringVar(value="Choose an audio file or start live listening.")
        self.search_var = tk.StringVar()
        self.wordcount_var = tk.StringVar(value="0 words")
        self.progress_label_var = tk.StringVar(value="")

        self._build_menu()
        self._build_layout()
        self._show_placeholder()
        self._bind_shortcuts()

    # ---------- styling ----------

    def _init_styles(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("App.TFrame", background=BG)
        style.configure("Card.TFrame", background=CARD)
        style.configure("Card.TLabelframe", background=CARD, bordercolor=BORDER)
        style.configure("Card.TLabelframe.Label", background=CARD, foreground=SUBTEXT,
                         font=("Helvetica Neue", 11, "bold"))

        style.configure("Title.TLabel", background=BG, foreground=TEXT,
                         font=("Helvetica Neue", 20, "bold"))
        style.configure("Subtitle.TLabel", background=BG, foreground=SUBTEXT,
                         font=("Helvetica Neue", 12))
        style.configure("Path.TLabel", background=CARD, foreground=TEXT,
                         font=("Helvetica Neue", 12))
        style.configure("PathEmpty.TLabel", background=CARD, foreground=SUBTEXT,
                         font=("Helvetica Neue", 12, "italic"))
        style.configure("Meta.TLabel", background=BG, foreground=SUBTEXT,
                         font=("Helvetica Neue", 10))

        style.configure("Primary.TButton", background=ACCENT, foreground="white",
                         font=("Helvetica Neue", 11, "bold"), padding=(16, 9), borderwidth=0)
        style.map("Primary.TButton",
                  background=[("active", ACCENT_HOVER), ("disabled", "#c7c9d9")])

        style.configure("Secondary.TButton", background="#eef0f4", foreground=TEXT,
                         font=("Helvetica Neue", 11), padding=(14, 9), borderwidth=0)
        style.map("Secondary.TButton",
                  background=[("active", "#e2e4ea"), ("disabled", "#f2f3f6")])

        style.configure("Live.TButton", background="#fff1f0", foreground=LIVE_RED,
                         font=("Helvetica Neue", 11, "bold"), padding=(14, 9), borderwidth=0)
        style.map("Live.TButton",
                  background=[("active", "#ffe1df"), ("disabled", "#f2f3f6")])

        style.configure("thin.Horizontal.TProgressbar", troughcolor="#eceef2",
                         background=ACCENT, thickness=6)

    # ---------- menu ----------

    def _build_menu(self):
        menubar = tk.Menu(self.root)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Open Audio File…", accelerator="Ctrl+O", command=self.browse_file)
        file_menu.add_command(label="Save Transcript…", accelerator="Ctrl+S", command=self.save_transcript)
        file_menu.add_separator()
        file_menu.add_command(label="Quit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=file_menu)

        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label="Copy Transcript", accelerator="Ctrl+C", command=self.copy_transcript)
        edit_menu.add_command(label="Clear Transcript", command=self.clear_transcript)
        menubar.add_cascade(label="Edit", menu=edit_menu)

        self.root.config(menu=menubar)

    def _bind_shortcuts(self):
        self.root.bind("<Control-o>", lambda e: self.browse_file())
        self.root.bind("<Control-s>", lambda e: self.save_transcript())
        self.root.bind("<Control-f>", lambda e: self.search_entry.focus_set())

    # ---------- layout ----------

    def _build_layout(self):
        outer = ttk.Frame(self.root, style="App.TFrame")
        outer.pack(fill="both", expand=True, padx=24, pady=20)

        # --- Header ---
        header = ttk.Frame(outer, style="App.TFrame")
        header.pack(fill="x", pady=(0, 18))
        ttk.Label(header, text="\U0001F3A4  Audio to Text", style="Title.TLabel").pack(anchor="w")
        ttk.Label(header, text="Transcribe recordings or speak live \u2014 powered by your own pipeline.",
                  style="Subtitle.TLabel").pack(anchor="w", pady=(2, 0))

        # --- Source card ---
        source_card = ttk.LabelFrame(outer, text="AUDIO SOURCE", style="Card.TLabelframe")
        source_card.pack(fill="x", pady=(0, 14))

        source_row = ttk.Frame(source_card, style="Card.TFrame")
        source_row.pack(fill="x", padx=16, pady=(0, 16))

        path_wrap = tk.Frame(source_row, bg=CARD, highlightbackground=BORDER,
                              highlightthickness=1, bd=0)
        path_wrap.pack(side="left", fill="x", expand=True, ipady=6, ipadx=8)

        self.path_label = ttk.Label(path_wrap, text="No file selected", style="PathEmpty.TLabel")
        self.path_label.pack(side="left", fill="x", expand=True, anchor="w")

        self.clear_file_btn = ttk.Button(source_row, text="\u2715", width=3, style="Secondary.TButton",
                                          command=self.clear_file, state="disabled")
        self.clear_file_btn.pack(side="left", padx=(8, 0))

        ttk.Button(source_row, text="Browse\u2026", style="Secondary.TButton",
                   command=self.browse_file).pack(side="left", padx=(8, 0))

        # --- Actions card ---
        controls_card = ttk.LabelFrame(outer, text="ACTIONS", style="Card.TLabelframe")
        controls_card.pack(fill="x", pady=(0, 14))

        controls_row = ttk.Frame(controls_card, style="Card.TFrame")
        controls_row.pack(fill="x", padx=16, pady=(0, 10))

        self.transcribe_btn = ttk.Button(controls_row, text="\u25B6  Transcribe", style="Primary.TButton",
                                          command=self.start_transcription, state="disabled")
        self.transcribe_btn.pack(side="left")

        self.live_btn = ttk.Button(controls_row, text="\u25CF  Start Live", style="Live.TButton",
                                    command=self.toggle_live)
        self.live_btn.pack(side="left", padx=(10, 0))

        self.copy_btn = ttk.Button(controls_row, text="Copy", style="Secondary.TButton",
                                    command=self.copy_transcript, state="disabled")
        self.copy_btn.pack(side="left", padx=(10, 0))

        self.save_btn = ttk.Button(controls_row, text="\u2913  Save Transcript\u2026", style="Secondary.TButton",
                                    command=self.save_transcript, state="disabled")
        self.save_btn.pack(side="left", padx=(10, 0))

        progress_row = ttk.Frame(controls_card, style="Card.TFrame")
        progress_row.pack(fill="x", padx=16, pady=(0, 16))

        self.progress = ttk.Progressbar(progress_row, mode="determinate",
                                         style="thin.Horizontal.TProgressbar", maximum=100)
        self.progress.pack(side="left", fill="x", expand=True)

        ttk.Label(progress_row, textvariable=self.progress_label_var, style="Meta.TLabel",
                  width=16, anchor="e").pack(side="left", padx=(10, 0))

        # --- Transcript card ---
        transcript_card = ttk.LabelFrame(outer, text="TRANSCRIPT", style="Card.TLabelframe")
        transcript_card.pack(fill="both", expand=True, pady=(0, 14))

        search_row = ttk.Frame(transcript_card, style="Card.TFrame")
        search_row.pack(fill="x", padx=16, pady=(0, 8))

        self.search_entry = ttk.Entry(search_row, textvariable=self.search_var)
        self.search_entry.pack(side="left", fill="x", expand=True, ipady=3)
        self.search_entry.bind("<Return>", lambda e: self.run_search())

        ttk.Button(search_row, text="Find", style="Secondary.TButton",
                   command=self.run_search).pack(side="left", padx=(8, 0))

        self.match_label = ttk.Label(search_row, text="", style="Meta.TLabel", width=12, anchor="e")
        self.match_label.pack(side="left", padx=(8, 0))

        text_wrap = ttk.Frame(transcript_card, style="Card.TFrame")
        text_wrap.pack(fill="both", expand=True, padx=16, pady=(0, 12))

        text_scroll = ttk.Scrollbar(text_wrap)
        text_scroll.pack(side="right", fill="y")

        self.output_box = tk.Text(
            text_wrap, wrap="word", font=("Helvetica Neue", 13),
            relief="flat", bg=CARD, fg=TEXT, insertbackground=TEXT,
            highlightthickness=0, padx=4, pady=4,
            yscrollcommand=text_scroll.set,
        )
        self.output_box.pack(fill="both", expand=True, side="left")
        text_scroll.config(command=self.output_box.yview)
        self.output_box.bind("<KeyRelease>", lambda e: self._update_wordcount())

        self.output_box.tag_configure("timestamp", foreground=ACCENT,
                                       font=("Helvetica Neue", 11, "bold"))
        self.output_box.tag_configure("placeholder", foreground=PLACEHOLDER_FG,
                                       font=("Helvetica Neue", 13, "italic"))
        self.output_box.tag_configure("match", background=SEARCH_HL)

        # --- Status bar ---
        status_row = ttk.Frame(outer, style="App.TFrame")
        status_row.pack(fill="x")

        self.status_dot = tk.Canvas(status_row, width=10, height=10, bg=BG, highlightthickness=0)
        self.status_dot.pack(side="left")
        self._draw_status_dot(SUBTEXT)

        ttk.Label(status_row, textvariable=self.status_text, style="Subtitle.TLabel").pack(
            side="left", padx=(8, 0)
        )

        ttk.Label(status_row, textvariable=self.wordcount_var, style="Meta.TLabel").pack(
            side="right"
        )

    def _draw_status_dot(self, color):
        self.status_dot.delete("all")
        self.status_dot.create_oval(1, 1, 9, 9, fill=color, outline="")

    def _set_status(self, text, kind="neutral"):
        colors = {"neutral": SUBTEXT, "busy": WARN, "success": SUCCESS, "error": ERROR}
        self.status_text.set(text)
        self._draw_status_dot(colors.get(kind, SUBTEXT))

    # ---------- placeholder / text helpers ----------

    def _show_placeholder(self):
        self.output_box.delete("1.0", tk.END)
        self.output_box.insert("1.0", PLACEHOLDER_MSG)
        self.output_box.tag_add("placeholder", "1.0", "end")
        self._placeholder_active = True
        self._update_wordcount()

    def _clear_placeholder_if_needed(self):
        if self._placeholder_active:
            self.output_box.delete("1.0", tk.END)
            self._placeholder_active = False

    def _update_wordcount(self):
        if self._placeholder_active:
            self.wordcount_var.set("0 words")
            return
        content = self.output_box.get("1.0", tk.END).strip()
        words = len(content.split()) if content else 0
        self.wordcount_var.set(f"{words} word{'s' if words != 1 else ''}")

    # ---------- file selection ----------

    def browse_file(self):
        if self._listening or self._transcribing:
            return
        path = filedialog.askopenfilename(
            title="Select an audio file",
            filetypes=[("Audio files", "*.wav *.mp3 *.m4a *.flac *.ogg"), ("All files", "*.*")],
        )
        if path:
            self.audio_path.set(path)
            self.path_label.config(text=truncate_middle(path), style="Path.TLabel")
            self.clear_file_btn.config(state="normal")
            self.transcribe_btn.config(state="normal")
            self._set_status(f"Selected {os.path.basename(path)}", "neutral")

    def clear_file(self):
        self.audio_path.set("")
        self.path_label.config(text="No file selected", style="PathEmpty.TLabel")
        self.clear_file_btn.config(state="disabled")
        self.transcribe_btn.config(state="disabled")
        self._set_status("Choose an audio file or start live listening.", "neutral")

    # ---------- transcription ----------

    def start_transcription(self):
        path = self.audio_path.get()
        if not path:
            messagebox.showwarning("No file selected", "Please choose an audio file first.")
            return

        self._transcribing = True
        self.transcribe_btn.config(state="disabled")
        self.live_btn.config(state="disabled")
        self.copy_btn.config(state="disabled")
        self.save_btn.config(state="disabled")

        self._clear_placeholder_if_needed()
        self.output_box.delete("1.0", tk.END)
        self.progress["value"] = 0
        self.progress_label_var.set("0%")
        self._set_status("Transcribing\u2026 this can take a moment.", "busy")

        thread = threading.Thread(target=self._run_transcription, args=(path,), daemon=True)
        thread.start()

    def _run_transcription(self, path):
        try:
            wav_path = convert_to_wav(path)
            try:
                segments = transcribe_long_file_segments(
                    wav_path, chunk_seconds=30, on_progress=self._on_progress
                )
            finally:
                os.remove(wav_path)
            self.root.after(0, self._on_done, segments, None)
        except Exception as e:
            self.root.after(0, self._on_done, None, e)

    def _on_progress(self, current, total):
        self.root.after(0, self._update_progress_ui, current, total)

    def _update_progress_ui(self, current, total):
        pct = int((current / total) * 100)
        self.progress["value"] = pct
        self.progress_label_var.set(f"{pct}%  \u2022  chunk {current}/{total}")

    def _on_done(self, segments, error):
        self._transcribing = False
        self.transcribe_btn.config(state="normal" if self.audio_path.get() else "disabled")
        self.live_btn.config(state="normal")

        if error is not None:
            self._set_status("Transcription failed.", "error")
            self.progress["value"] = 0
            self.progress_label_var.set("")
            self._show_placeholder()
            messagebox.showerror("Transcription failed", str(error))
            return

        self._clear_placeholder_if_needed()
        for start_seconds, text in segments:
            ts = format_timestamp(start_seconds)
            self.output_box.insert(tk.END, f"[{ts}]  ", "timestamp")
            self.output_box.insert(tk.END, f"{text}\n\n")

        self.copy_btn.config(state="normal")
        self.save_btn.config(state="normal")
        self._update_wordcount()
        self._set_status("Done.", "success")
        self.progress_label_var.set("100%  \u2022  complete")

    # ---------- live listening ----------

    def toggle_live(self):
        if self._listening:
            self._stop_event.set()
            self._listening = False
            self.live_btn.config(text="\u25CF  Start Live")
            self.transcribe_btn.config(state="normal" if self.audio_path.get() else "disabled")
            self._set_status("Stopped live listening.", "neutral")
        else:
            self._clear_placeholder_if_needed()
            self._listening = True
            self._live_start_time = time.time()
            self._stop_event = threading.Event()
            self.live_btn.config(text="\u25A0  Stop Live")
            self.transcribe_btn.config(state="disabled")
            self._set_status("Listening\u2026 speak now.", "busy")

            recognizer = sr.Recognizer()
            mic = sr.Microphone()

            thread = threading.Thread(
                target=listen_live,
                args=(recognizer, mic, self._stop_event, self._append_live_text),
                daemon=True,
            )
            thread.start()

    def _append_live_text(self, text):
        elapsed = time.time() - self._live_start_time if self._live_start_time else 0
        self.root.after(0, self._insert_live_text, text, elapsed)

    def _insert_live_text(self, text, elapsed):
        ts = format_timestamp(elapsed)
        self.output_box.insert(tk.END, f"[{ts}]  ", "timestamp")
        self.output_box.insert(tk.END, f"{text}\n")
        self.output_box.see(tk.END)
        self.copy_btn.config(state="normal")
        self.save_btn.config(state="normal")
        self._update_wordcount()

    # ---------- copy / save / clear ----------

    def copy_transcript(self):
        if self._placeholder_active:
            return
        content = self.output_box.get("1.0", tk.END).strip()
        if not content:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(content)
        self._set_status("Copied transcript to clipboard.", "success")

    def save_transcript(self):
        if self._placeholder_active:
            return
        content = self.output_box.get("1.0", tk.END).strip()
        if not content:
            return
        path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text file", "*.txt")])
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content + "\n")
            self._set_status(f"Saved to {os.path.basename(path)}", "success")

    def clear_transcript(self):
        self._show_placeholder()
        self.copy_btn.config(state="disabled")
        self.save_btn.config(state="disabled")
        self.progress["value"] = 0
        self.progress_label_var.set("")

    # ---------- search ----------

    def run_search(self):
        query = self.search_var.get().strip()
        self.output_box.tag_remove("match", "1.0", tk.END)

        if not query or self._placeholder_active:
            self.match_label.config(text="")
            return

        count = 0
        start_idx = "1.0"
        while True:
            pos = self.output_box.search(query, start_idx, stopindex=tk.END, nocase=True)
            if not pos:
                break
            end_pos = f"{pos}+{len(query)}c"
            self.output_box.tag_add("match", pos, end_pos)
            start_idx = end_pos
            count += 1

        if count:
            first_match = self.output_box.tag_ranges("match")[0]
            self.output_box.see(first_match)

        self.match_label.config(text=f"{count} match{'es' if count != 1 else ''}")


if __name__ == "__main__":
    root = tk.Tk()
    TranscriptApp(root)
    root.mainloop()