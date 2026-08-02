from __future__ import annotations

import argparse
import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, ttk
from tkinter.scrolledtext import ScrolledText
from typing import Optional

from f1.advisor import LocalAdvisor
from f1.audio import AudioCapture, AudioDevice, default_indices, list_devices
from f1.config import load_config, save_config
from f1.session import CallSession, archive_root
from f1.transcriber import OfflineTranscriber

BASE = Path(__file__).resolve().parent
SCRIPTS = BASE / "scripts"
MODEL_PATH = BASE / "models" / "vosk-model-small-it-0.22"

BG = "#070907"
PANEL = "#111512"
PANEL2 = "#171D19"
GREEN = "#39F28A"
WHITE = "#FFFFFF"
MUTED = "#A8B2AA"
YELLOW = "#FFD166"
RED = "#FF6B6B"
BLUE = "#7CC7FF"


class Settings(tk.Toplevel):
    def __init__(self, app: "Application") -> None:
        super().__init__(app.root)
        self.app = app
        self.microphones: list[AudioDevice] = []
        self.customer_devices: list[AudioDevice] = []
        self.title("Configurazione audio offline")
        self.geometry("900x540")
        self.minsize(760, 480)
        self.configure(bg=BG)
        self.transient(app.root)
        self.grab_set()

        frame = tk.Frame(self, bg=BG, padx=22, pady=20)
        frame.pack(fill="both", expand=True)
        tk.Label(frame, text="CONFIGURAZIONE AUDIO OFFLINE", bg=BG, fg=GREEN, font=("Segoe UI", 12, "bold")).pack(anchor="w")
        tk.Label(frame, text="Nessuna chiave. Nessun servizio cloud.", bg=BG, fg=WHITE, font=("Segoe UI", 22, "bold")).pack(anchor="w", pady=(4, 18))

        panel = tk.Frame(frame, bg=PANEL, padx=18, pady=18)
        panel.pack(fill="both", expand=True)
        tk.Label(panel, text="CLIENTE · Phone Link, Voicemeeter B1, CABLE, Stereo Mix o loopback altoparlanti", bg=PANEL, fg=MUTED, font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.customer_combo = ttk.Combobox(panel, state="readonly")
        self.customer_combo.pack(fill="x", pady=(5, 18), ipady=5)
        tk.Label(panel, text="JOSEPH · seleziona il microfono utilizzato durante la telefonata", bg=PANEL, fg=MUTED, font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.microphone_combo = ttk.Combobox(panel, state="readonly")
        self.microphone_combo.pack(fill="x", pady=(5, 18), ipady=5)

        self.top_var = tk.BooleanVar(value=bool(app.config.get("always_on_top", True)))
        tk.Checkbutton(panel, text="Mantieni il pannello sempre in primo piano", variable=self.top_var, bg=PANEL, fg=WHITE, selectcolor=PANEL2, activebackground=PANEL, activeforeground=WHITE).pack(anchor="w")
        self.status = tk.Label(panel, text="Caricamento dispositivi...", bg=PANEL, fg=MUTED)
        self.status.pack(anchor="w", pady=(15, 0))

        buttons = tk.Frame(frame, bg=BG)
        buttons.pack(fill="x", pady=(15, 0))
        tk.Button(buttons, text="SALVA", command=self.save, bg=GREEN, fg=BG, relief="flat", padx=24, pady=10, font=("Segoe UI", 10, "bold")).pack(side="right")
        tk.Button(buttons, text="AGGIORNA DISPOSITIVI", command=self.load_devices, bg=PANEL2, fg=WHITE, relief="flat", padx=20, pady=10, font=("Segoe UI", 10, "bold")).pack(side="right", padx=(0, 10))
        tk.Button(buttons, text="ANNULLA", command=self.destroy, bg=PANEL2, fg=WHITE, relief="flat", padx=20, pady=10, font=("Segoe UI", 10, "bold")).pack(side="right", padx=(0, 10))
        self.after(100, self.load_devices)

    def load_devices(self) -> None:
        self.status.config(text="Rilevamento dispositivi audio...", fg=MUTED)
        self.update_idletasks()
        try:
            self.microphones, self.customer_devices = list_devices()
            self.customer_combo["values"] = [item.label for item in self.customer_devices]
            self.microphone_combo["values"] = [item.label for item in self.microphones]
            default_mic, default_customer = default_indices()
            self.select_device(self.customer_combo, self.customer_devices, self.app.config.get("customer_device_index", default_customer), self.app.config.get("customer_device_name", ""))
            self.select_device(self.microphone_combo, self.microphones, self.app.config.get("microphone_device_index", default_mic), self.app.config.get("microphone_device_name", ""))
            self.status.config(text=f"{len(self.customer_devices)} sorgenti cliente e {len(self.microphones)} microfoni rilevati.", fg=GREEN)
        except Exception as exc:
            self.status.config(text=str(exc), fg=RED)

    @staticmethod
    def select_device(combo, devices, selected_index, selected_name) -> None:
        for position, device in enumerate(devices):
            if selected_index is not None and device.index == int(selected_index):
                combo.current(position)
                return
        for position, device in enumerate(devices):
            if selected_name and selected_name.lower() in device.name.lower():
                combo.current(position)
                return
        if devices:
            combo.current(0)

    def save(self) -> None:
        if self.customer_combo.current() < 0 or self.microphone_combo.current() < 0:
            messagebox.showerror("Configurazione", "Seleziona entrambi i dispositivi.", parent=self)
            return
        customer = self.customer_devices[self.customer_combo.current()]
        microphone = self.microphones[self.microphone_combo.current()]
        self.app.config.update({
            "customer_device_index": customer.index,
            "customer_device_name": customer.name,
            "microphone_device_index": microphone.index,
            "microphone_device_name": microphone.name,
            "always_on_top": bool(self.top_var.get()),
        })
        save_config(self.app.config)
        self.app.apply_config()
        self.destroy()


class Application:
    def __init__(self, demo: bool = False) -> None:
        self.demo = demo
        self.root = tk.Tk()
        self.root.title("F1 Assistente Telefonico Offline")
        self.root.geometry("1460x880")
        self.root.minsize(1180, 720)
        self.root.configure(bg=BG)
        self.config = load_config()
        self.events: queue.Queue[tuple] = queue.Queue()
        self.running = False
        self.paused = False
        self.model = None
        self.transcribers: list[OfflineTranscriber] = []
        self.captures: list[AudioCapture] = []
        self.turns: list[dict[str, str]] = []
        self.session: Optional[CallSession] = None
        self.advisor = LocalAdvisor("")
        self.current_suggestion = ""
        self.build_ui()
        self.apply_config()
        self.root.after(40, self.drain_events)
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        if demo:
            self.root.after(500, self.start_demo)
        elif self.config.get("customer_device_index") is None:
            self.root.after(350, self.open_settings)

    def button(self, parent, text, command, bg, fg):
        return tk.Button(parent, text=text, command=command, bg=bg, fg=fg, activebackground=bg, activeforeground=fg, relief="flat", cursor="hand2", padx=16, pady=10, font=("Segoe UI", 10, "bold"))

    def build_ui(self) -> None:
        header = tk.Frame(self.root, bg=BG, padx=20, pady=14)
        header.pack(fill="x")
        title = tk.Frame(header, bg=BG)
        title.pack(side="left")
        tk.Label(title, text="F1 IMMOBILIARE", bg=BG, fg=GREEN, font=("Segoe UI", 11, "bold")).pack(anchor="w")
        tk.Label(title, text="Assistente Telefonico OFFLINE", bg=BG, fg=WHITE, font=("Segoe UI", 24, "bold")).pack(anchor="w")
        self.status = tk.Label(header, text="● PRONTO", bg=BG, fg=MUTED, font=("Segoe UI", 11, "bold"))
        self.status.pack(side="right")

        bar = tk.Frame(self.root, bg=PANEL, padx=16, pady=12)
        bar.pack(fill="x", padx=20, pady=(0, 12))

        def field(label: str, width: int):
            box = tk.Frame(bar, bg=PANEL)
            box.pack(side="left", padx=(0, 12))
            tk.Label(box, text=label, bg=PANEL, fg=MUTED, font=("Segoe UI", 8, "bold")).pack(anchor="w")
            variable = tk.StringVar()
            tk.Entry(box, textvariable=variable, width=width, bg=PANEL2, fg=WHITE, insertbackground=WHITE, relief="flat", font=("Segoe UI", 11)).pack(ipady=6)
            return variable

        self.name_var = field("CONTATTO", 25)
        self.phone_var = field("TELEFONO", 18)
        self.city_var = field("COMUNE", 18)
        script_box = tk.Frame(bar, bg=PANEL)
        script_box.pack(side="left", fill="x", expand=True)
        tk.Label(script_box, text="SCRIPT", bg=PANEL, fg=MUTED, font=("Segoe UI", 8, "bold")).pack(anchor="w")
        self.script_var = tk.StringVar()
        self.script_combo = ttk.Combobox(script_box, textvariable=self.script_var, state="readonly")
        self.script_combo.pack(fill="x", ipady=5)
        self.script_combo.bind("<<ComboboxSelected>>", self.on_script_selected)

        controls = tk.Frame(self.root, bg=BG, padx=20)
        controls.pack(fill="x", pady=(0, 12))
        self.start_button = self.button(controls, "AVVIA ASCOLTO", self.toggle, GREEN, BG)
        self.start_button.pack(side="left")
        self.button(controls, "TERMINA", self.stop, RED, BG).pack(side="left", padx=8)
        self.button(controls, "APRI ARCHIVIO", self.open_archive, PANEL2, WHITE).pack(side="left")
        self.button(controls, "CONFIGURAZIONE", self.open_settings, PANEL2, WHITE).pack(side="right")

        main = tk.PanedWindow(self.root, orient="horizontal", sashwidth=7, bg=BG, bd=0)
        main.pack(fill="both", expand=True, padx=20, pady=(0, 12))
        left = tk.Frame(main, bg=PANEL, padx=14, pady=14)
        right = tk.Frame(main, bg=PANEL, padx=14, pady=14)
        main.add(left, minsize=600, stretch="always")
        main.add(right, minsize=460, stretch="always")

        tk.Label(left, text="TRASCRIZIONE LOCALE IN TEMPO REALE", bg=PANEL, fg=GREEN, font=("Segoe UI", 11, "bold")).pack(anchor="w")
        self.transcript = ScrolledText(left, bg=BG, fg=WHITE, relief="flat", wrap="word", font=("Segoe UI", 13), padx=14, pady=14, state="disabled")
        self.transcript.pack(fill="both", expand=True, pady=(10, 8))
        self.transcript.tag_configure("cliente", foreground=BLUE, font=("Segoe UI", 13, "bold"))
        self.transcript.tag_configure("joseph", foreground=GREEN, font=("Segoe UI", 13, "bold"))
        self.transcript.tag_configure("time", foreground=MUTED, font=("Consolas", 9))
        self.transcript.tag_configure("system", foreground=YELLOW, font=("Segoe UI", 10, "italic"))
        self.partial = tk.Label(left, text="In attesa dell’audio...", bg=PANEL2, fg=MUTED, anchor="w", justify="left", wraplength=760, padx=12, pady=10, font=("Segoe UI", 11, "italic"))
        self.partial.pack(fill="x")

        tk.Label(right, text="PROSSIMA FRASE DA DIRE", bg=PANEL, fg=GREEN, font=("Segoe UI", 11, "bold")).pack(anchor="w")
        suggestion_frame = tk.Frame(right, bg=BG, padx=22, pady=22)
        suggestion_frame.pack(fill="x", pady=(10, 12))
        self.suggestion = tk.Label(suggestion_frame, text="Il suggerimento comparirà durante la risposta del cliente.", bg=BG, fg=WHITE, justify="left", anchor="w", wraplength=610, font=("Segoe UI", 23, "bold"), padx=5, pady=15)
        self.suggestion.pack(fill="x")
        self.category = tk.Label(right, text="Motore decisionale locale · nessun cloud", bg=PANEL, fg=MUTED, font=("Segoe UI", 9))
        self.category.pack(anchor="w", pady=(0, 12))
        tk.Label(right, text="SCRIPT OPERATIVO", bg=PANEL, fg=GREEN, font=("Segoe UI", 11, "bold")).pack(anchor="w")
        self.script_preview = ScrolledText(right, bg=PANEL2, fg=WHITE, relief="flat", wrap="word", font=("Segoe UI", 10), padx=12, pady=10, state="disabled")
        self.script_preview.pack(fill="both", expand=True, pady=(8, 0))

        footer = tk.Frame(self.root, bg=PANEL, padx=20, pady=9)
        footer.pack(fill="x")
        self.customer_level = ttk.Progressbar(footer, maximum=100, length=180)
        self.customer_level.pack(side="left")
        tk.Label(footer, text=" CLIENTE", bg=PANEL, fg=BLUE, font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 20))
        self.mic_level = ttk.Progressbar(footer, maximum=100, length=180)
        self.mic_level.pack(side="left")
        tk.Label(footer, text=" JOSEPH", bg=PANEL, fg=GREEN, font=("Segoe UI", 9, "bold")).pack(side="left")
        self.devices = tk.Label(footer, text="", bg=PANEL, fg=MUTED, font=("Segoe UI", 9))
        self.devices.pack(side="right")

    def apply_config(self) -> None:
        scripts = sorted(path.name for path in SCRIPTS.glob("*.txt"))
        self.script_combo["values"] = scripts
        selected = self.config.get("selected_script", "")
        self.script_var.set(selected if selected in scripts else (scripts[0] if scripts else ""))
        self.load_script()
        try:
            self.root.attributes("-topmost", bool(self.config.get("always_on_top", True)))
        except tk.TclError:
            pass
        self.devices.config(text=f"Cliente: {self.config.get('customer_device_name', '')[:34]} · Mic: {self.config.get('microphone_device_name', '')[:28]}")

    def on_script_selected(self, _event=None) -> None:
        self.config["selected_script"] = self.script_var.get()
        save_config(self.config)
        self.load_script()

    def load_script(self) -> str:
        path = SCRIPTS / self.script_var.get()
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        self.script_preview.config(state="normal")
        self.script_preview.delete("1.0", "end")
        self.script_preview.insert("1.0", text)
        self.script_preview.config(state="disabled")
        self.advisor.update_script(text)
        return text

    def open_settings(self) -> None:
        if self.running:
            messagebox.showwarning("Configurazione", "Termina prima la telefonata.")
            return
        Settings(self)

    def toggle(self) -> None:
        if not self.running:
            self.start()
            return
        if self.paused:
            for capture in self.captures:
                capture.resume()
            self.paused = False
            self.start_button.config(text="PAUSA ASCOLTO", bg=YELLOW)
            self.status.config(text="● ASCOLTO ATTIVO", fg=GREEN)
        else:
            for capture in self.captures:
                capture.pause()
            self.paused = True
            self.start_button.config(text="RIPRENDI ASCOLTO", bg=GREEN)
            self.status.config(text="● IN PAUSA", fg=YELLOW)

    def start(self) -> None:
        if not MODEL_PATH.exists():
            if messagebox.askyesno("Modello mancante", "Il modello italiano non è installato. Vuoi avviare ora il download?"):
                self.download_model()
            return
        if self.config.get("customer_device_index") is None or self.config.get("microphone_device_index") is None:
            self.open_settings()
            return
        self.running = True
        self.paused = False
        self.turns = []
        self.clear()
        self.status.config(text="● CARICAMENTO MODELLO...", fg=YELLOW)
        self.start_button.config(text="PAUSA ASCOLTO", bg=YELLOW)
        self.session = CallSession(self.name_var.get().strip() or "Contatto", self.phone_var.get().strip(), self.city_var.get().strip(), self.script_var.get())
        threading.Thread(target=self.start_pipeline, daemon=True).start()

    def start_pipeline(self) -> None:
        try:
            from vosk import Model, SetLogLevel
            SetLogLevel(-1)
            if self.model is None:
                self.model = Model(str(MODEL_PATH))
            customer_transcriber = OfflineTranscriber(self.model, "CLIENTE", lambda speaker, text: self.events.put(("partial", speaker, text)), lambda speaker, text: self.events.put(("final", speaker, text)), lambda speaker, error: self.events.put(("error", speaker, error)))
            joseph_transcriber = OfflineTranscriber(self.model, "JOSEPH", lambda speaker, text: self.events.put(("partial", speaker, text)), lambda speaker, text: self.events.put(("final", speaker, text)), lambda speaker, error: self.events.put(("error", speaker, error)))
            self.transcribers = [customer_transcriber, joseph_transcriber]
            customer_transcriber.start()
            joseph_transcriber.start()
            customer_capture = AudioCapture(int(self.config["customer_device_index"]), customer_transcriber.submit, lambda level: self.events.put(("level", "CLIENTE", level)), lambda error: self.events.put(("error", "CLIENTE", error)), "CLIENTE", int(self.config.get("audio_chunk_ms", 100)))
            joseph_capture = AudioCapture(int(self.config["microphone_device_index"]), joseph_transcriber.submit, lambda level: self.events.put(("level", "JOSEPH", level)), lambda error: self.events.put(("error", "JOSEPH", error)), "JOSEPH", int(self.config.get("audio_chunk_ms", 100)))
            self.captures = [customer_capture, joseph_capture]
            customer_capture.start()
            joseph_capture.start()
            self.events.put(("ready",))
        except Exception as exc:
            self.events.put(("failed", str(exc)))

    def stop(self) -> None:
        if not self.running:
            return
        self.running = False
        self.paused = False
        for capture in self.captures:
            capture.stop()
        self.captures = []
        for transcriber in self.transcribers:
            transcriber.stop()
        self.transcribers = []
        folder = self.session.finish("", "") if self.session else None
        self.session = None
        self.start_button.config(text="AVVIA ASCOLTO", bg=GREEN)
        self.status.config(text="● TERMINATA", fg=MUTED)
        self.customer_level["value"] = 0
        self.mic_level["value"] = 0
        if folder:
            messagebox.showinfo("Salvataggio", f"Trascrizione salvata in:\n{folder}")

    def clear(self) -> None:
        self.transcript.config(state="normal")
        self.transcript.delete("1.0", "end")
        self.transcript.config(state="disabled")
        self.partial.config(text="Avvio trascrizione locale...", fg=MUTED)
        self.suggestion.config(text="In attesa della risposta del cliente.")
        self.category.config(text="Motore decisionale locale · nessun cloud", fg=MUTED)
        self.current_suggestion = ""

    def append_turn(self, speaker: str, text: str) -> None:
        self.transcript.config(state="normal")
        self.transcript.insert("end", f"[{datetime.now():%H:%M:%S}] ", "time")
        self.transcript.insert("end", f"{speaker}: ", "cliente" if speaker == "CLIENTE" else "joseph")
        self.transcript.insert("end", text + "\n\n")
        self.transcript.see("end")
        self.transcript.config(state="disabled")

    def append_system(self, text: str) -> None:
        self.transcript.config(state="normal")
        self.transcript.insert("end", f"• {text}\n", "system")
        self.transcript.see("end")
        self.transcript.config(state="disabled")

    def set_advice(self, text: str, category: str) -> None:
        if not text or text == self.current_suggestion:
            return
        self.current_suggestion = text
        self.suggestion.config(text=text)
        self.category.config(text=f"Categoria: {category} · risposta locale immediata", fg=YELLOW)
        if self.session:
            self.session.add_suggestion(text, category)

    def drain_events(self) -> None:
        try:
            while True:
                event = self.events.get_nowait()
                kind = event[0]
                if kind == "ready":
                    self.status.config(text="● ASCOLTO ATTIVO", fg=GREEN)
                    self.partial.config(text="In attesa della voce...", fg=MUTED)
                    self.append_system("Trascrizione locale attiva. Nessun cloud.")
                elif kind == "failed":
                    self.status.config(text="● ERRORE", fg=RED)
                    messagebox.showerror("Errore", event[1])
                    self.stop()
                elif kind == "partial":
                    speaker, text = event[1], event[2]
                    self.partial.config(text=f"{speaker}: {text}", fg=BLUE if speaker == "CLIENTE" else GREEN)
                    if speaker == "CLIENTE" and len(text.split()) >= 3:
                        advice = self.advisor.suggest(text, self.turns)
                        self.set_advice(advice.text, advice.category)
                elif kind == "final":
                    speaker, text = event[1], event[2]
                    if not text.strip():
                        continue
                    self.partial.config(text="In attesa del prossimo intervento...", fg=MUTED)
                    turn = {"speaker": speaker, "text": text}
                    self.turns.append(turn)
                    self.append_turn(speaker, text)
                    if self.session:
                        self.session.add_turn(speaker, text)
                    if speaker == "CLIENTE":
                        advice = self.advisor.suggest(text, self.turns)
                        self.set_advice(advice.text, advice.category)
                elif kind == "level":
                    percent = min(100, max(0, int(float(event[2]) * 360)))
                    if event[1] == "CLIENTE":
                        self.customer_level["value"] = percent
                    else:
                        self.mic_level["value"] = percent
                elif kind == "error":
                    self.append_system(f"{event[1]}: {event[2]}")
        except queue.Empty:
            pass
        self.root.after(40, self.drain_events)

    def start_demo(self) -> None:
        if self.running:
            return
        self.running = True
        self.name_var.set("Mario Rossi · DEMO")
        self.city_var.set("Susa")
        self.clear()
        self.status.config(text="● MODALITÀ DEMO", fg=YELLOW)
        self.start_button.config(text="PAUSA ASCOLTO", bg=YELLOW)
        demo_events = [
            (700, ("partial", "JOSEPH", "buongiorno sono Joseph")),
            (1500, ("final", "JOSEPH", "Buongiorno, sono Joseph Malafronte. Posso rubarle un minuto?")),
            (2500, ("partial", "CLIENTE", "guardi in questo momento non")),
            (3400, ("partial", "CLIENTE", "guardi in questo momento non sono interessato a vendere")),
            (4300, ("final", "CLIENTE", "Guardi, in questo momento non sono interessato a vendere, forse più avanti.")),
        ]
        for delay, event in demo_events:
            self.root.after(delay, lambda value=event: self.events.put(value))

    def download_model(self) -> None:
        script = BASE / "tools" / "download_model.py"
        if not script.exists():
            messagebox.showerror("Download", "Script di download non trovato.")
            return
        try:
            subprocess.Popen([sys.executable, str(script)], cwd=str(BASE), creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == "nt" else 0)
            messagebox.showinfo("Download modello", "Si è aperta una finestra di installazione. Al termine riavvia il programma.")
        except Exception as exc:
            messagebox.showerror("Download", str(exc))

    def open_archive(self) -> None:
        folder = archive_root()
        folder.mkdir(parents=True, exist_ok=True)
        try:
            if os.name == "nt":
                os.startfile(str(folder))
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(folder)])
            else:
                subprocess.Popen(["xdg-open", str(folder)])
        except Exception as exc:
            messagebox.showinfo("Archivio", f"Cartella archivio:\n{folder}\n\n{exc}")

    def close(self) -> None:
        try:
            self.stop()
        except Exception:
            pass
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--demo", action="store_true")
    args = parser.parse_args()
    Application(demo=args.demo).run()


if __name__ == "__main__":
    main()
