import math, sys, os, threading, tkinter as tk
import customtkinter as ctk

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from protocol import formula_holds, run_ociorcool
from main import create_network

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("OciorCOOL")
        self.geometry("700x500")
        self._running = False
        self._build()

    def _build(self):
        bar = ctk.CTkFrame(self, fg_color="#222", corner_radius=0)
        bar.pack(fill="x")

        ctk.CTkLabel(bar, text="n:", font=("Arial", 12)).pack(side="left", padx=(12, 2), pady=8)
        self._n_var = tk.IntVar(value=7)
        self._n_lbl = ctk.CTkLabel(bar, text="7", font=("Arial", 12, "bold"), width=24)
        self._n_lbl.pack(side="left")
        ctk.CTkSlider(bar, from_=4, to=20, number_of_steps=16, variable=self._n_var,
                      command=self._on_change, width=120).pack(side="left", padx=4)

        ctk.CTkLabel(bar, text="t:", font=("Arial", 12)).pack(side="left", padx=(12, 2))
        self._t_var = tk.IntVar(value=2)
        self._t_lbl = ctk.CTkLabel(bar, text="2", font=("Arial", 12, "bold"), width=24)
        self._t_lbl.pack(side="left")
        ctk.CTkSlider(bar, from_=1, to=6, number_of_steps=5, variable=self._t_var,
                      command=self._on_change, width=100).pack(side="left", padx=4)

        self._formula_lbl = ctk.CTkLabel(bar, text="", font=("Arial", 11))
        self._formula_lbl.pack(side="left", padx=14)

        self._run_btn = ctk.CTkButton(bar, text="Run", width=80, fg_color="#1a5276",
                                       hover_color="#154360", font=("Arial", 12, "bold"),
                                       command=self._run)
        self._run_btn.pack(side="left", padx=8)

        self._status = ctk.CTkLabel(bar, text="", font=("Arial", 11), width=160)
        self._status.pack(side="left", padx=8)

        self._canvas = NodeCanvas(self)
        self._canvas.pack(fill="both", expand=True, padx=8, pady=6)

        self._on_change()

    def _on_change(self, *_):
        n, t = self._n_var.get(), self._t_var.get()
        self._n_lbl.configure(text=str(n))
        self._t_lbl.configure(text=str(t))
        ok = formula_holds(n, t)
        self._formula_lbl.configure(
            text=f"n >= 3t+1:  {n} >= {3*t+1}  {'✓' if ok else '✗'}",
            text_color="#66bb6a" if ok else "#ef5350")

    def _run(self):
        if self._running:
            return
        self._running = True
        self._run_btn.configure(state="disabled", text="...")
        self._status.configure(text="", text_color="#aaa")
        n, t = self._n_var.get(), self._t_var.get()
        threading.Thread(target=self._do_run, args=(n, t), daemon=True).start()

    def _do_run(self, n, t):
        import io, contextlib
        nodes = create_network(n, t)
        with contextlib.redirect_stdout(io.StringIO()):
            result = run_ociorcool(nodes, t=t, attack_type="honest", verbose=True)
        self.after(0, lambda: self._finish(nodes, result))

    def _finish(self, nodes, result):
        self._running = False
        self._run_btn.configure(state="normal", text="Run")
        ok = result.get("consensus", False)
        fv = result.get("final_value", "?")
        self._status.configure(
            text=f"{'Consensus ✓' if ok else 'No consensus ✗'}  {fv}",
            text_color="#66bb6a" if ok else "#ef5350")
        self._canvas.draw(nodes)


class NodeCanvas(tk.Canvas):
    R = 20

    def __init__(self, master):
        super().__init__(master, bg="#1e1e2e", highlightthickness=0)
        self._nodes = []
        self._pos = []
        self._tip = []
        self.bind("<Configure>", lambda e: self._redraw())
        self.bind("<Motion>", self._hover)
        self.bind("<Leave>", lambda e: self._clr_tip())

    def draw(self, nodes):
        self._nodes = nodes
        self._redraw()

    def _redraw(self):
        self.delete("all")
        w = self.winfo_width() or 500
        h = self.winfo_height() or 400

        if not self._nodes:
            self.create_text(w // 2, h // 2, text="press Run", fill="#444", font=("Arial", 13))
            return

        n = len(self._nodes)
        cx, cy = w / 2, h / 2
        ring_r = min(w, h) / 2 - self.R - 30
        self._pos = [
            (cx + ring_r * math.cos(-math.pi / 2 + 2 * math.pi * i / n),
             cy + ring_r * math.sin(-math.pi / 2 + 2 * math.pi * i / n))
            for i in range(n)
        ]

        for i in range(n):
            for j in range(i + 1, n):
                x1, y1 = self._pos[i]
                x2, y2 = self._pos[j]
                self.create_line(x1, y1, x2, y2, fill="#334", width=1)

        for i, nd in enumerate(self._nodes):
            x, y = self._pos[i]
            r = self.R
            color = "#ef5350" if nd.byzantine else "#4fc3f7"
            self.create_oval(x - r, y - r, x + r, y + r, fill="#1e1e2e", outline=color, width=2)
            self.create_text(x, y, text=str(i), fill=color, font=("Arial", 9, "bold"))

    def _hover(self, e):
        self._clr_tip()
        for i, (x, y) in enumerate(self._pos):
            if (e.x - x) ** 2 + (e.y - y) ** 2 <= (self.R + 4) ** 2 and i < len(self._nodes):
                nd = self._nodes[i]
                role = "Byzantine" if nd.byzantine else "Honest"
                tip = f"Node {i} ({role})  output: {nd.output}"
                tw = len(tip) * 6 + 10
                tx, ty = e.x + 10, e.y - 18
                self._tip = [
                    self.create_rectangle(tx, ty, tx + tw, ty + 18, fill="#222", outline="#555"),
                    self.create_text(tx + 5, ty + 3, text=tip, fill="#ddd",
                                     font=("Courier", 8), anchor="nw"),
                ]
                break

    def _clr_tip(self):
        for it in self._tip:
            self.delete(it)
        self._tip = []


def main():
    App().mainloop()


if __name__ == "__main__":
    main()
