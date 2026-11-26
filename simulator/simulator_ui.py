"""Basic Tkinter UI for the PROMETHEUS-X Line Simulator.

Select a Scanner Unit, choose an image folder (defaults to simulator/sample_data),
and stream scan requests one-by-one while displaying True / False results live.
"""

from __future__ import annotations

import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from stream_simulator import (
    DEFAULT_SAMPLE_DIR,
    IMAGE_EXTS,
    check_image_async,
    check_image_sync,
    list_scanner_units,
)


class SimulatorApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("PROMETHEUS-X — Production Line Simulator")
        self.root.geometry("840x560")
        self.stop_flag = threading.Event()
        self.worker_thread: threading.Thread | None = None
        self.unit_map: dict[str, int] = {}

        self._build_ui()
        self._load_units()

    def _build_ui(self) -> None:
        top = ttk.LabelFrame(self.root, text="Stream Configuration", padding=10)
        top.pack(fill="x", padx=12, pady=8)

        ttk.Label(top, text="Server API:").grid(row=0, column=0, sticky="w")
        self.url_var = tk.StringVar(value="http://127.0.0.1:8000/api/v1")
        ttk.Entry(top, textvariable=self.url_var, width=34).grid(row=0, column=1, padx=6, pady=3, sticky="w")

        ttk.Label(top, text="Scanner Unit:").grid(row=0, column=2, sticky="w", padx=(12, 0))
        self.unit_var = tk.StringVar()
        self.unit_combo = ttk.Combobox(top, textvariable=self.unit_var, state="readonly", width=26)
        self.unit_combo.grid(row=0, column=3, padx=6, pady=3, sticky="w")
        ttk.Button(top, text="Refresh Units", command=self._load_units).grid(row=0, column=4, padx=4)

        ttk.Label(top, text="Sample Folder:").grid(row=1, column=0, sticky="w")
        self.folder_var = tk.StringVar(value=str(DEFAULT_SAMPLE_DIR))
        ttk.Entry(top, textvariable=self.folder_var, width=34).grid(row=1, column=1, padx=6, pady=3, sticky="w")
        ttk.Button(top, text="Browse…", command=self._browse_folder).grid(row=1, column=2, sticky="w", padx=(12, 0))

        ttk.Label(top, text="Mode / Delay (ms):").grid(row=1, column=3, sticky="w", padx=6)
        opts = ttk.Frame(top)
        opts.grid(row=1, column=4, sticky="w")
        self.mode_var = tk.StringVar(value="sync")
        ttk.Combobox(opts, textvariable=self.mode_var, values=["sync", "async"], state="readonly", width=6).pack(side="left")
        self.delay_var = tk.StringVar(value="200")
        ttk.Entry(opts, textvariable=self.delay_var, width=6).pack(side="left", padx=4)

        ctrl = ttk.Frame(self.root, padding=(12, 4))
        ctrl.pack(fill="x")
        self.start_btn = ttk.Button(ctrl, text="Start Stream", command=self._start_stream)
        self.start_btn.pack(side="left")
        self.stop_btn = ttk.Button(ctrl, text="Stop", command=self._stop_stream, state="disabled")
        self.stop_btn.pack(side="left", padx=6)
        ttk.Button(ctrl, text="Clear Results", command=self._clear_results).pack(side="left")

        self.summary_var = tk.StringVar(value="Ready — 0 checked | True (PASS): 0 | False (FAIL/REVIEW): 0")
        ttk.Label(ctrl, textvariable=self.summary_var, font=("Segoe UI", 9, "bold")).pack(side="right")

        table_frame = ttk.Frame(self.root, padding=(12, 6))
        table_frame.pack(fill="both", expand=True)

        cols = ("file", "passed", "decision", "score", "inspection_id", "latency")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=16)
        for col, title, w in [
            ("file", "Image File", 190),
            ("passed", "Result (True/False)", 130),
            ("decision", "Decision", 140),
            ("score", "Quality Score", 100),
            ("inspection_id", "Inspection ID", 110),
            ("latency", "Latency (ms)", 100),
        ]:
            self.tree.heading(col, text=title)
            self.tree.column(col, width=w, anchor="center" if col != "file" else "w")

        self.tree.tag_configure("pass", foreground="#16a34a")
        self.tree.tag_configure("fail", foreground="#dc2626")

        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

    def _browse_folder(self) -> None:
        chosen = filedialog.askdirectory(initialdir=self.folder_var.get())
        if chosen:
            self.folder_var.set(chosen)

    def _load_units(self) -> None:
        try:
            units = list_scanner_units(self.url_var.get().strip())
            self.unit_map = {f"{u['id']}: {u['name']} ({u['status']})": int(u["id"]) for u in units}
            labels = list(self.unit_map.keys())
            self.unit_combo["values"] = labels
            if labels and self.unit_var.get() not in self.unit_map:
                self.unit_var.set(labels[0])
        except Exception as exc:
            messagebox.showwarning("Connection", f"Could not load Scanner Units:\n{exc}")

    def _clear_results(self) -> None:
        for row in self.tree.get_children():
            self.tree.delete(row)
        self.summary_var.set("Ready — 0 checked | True (PASS): 0 | False (FAIL/REVIEW): 0")

    def _start_stream(self) -> None:
        unit_label = self.unit_var.get()
        if unit_label not in self.unit_map:
            messagebox.showerror("Scanner Unit Required", "Select a Scanner Unit before starting the stream.")
            return
        folder = Path(self.folder_var.get())
        if not folder.is_dir():
            messagebox.showerror("Invalid Folder", f"Folder not found:\n{folder}")
            return

        images = [p for p in sorted(folder.iterdir()) if p.is_file() and p.suffix.lower() in IMAGE_EXTS]
        if not images:
            messagebox.showinfo("No Images", f"No supported images found in:\n{folder}")
            return

        self._clear_results()
        self.stop_flag.clear()
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")

        unit_id = self.unit_map[unit_label]
        base_url = self.url_var.get().strip()
        mode = self.mode_var.get()
        try:
            delay_ms = max(0, int(self.delay_var.get()))
        except ValueError:
            delay_ms = 200

        def _run() -> None:
            passed_cnt = 0
            failed_cnt = 0
            for img in images:
                if self.stop_flag.is_set():
                    break
                try:
                    res = (
                        check_image_async(base_url, unit_id, img)
                        if mode == "async"
                        else check_image_sync(base_url, unit_id, img)
                    )
                    if res["passed"]:
                        passed_cnt += 1
                    else:
                        failed_cnt += 1
                    total = passed_cnt + failed_cnt
                    tag = "pass" if res["passed"] else "fail"
                    self.root.after(0, self._append_row, res, tag, total, passed_cnt, failed_cnt)
                except Exception as exc:
                    failed_cnt += 1
                    total = passed_cnt + failed_cnt
                    err_res = {
                        "file": img.name,
                        "passed": False,
                        "decision": f"ERROR: {exc}",
                        "score": "—",
                        "inspection_id": "—",
                        "latency_ms": "—",
                    }
                    self.root.after(0, self._append_row, err_res, "fail", total, passed_cnt, failed_cnt)

                if delay_ms > 0 and not self.stop_flag.is_set():
                    time.sleep(delay_ms / 1000.0)

            self.root.after(0, self._on_finished)

        self.worker_thread = threading.Thread(target=_run, daemon=True)
        self.worker_thread.start()

    def _append_row(self, res: dict, tag: str, total: int, passed_cnt: int, failed_cnt: int) -> None:
        self.tree.insert(
            "",
            "end",
            values=(
                res["file"],
                str(res["passed"]),
                res["decision"],
                res["score"],
                res["inspection_id"],
                res["latency_ms"],
            ),
            tags=(tag,),
        )
        self.summary_var.set(
            f"Checked: {total} | True (PASS): {passed_cnt} | False (FAIL/REVIEW): {failed_cnt}"
        )

    def _stop_stream(self) -> None:
        self.stop_flag.set()

    def _on_finished(self) -> None:
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")


if __name__ == "__main__":
    app_root = tk.Tk()
    SimulatorApp(app_root)
    app_root.mainloop()
