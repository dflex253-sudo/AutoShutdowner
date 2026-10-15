import json
import os
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import messagebox, ttk
from datetime import datetime
from pathlib import Path

APP_NAME = "AutoShutdowner"
APP_DIR = Path(os.environ.get("APPDATA", str(Path.home()))) / APP_NAME
CONFIG_PATH = APP_DIR / "settings.json"
STARTUP_NAME = "AutoShutdowner"
WARNING_SECONDS = 60

def config_dir():
    APP_DIR.mkdir(parents=True, exist_ok=True)

def load_settings():
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"enabled": False, "shutdown_at": "23:00", "startup": True, "warn": True}

def save_settings(data):
    config_dir()
    CONFIG_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")

def set_startup(enabled):
    if os.name != "nt":
        return
    import winreg
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    exe_path = sys.executable
    if getattr(sys, "frozen", False):
        command = f'"{exe_path}"'
    else:
        command = f'"{exe_path}" "{Path(__file__).resolve()}"'
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
        if enabled:
            winreg.SetValueEx(key, STARTUP_NAME, 0, winreg.REG_SZ, command)
        else:
            try:
                winreg.DeleteValue(key, STARTUP_NAME)
            except FileNotFoundError:
                pass

def issue_shutdown():
    # Uses Windows' built-in shutdown command.
    subprocess.Popen(["shutdown", "/s", "/t", "0"], creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))

class App:
    def __init__(self, root):
        self.root = root
        self.settings = load_settings()
        self.root.title("AutoShutdowner")
        self.root.geometry("510x430")
        self.root.minsize(480, 400)
        self.root.configure(bg="#101827")
        self.running = True
        self.warned_for = None

        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TLabel", background="#101827", foreground="#eef4ff", font=("Segoe UI", 10))
        style.configure("Header.TLabel", font=("Segoe UI", 20, "bold"), foreground="#ffffff")
        style.configure("TButton", font=("Segoe UI", 10), padding=8)
        style.configure("TCheckbutton", background="#101827", foreground="#eef4ff", font=("Segoe UI", 10))
        style.configure("TEntry", padding=6)

        outer = tk.Frame(root, bg="#101827", padx=24, pady=20)
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text="AutoShutdowner", style="Header.TLabel").pack(anchor="w")
        ttk.Label(outer, text="Schedule a shutdown. Your saved schedule can resume at Windows startup.").pack(anchor="w", pady=(4, 18))

        card = tk.Frame(outer, bg="#1c293b", padx=16, pady=16)
        card.pack(fill="x")
        ttk.Label(card, text="Daily shutdown time (24-hour format)").pack(anchor="w")
        row = tk.Frame(card, bg="#1c293b")
        row.pack(fill="x", pady=(7, 12))
        self.time_var = tk.StringVar(value=self.settings.get("shutdown_at", "23:00"))
        self.time_entry = ttk.Entry(row, textvariable=self.time_var, width=12, font=("Segoe UI", 15))
        self.time_entry.pack(side="left")
        ttk.Label(row, text="Example: 23:00").pack(side="left", padx=12)

        self.enabled_var = tk.BooleanVar(value=self.settings.get("enabled", False))
        self.startup_var = tk.BooleanVar(value=self.settings.get("startup", True))
        self.warn_var = tk.BooleanVar(value=self.settings.get("warn", True))
        ttk.Checkbutton(card, text="Enable daily auto shutdown", variable=self.enabled_var).pack(anchor="w", pady=4)
        ttk.Checkbutton(card, text="Start automatically when I sign in to Windows", variable=self.startup_var).pack(anchor="w", pady=4)
        ttk.Checkbutton(card, text="Show a 60-second warning before shutdown", variable=self.warn_var).pack(anchor="w", pady=4)

        buttons = tk.Frame(outer, bg="#101827")
        buttons.pack(fill="x", pady=16)
        ttk.Button(buttons, text="Save settings", command=self.save).pack(side="left")
        ttk.Button(buttons, text="Test shutdown in 60 sec", command=self.test_shutdown).pack(side="left", padx=8)
        ttk.Button(buttons, text="Cancel pending shutdown", command=self.cancel_shutdown).pack(side="left")

        self.status_var = tk.StringVar(value="Loading schedule…")
        ttk.Label(outer, textvariable=self.status_var, wraplength=450).pack(anchor="w", pady=(4, 8))
        ttk.Label(outer, text="Note: The PC must be powered on and awake at the scheduled time. Save your work before shutdown.", wraplength=450).pack(anchor="w", pady=(6, 0))

        self.root.protocol("WM_DELETE_WINDOW", self.hide_or_close)
        self.tick()

    def save(self):
        value = self.time_var.get().strip()
        try:
            datetime.strptime(value, "%H:%M")
        except ValueError:
            messagebox.showerror("Invalid time", "Enter time as HH:MM, for example 22:30.")
            return
        self.settings = {
            "enabled": self.enabled_var.get(),
            "shutdown_at": value,
            "startup": self.startup_var.get(),
            "warn": self.warn_var.get(),
        }
        try:
            set_startup(self.settings["startup"])
        except Exception as exc:
            messagebox.showwarning("Startup setting", f"Could not update Windows startup setting:\n{exc}")
        save_settings(self.settings)
        self.warned_for = None
        self.status_var.set("Settings saved. " + ("Daily shutdown is enabled." if self.settings["enabled"] else "Daily shutdown is disabled."))
        messagebox.showinfo("Saved", "Your settings have been saved.")

    def test_shutdown(self):
        if messagebox.askyesno("Test shutdown", "This will shut down Windows in 60 seconds. Save your work first. Continue?"):
            subprocess.Popen(["shutdown", "/s", "/t", "60"], creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            self.status_var.set("Test shutdown scheduled for 60 seconds from now.")

    def cancel_shutdown(self):
        try:
            subprocess.Popen(["shutdown", "/a"], creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            self.status_var.set("Cancellation command sent. Any pending Windows shutdown should be aborted.")
        except Exception as exc:
            messagebox.showerror("Cancel failed", str(exc))

    def tick(self):
        now = datetime.now()
        schedule = self.settings.get("shutdown_at", "23:00")
        enabled = self.settings.get("enabled", False)
        target_key = now.strftime("%Y-%m-%d") + " " + schedule
        if enabled:
            try:
                target = datetime.strptime(target_key, "%Y-%m-%d %H:%M")
                delta = (target - now).total_seconds()
                if 0 <= delta <= 60 and self.warned_for != target_key:
                    self.warned_for = target_key
                    if self.settings.get("warn", True):
                        if messagebox.askyesno("Shutdown warning", "Windows will shut down now. Shut down in 60 seconds? Choose No to cancel today's shutdown."):
                            subprocess.Popen(["shutdown", "/s", "/t", "60"], creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                        else:
                            self.status_var.set("Today's shutdown was skipped.")
                    else:
                        issue_shutdown()
                elif delta < 0 and self.warned_for != target_key:
                    # If the app starts after the scheduled time, don't unexpectedly shut down immediately.
                    self.warned_for = target_key
                self.status_var.set(f"Daily shutdown: ON at {schedule} | Current time: {now.strftime('%H:%M:%S')}")
            except ValueError:
                self.status_var.set("Invalid saved time. Please save settings again.")
        else:
            self.status_var.set(f"Daily shutdown: OFF | Current time: {now.strftime('%H:%M:%S')}")
        self.root.after(1000, self.tick)

    def hide_or_close(self):
        self.running = False
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
