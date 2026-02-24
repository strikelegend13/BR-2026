#!/usr/bin/env python3
"""
Secure File Advisor - Advanced Edition
A friendly, proactive safety tool designed for elderly and non-technical users.
"""

import logging
import threading
import tkinter as tk
from tkinter import messagebox

from modules.ui import SafetyAdvisorApp
from modules.monitor import DownloadMonitor
from modules.config import Config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger(__name__)


def main():
    try:
        config = Config()
    except Exception as exc:
        try:
            err_root = tk.Tk()
            err_root.withdraw()
            messagebox.showerror(
                "Startup Error",
                f"Could not load settings:\n{exc}",
            )
            err_root.destroy()
        except Exception:
            print(f"Fatal: could not load settings: {exc}")
        return

    root = tk.Tk()
    root.withdraw()

    app = SafetyAdvisorApp(root, config)

    monitor = DownloadMonitor(
        watch_folder=config.downloads_folder,
        on_new_file=app.on_new_download_detected,
    )
    monitor_thread = threading.Thread(target=monitor.start, daemon=True, name="DownloadMonitor")
    monitor_thread.start()

    def on_close():
        log.info("Shutting down...")
        monitor.stop()
        monitor_thread.join(timeout=2.0)
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.deiconify()
    log.info("App started, monitoring %s", config.downloads_folder)
    root.mainloop()


if __name__ == "__main__":
    main()
