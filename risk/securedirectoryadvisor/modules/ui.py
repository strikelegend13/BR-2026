"""
ui.py - Main GUI for Secure File Advisor (Advanced Edition)
Designed for elderly and non-technical users: large text, clear colours, simple layout.
"""

import logging
import os
import platform
import threading
import tkinter as tk
from tkinter import filedialog, font as tkfont, messagebox

try:
    import send2trash as _send2trash
    _SEND2TRASH_AVAILABLE = True
except ImportError:
    _send2trash = None
    _SEND2TRASH_AVAILABLE = False

from modules.analyzer import analyze_file, analyze_url, format_file_size, RISK_SAFE, RISK_CAUTION, RISK_DANGER
from modules.contact import compose_message, open_mailto

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Colour palette
# ---------------------------------------------------------------------------
COLOURS = {
    "bg":               "#EAF4EF",
    "panel":            "#F8FCF9",
    "panel_warm":       "#EEF5F2",
    "accent":           "#1F5D4D",
    "accent_light":     "#D6E8E0",
    "coast":            "#2B7E87",
    "coast_light":      "#D8ECEF",
    "industrial":       "#5C6870",
    "industrial_light": "#DDE2E6",
    "safe":             "#237248",
    "safe_bg":          "#E3F3E8",
    "caution":          "#A86415",
    "caution_bg":       "#FEF3E3",
    "danger":           "#9B2C2C",
    "danger_bg":        "#FCECED",
    "text":             "#1F2B27",
    "subtext":          "#4E5E58",
    "border":           "#B5C6BC",
    "button":           "#2E7B62",
    "button_text":      "#F7FCF8",
    "button_hover":     "#225B49",
    "tab_active":       "#F8FCF9",
    "tab_inactive":     "#2A6D5A",
    "tab_text":         "#EAF7F2",
    "input_bg":         "#FFFFFF",
    "input_border":     "#9EB3A8",
    "input_focus":      "#2B7E87",
    "status_bg":        "#DCE9E2",
    "prompt_bg":        "#E9F0F2",
}

RISK_COLOURS = {
    RISK_SAFE:    (COLOURS["safe"],    COLOURS["safe_bg"],    "✅ SAFE"),
    RISK_CAUTION: (COLOURS["caution"], COLOURS["caution_bg"], "⚠️ CAUTION"),
    RISK_DANGER:  (COLOURS["danger"],  COLOURS["danger_bg"],  "🛑 DANGER"),
}


class SafetyAdvisorApp:
    def __init__(self, root: tk.Tk, config):
        self.root = root
        self.config = config
        self.last_scan_result = None
        self._mousewheel_canvas: tk.Canvas | None = None
        self._settings_scroll_canvas: tk.Canvas | None = None
        self._platform = platform.system()
        self._status_clear_id: str | None = None
        self._setup_fonts()
        self._build_window()

    # ------------------------------------------------------------------
    # Font setup
    # ------------------------------------------------------------------
    def _setup_fonts(self):
        base = 15  # Larger base for accessibility
        ui_family = self._pick_font_family("Trebuchet MS", "Segoe UI", "Calibri", "Verdana")
        title_family = self._pick_font_family("Book Antiqua", "Georgia", "Constantia", ui_family)
        self.font_title = tkfont.Font(family=title_family, size=base + 6, weight="bold")
        self.font_heading = tkfont.Font(family=ui_family, size=base + 2, weight="bold")
        self.font_body = tkfont.Font(family=ui_family, size=base)
        self.font_small = tkfont.Font(family=ui_family, size=base - 2)
        self.font_button = tkfont.Font(family=ui_family, size=base, weight="bold")
        self.font_risk = tkfont.Font(family=ui_family, size=base + 8, weight="bold")
        self.font_tab = tkfont.Font(family=ui_family, size=base - 1, weight="bold")

    def _pick_font_family(self, *choices: str) -> str:
        available = {name.lower(): name for name in tkfont.families()}
        for choice in choices:
            match = available.get(choice.lower())
            if match:
                return match
        return "TkDefaultFont"

    # ------------------------------------------------------------------
    # Window construction
    # ------------------------------------------------------------------
    def _build_window(self):
        self.root.title("Secure File Advisor")
        self.root.geometry("860x720")
        self.root.minsize(700, 600)
        self.root.configure(bg=COLOURS["bg"])
        self.root.resizable(True, True)
        self._build_menubar()

        # Header
        self._build_header()

        # Tab bar
        self._build_tabs()

        # Content area (swapped by tabs)
        self.content_frame = tk.Frame(self.root, bg=COLOURS["bg"])
        self.content_frame.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        # Build all tab pages
        self.page_file    = self._build_file_page()
        self.page_url     = self._build_url_page()
        self.page_history = self._build_history_page()
        self.page_settings = self._build_settings_page()

        # Show file tab by default
        self._show_tab("file")

        # Status bar
        self._build_statusbar()

    def _build_header(self):
        hdr = tk.Frame(self.root, bg=COLOURS["accent"], pady=14)
        hdr.pack(fill="x")
        tk.Label(
            hdr,
            text="🛡️  Secure File Advisor",
            font=self.font_title,
            fg=COLOURS["button_text"], bg=COLOURS["accent"]
        ).pack(side="left", padx=20)
        tk.Label(
            hdr,
            text="Your personal safety assistant",
            font=self.font_small,
            fg=COLOURS["coast_light"], bg=COLOURS["accent"]
        ).pack(side="left", padx=4)
        tk.Frame(self.root, bg=COLOURS["coast"], height=4).pack(fill="x")

    def _build_menubar(self):
        menubar = tk.Menu(self.root)
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(
            label="Downloads Folder Help",
            command=self._show_download_folder_help,
        )
        help_menu.add_separator()
        help_menu.add_command(
            label="About Secure File Advisor",
            command=lambda: messagebox.showinfo(
                "About Secure File Advisor",
                "Secure File Advisor helps you check files and websites before opening them.",
                parent=self.root,
            ),
        )
        menubar.add_cascade(label="Help", menu=help_menu)
        self.root.config(menu=menubar)

    def _download_folder_help_text(self) -> str:
        home = os.path.expanduser("~")
        if self._platform == "Windows":
            examples = (
                f"- {home}\\Downloads (best default)\n"
                f"- {home}\\Desktop\n"
                f"- {home}\\Documents\n"
                "- C:\\Users\\<you>\\AppData\\Local\\Temp (advanced users)"
            )
        elif self._platform == "Darwin":
            examples = (
                f"- {home}/Downloads (best default)\n"
                f"- {home}/Desktop\n"
                f"- {home}/Documents\n"
                "- /private/tmp (advanced users)"
            )
        else:
            examples = (
                f"- {home}/Downloads (best default)\n"
                f"- {home}/Desktop\n"
                f"- {home}/Documents\n"
                "- /tmp (advanced users)"
            )

        return (
            "What does 'Downloads Folder to Watch' mean?\n\n"
            "This is the folder the app watches for newly downloaded files.\n"
            "When a new file appears there, the app can prompt you to scan it for safety.\n\n"
            "High-risk folders you may want to monitor:\n"
            "- Downloads folder\n"
            "- Desktop (people often save email attachments here)\n"
            "- Documents (shared files and invoices often land here)\n"
            "- Temporary folders (advanced users)\n"
            "- Cloud sync folders if they receive files automatically (OneDrive, Dropbox, Google Drive)\n\n"
            "Recommended approach:\n"
            "Start with your Downloads folder. If you frequently save files elsewhere,\n"
            "set this to the folder where unknown files usually appear first.\n\n"
            "Common folder examples for your computer:\n"
            f"{examples}"
        )

    def _show_download_folder_help(self):
        messagebox.showinfo(
            "Downloads Folder Help",
            self._download_folder_help_text(),
            parent=self.root,
        )

    def _build_tabs(self):
        self.tab_frame = tk.Frame(self.root, bg=COLOURS["tab_inactive"], pady=0)
        self.tab_frame.pack(fill="x")

        self._tab_buttons = {}
        tabs = [
            ("file",     "📁  Check a File"),
            ("url",      "🌐  Check a Website"),
            ("history",  "📋  Past Checks"),
            ("settings", "⚙️  Settings"),
        ]
        for key, label in tabs:
            btn = tk.Button(
                self.tab_frame,
                text=label,
                font=self.font_tab,
                bd=0, relief="flat",
                padx=16, pady=8,
                cursor="hand2",
                bg=COLOURS["tab_inactive"],
                fg=COLOURS["tab_text"],
                activebackground=COLOURS["tab_active"],
                activeforeground=COLOURS["accent"],
                command=lambda k=key: self._show_tab(k)
            )
            btn.pack(side="left")
            self._tab_buttons[key] = btn
        self._active_tab = None

    def _show_tab(self, key: str):
        self._deactivate_mousewheel()
        for k, btn in self._tab_buttons.items():
            if k == key:
                btn.configure(bg=COLOURS["tab_active"], fg=COLOURS["accent"])
            else:
                btn.configure(bg=COLOURS["tab_inactive"], fg=COLOURS["tab_text"])

        pages = {
            "file":     self.page_file,
            "url":      self.page_url,
            "history":  self.page_history,
            "settings": self.page_settings,
        }
        for k, page in pages.items():
            if k == key:
                page.pack(fill="both", expand=True)
            else:
                page.pack_forget()
        self._active_tab = key

        if key == "history":
            self._refresh_history()
        elif key == "settings" and self._settings_scroll_canvas is not None:
            self._activate_mousewheel(self._settings_scroll_canvas)

    # ------------------------------------------------------------------
    # File check page
    # ------------------------------------------------------------------
    def _build_file_page(self) -> tk.Frame:
        page = tk.Frame(self.content_frame, bg=COLOURS["bg"])

        # Instruction card
        instr = self._card(page)
        tk.Label(
            instr,
            text="📁  Check a File Before Opening It",
            font=self.font_heading, fg=COLOURS["accent"], bg=COLOURS["panel"],
            anchor="w"
        ).pack(fill="x", pady=(0, 6))
        self._wrap_label(
            instr,
            text=(
                "Not sure if a file is safe to open? Click the big button below to select it.\n"
                "We'll check it and tell you in plain English whether it looks safe."
            ),
            font=self.font_body, fg=COLOURS["subtext"], bg=COLOURS["panel"],
        ).pack(fill="x")
        instr.pack(fill="x", pady=(10, 4))

        # Browse button
        btn_frame = tk.Frame(page, bg=COLOURS["bg"], pady=10)
        btn_frame.pack(fill="x")
        self._make_big_button(
            btn_frame,
            "📂   Browse for a File...",
            self._on_browse_file,
            width=36
        ).pack(pady=6)

        # OR drag hint
        tk.Label(
            btn_frame,
            text="— or wait: we'll automatically check new files as they appear in your Downloads folder —",
            font=self.font_small, fg=COLOURS["subtext"], bg=COLOURS["bg"]
        ).pack()

        # Results area
        self.file_result_frame = tk.Frame(page, bg=COLOURS["bg"])
        self.file_result_frame.pack(fill="both", expand=True, pady=4)

        return page

    def _on_browse_file(self):
        filepath = filedialog.askopenfilename(
            title="Select a file to check",
            parent=self.root
        )
        if filepath:
            self._run_file_scan(filepath)

    def _run_file_scan(self, filepath: str):
        self._set_status("Checking file, please wait…")
        self._show_scanning(self.file_result_frame)

        def worker():
            try:
                result = analyze_file(
                    filepath,
                    vt_api_key=self.config.virustotal_api_key
                )
                self.config.add_scan_history(result)
                self.last_scan_result = result
                self._safe_after(lambda r=result: self._display_result(r, self.file_result_frame))
                self._safe_after(lambda: self._set_status("Ready"))
            except Exception as exc:
                log.exception("File scan failed for %s", filepath)
                err_text = (
                    "Something went wrong while checking this file.\n\n"
                    f"Error: {exc}\n\nPlease try again."
                )
                self._safe_after(lambda msg=err_text: self._show_message(
                    self.file_result_frame,
                    msg,
                    RISK_CAUTION,
                ))
                self._safe_after(lambda: self._set_status("Check failed - see details above"))

        threading.Thread(target=worker, daemon=True).start()

    # ------------------------------------------------------------------
    # URL check page
    # ------------------------------------------------------------------
    def _build_url_page(self) -> tk.Frame:
        page = tk.Frame(self.content_frame, bg=COLOURS["bg"])

        instr = self._card(page)
        tk.Label(
            instr,
            text="🌐  Check a Website Before Visiting It",
            font=self.font_heading, fg=COLOURS["accent"], bg=COLOURS["panel"],
            anchor="w"
        ).pack(fill="x", pady=(0, 6))
        self._wrap_label(
            instr,
            text=(
                "Got a link in an email or message and not sure if it's safe?\n"
                "Copy and paste the web address below and press 'Check This Website'."
            ),
            font=self.font_body, fg=COLOURS["subtext"], bg=COLOURS["panel"],
        ).pack(fill="x")
        instr.pack(fill="x", pady=(10, 4))

        # URL entry area
        entry_card = self._card(page)
        tk.Label(
            entry_card,
            text="Paste the web address here:",
            font=self.font_body, fg=COLOURS["text"], bg=COLOURS["panel"],
            anchor="w"
        ).pack(fill="x", pady=(0, 6))

        self.url_entry_var = tk.StringVar()
        url_entry = tk.Entry(
            entry_card,
            textvariable=self.url_entry_var,
            font=self.font_body
        )
        self._style_entry(url_entry)
        url_entry.pack(fill="x", ipady=8, pady=(0, 10))
        url_entry.bind("<Return>", lambda e: self._on_check_url())

        self._make_big_button(entry_card, "🔍   Check This Website", self._on_check_url, width=30).pack(pady=4)
        entry_card.pack(fill="x", pady=(0, 4))

        # Results
        self.url_result_frame = tk.Frame(page, bg=COLOURS["bg"])
        self.url_result_frame.pack(fill="both", expand=True, pady=4)

        return page

    def _on_check_url(self):
        url = self.url_entry_var.get().strip()
        if not url:
            self._show_message(self.url_result_frame, "Please paste a web address first.", RISK_CAUTION)
            return
        # Quick sanity check before handing off to the worker thread.
        # Prepend https:// if the user omitted the scheme, mirroring what analyze_url does.
        test_url = url if url.startswith(("http://", "https://")) else "https://" + url
        if "." not in test_url.split("//", 1)[-1].split("/")[0]:
            self._show_message(
                self.url_result_frame,
                "That doesn't look like a web address. Please check it and try again.\n\n"
                "Example:  www.google.com  or  https://www.bbc.co.uk",
                RISK_CAUTION,
            )
            return
        self._set_status("Checking website, please wait…")
        self._show_scanning(self.url_result_frame)

        def worker():
            try:
                result = analyze_url(url, gsb_api_key=self.config.google_safe_browsing_key)
                self.config.add_scan_history(result)
                self.last_scan_result = result
                self._safe_after(lambda r=result: self._display_result(r, self.url_result_frame))
                self._safe_after(lambda: self._set_status("Ready"))
            except Exception as exc:
                log.exception("URL scan failed for %s", url)
                err_text = (
                    "Something went wrong while checking this website.\n\n"
                    f"Error: {exc}\n\nPlease try again."
                )
                self._safe_after(lambda msg=err_text: self._show_message(
                    self.url_result_frame,
                    msg,
                    RISK_CAUTION,
                ))
                self._safe_after(lambda: self._set_status("Check failed - see details above"))

        threading.Thread(target=worker, daemon=True).start()

    # ------------------------------------------------------------------
    # History page
    # ------------------------------------------------------------------
    def _build_history_page(self) -> tk.Frame:
        page = tk.Frame(self.content_frame, bg=COLOURS["bg"])

        hdr = self._card(page)
        tk.Label(
            hdr, text="📋  Your Past Checks",
            font=self.font_heading, fg=COLOURS["accent"], bg=COLOURS["panel"], anchor="w"
        ).pack(fill="x", pady=(0, 4))
        tk.Label(
            hdr,
            text="Here is a list of files and websites you've checked before.",
            font=self.font_body, fg=COLOURS["subtext"], bg=COLOURS["panel"], anchor="w"
        ).pack(fill="x")
        hdr.pack(fill="x", pady=(10, 4))

        # Scrollable list
        list_frame = tk.Frame(page, bg=COLOURS["bg"])
        list_frame.pack(fill="both", expand=True)

        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")

        self.history_listbox = tk.Listbox(
            list_frame,
            font=self.font_body,
            yscrollcommand=scrollbar.set,
            selectbackground=COLOURS["coast"],
            selectforeground=COLOURS["button_text"],
            bg=COLOURS["panel_warm"],
            fg=COLOURS["text"],
            bd=0, relief="flat",
            activestyle="none",
            height=18
        )
        self.history_listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.history_listbox.yview)

        self.history_listbox.bind("<<ListboxSelect>>", self._on_history_select)

        btn_row = tk.Frame(page, bg=COLOURS["bg"])
        btn_row.pack(pady=8)
        self._make_button(btn_row, "Refresh List", self._refresh_history).pack(side="left", padx=(0, 8))
        self._make_button(btn_row, "🗑️  Clear All History", self._clear_history, tone="industrial").pack(side="left")

        return page

    def _refresh_history(self):
        self.history_listbox.delete(0, "end")
        for entry in self.config.scan_history:
            scanned_at = entry.get("scanned_at", "")[:16].replace("T", " ")
            risk = entry.get("overall_risk", "?").upper()
            if entry.get("type") == "file":
                label = f"[{scanned_at}]  {risk:<8}  📁 {entry.get('filename','?')}"
            else:
                label = f"[{scanned_at}]  {risk:<8}  🌐 {entry.get('url','?')}"
            self.history_listbox.insert("end", label)

    def _on_history_select(self, _event=None):
        selection = self.history_listbox.curselection()
        if not selection:
            return
        idx = selection[0]
        history = self.config.scan_history
        if idx >= len(history):
            return
        entry = history[idx]
        self._show_history_detail(entry)

    def _clear_history(self):
        if not self.config.scan_history:
            self._set_status_temp("History is already empty.")
            return
        confirmed = messagebox.askyesno(
            "Clear History?",
            "Are you sure you want to delete all past scan results?\n\n"
            "This cannot be undone.",
            parent=self.root,
        )
        if not confirmed:
            return
        self.config.clear_scan_history()
        self._refresh_history()
        self._set_status_temp("Scan history cleared ✓")

    def _show_history_detail(self, entry: dict):
        popup = tk.Toplevel(self.root)
        popup.title("Scan Details")
        popup.geometry("680x520")
        popup.configure(bg=COLOURS["bg"])
        popup.grab_set()
        popup.lift()

        scanned_at = entry.get("scanned_at", "")[:16].replace("T", " ")
        risk = entry.get("overall_risk", "caution")
        fg_colour, bg_colour, risk_label = RISK_COLOURS.get(
            risk, (COLOURS["caution"], COLOURS["caution_bg"], "⚠️ CAUTION")
        )

        # Banner
        banner = tk.Frame(popup, bg=bg_colour, pady=12, padx=20)
        banner.pack(fill="x")
        tk.Label(
            banner, text=risk_label,
            font=self.font_risk, fg=fg_colour, bg=bg_colour
        ).pack(side="left")
        name = entry.get("filename") or entry.get("url", "")
        tk.Label(
            banner, text=f"{name}  •  {scanned_at}",
            font=self.font_small, fg=COLOURS["subtext"], bg=bg_colour,
            justify="left"
        ).pack(side="left", padx=16)

        # Scrollable findings
        findings_frame = tk.Frame(popup, bg=COLOURS["bg"])
        findings_frame.pack(fill="both", expand=True, padx=16, pady=8)
        canvas = tk.Canvas(findings_frame, bg=COLOURS["bg"], highlightthickness=0)
        scroll = tk.Scrollbar(findings_frame, command=canvas.yview)
        scroll.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        canvas.configure(yscrollcommand=scroll.set)
        inner = tk.Frame(canvas, bg=COLOURS["bg"])
        cw = canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(cw, width=e.width))
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        for finding in entry.get("findings", []):
            frisk = finding.get("risk", "caution")
            ffg, fbg, _ = RISK_COLOURS.get(frisk, (COLOURS["caution"], COLOURS["caution_bg"], ""))
            card = tk.Frame(inner, bg=fbg, highlightthickness=1,
                            highlightbackground=COLOURS["industrial_light"], padx=14, pady=10)
            card.pack(fill="x", pady=4, padx=2)
            self._wrap_label(card, text=finding["title"],
                             font=self.font_heading, fg=ffg, bg=fbg).pack(fill="x")
            self._wrap_label(card, text=finding["detail"],
                             font=self.font_body, fg=COLOURS["text"], bg=fbg).pack(fill="x", pady=(4, 0))

        self._make_button(popup, "Close", popup.destroy, tone="industrial").pack(pady=10)

    # ------------------------------------------------------------------
    # Settings page
    # ------------------------------------------------------------------
    def _build_settings_page(self) -> tk.Frame:
        page = tk.Frame(self.content_frame, bg=COLOURS["bg"])
        shell = tk.Frame(page, bg=COLOURS["bg"])
        shell.pack(fill="both", expand=True)

        scrollbar = tk.Scrollbar(shell)
        scrollbar.pack(side="right", fill="y")
        canvas = tk.Canvas(shell, bg=COLOURS["bg"], highlightthickness=0, bd=0)
        canvas.pack(side="left", fill="both", expand=True)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.configure(command=canvas.yview)
        self._settings_scroll_canvas = canvas
        self._bind_mousewheel(canvas)

        content = tk.Frame(canvas, bg=COLOURS["bg"])
        canvas_window = canvas.create_window((0, 0), window=content, anchor="nw")
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(canvas_window, width=e.width))
        content.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))

        # --- Trusted Contact ---
        contact_card = self._card(content)
        tk.Label(
            contact_card, text="👤  Your Trusted Contact",
            font=self.font_heading, fg=COLOURS["accent"], bg=COLOURS["panel"], anchor="w"
        ).pack(fill="x", pady=(0, 4))
        tk.Label(
            contact_card,
            text="When something looks suspicious, you can send them a message for help.",
            font=self.font_body, fg=COLOURS["subtext"], bg=COLOURS["panel"], anchor="w"
        ).pack(fill="x", pady=(0, 8))

        self._contact_name_var = tk.StringVar(value=self.config.trusted_contact_name)
        self._contact_email_var = tk.StringVar(value=self.config.trusted_contact_email)

        for label, var in [("Their name:", self._contact_name_var), ("Their email address:", self._contact_email_var)]:
            row = tk.Frame(contact_card, bg=COLOURS["panel"])
            row.pack(fill="x", pady=3)
            tk.Label(row, text=label, font=self.font_body, fg=COLOURS["text"], bg=COLOURS["panel"], width=22, anchor="w").pack(side="left")
            entry = tk.Entry(row, textvariable=var, font=self.font_body)
            self._style_entry(entry)
            entry.pack(side="left", fill="x", expand=True, ipady=5)

        contact_save_row = tk.Frame(contact_card, bg=COLOURS["panel"])
        contact_save_row.pack(fill="x", pady=(10, 0))
        self._make_button(contact_save_row, "💾  Save Contact", self._save_contact).pack(side="left")
        self._contact_save_label = tk.Label(
            contact_save_row, text="", font=self.font_body,
            fg=COLOURS["safe"], bg=COLOURS["panel"], anchor="w"
        )
        self._contact_save_label.pack(side="left", padx=(12, 0))
        contact_card.pack(fill="x", pady=(10, 4), padx=(0, 10))

        # --- Downloads Folder ---
        dl_card = self._card(content)
        dl_header = tk.Frame(dl_card, bg=COLOURS["panel"])
        dl_header.pack(fill="x", pady=(0, 4))
        tk.Label(
            dl_header, text="📂  Downloads Folder to Watch",
            font=self.font_heading, fg=COLOURS["accent"], bg=COLOURS["panel"], anchor="w"
        ).pack(side="left", fill="x", expand=True)
        tk.Button(
            dl_header,
            text="Info",
            font=self.font_small,
            bg=COLOURS["coast"],
            fg=COLOURS["button_text"],
            activebackground=COLOURS["accent"],
            activeforeground=COLOURS["button_text"],
            bd=0,
            relief="flat",
            padx=10,
            pady=3,
            cursor="hand2",
            command=self._show_download_folder_help,
        ).pack(side="right")
        tk.Label(
            dl_card,
            text="We'll automatically check any file that appears here.",
            font=self.font_body, fg=COLOURS["subtext"], bg=COLOURS["panel"], anchor="w"
        ).pack(fill="x", pady=(0, 8))

        self._dl_folder_var = tk.StringVar(value=self.config.downloads_folder)
        row = tk.Frame(dl_card, bg=COLOURS["panel"])
        row.pack(fill="x", pady=3)
        dl_entry = tk.Entry(row, textvariable=self._dl_folder_var, font=self.font_body)
        self._style_entry(dl_entry)
        dl_entry.pack(side="left", fill="x", expand=True, ipady=5)
        tk.Button(row, text="Browse…", font=self.font_small, bg=COLOURS["button"], fg=COLOURS["button_text"],
                  bd=0, relief="flat", padx=10, pady=4, cursor="hand2",
                  command=self._browse_dl_folder).pack(side="left", padx=(6, 0))
        dl_save_row = tk.Frame(dl_card, bg=COLOURS["panel"])
        dl_save_row.pack(fill="x", pady=(10, 0))
        self._make_button(dl_save_row, "💾  Save Folder", self._save_dl_folder).pack(side="left")
        self._dl_save_label = tk.Label(
            dl_save_row, text="", font=self.font_body,
            fg=COLOURS["safe"], bg=COLOURS["panel"], anchor="w"
        )
        self._dl_save_label.pack(side="left", padx=(12, 0))
        dl_card.pack(fill="x", pady=(0, 4), padx=(0, 10))

        # --- Optional API Keys ---
        api_card = self._card(content)
        tk.Label(
            api_card, text="🔑  Optional: Advanced Checking (API Keys)",
            font=self.font_heading, fg=COLOURS["accent"], bg=COLOURS["panel"], anchor="w"
        ).pack(fill="x", pady=(0, 4))
        self._wrap_label(
            api_card,
            text=(
                "For extra protection, you can add free API keys from VirusTotal and Google.\n"
                "These let us check files and websites against real-world security databases.\n"
                "Leave blank to skip — the basic checks still work without these."
            ),
            font=self.font_small, fg=COLOURS["subtext"], bg=COLOURS["panel"],
        ).pack(fill="x", pady=(0, 8))

        self._vt_key_var  = tk.StringVar(value=self.config.virustotal_api_key)
        self._gsb_key_var = tk.StringVar(value=self.config.google_safe_browsing_key)

        for label, var in [("VirusTotal API key:", self._vt_key_var), ("Google Safe Browsing key:", self._gsb_key_var)]:
            row = tk.Frame(api_card, bg=COLOURS["panel"])
            row.pack(fill="x", pady=3)
            tk.Label(row, text=label, font=self.font_body, fg=COLOURS["text"], bg=COLOURS["panel"], width=25, anchor="w").pack(side="left")
            self._make_secret_entry(row, var)

        save_row = tk.Frame(api_card, bg=COLOURS["panel"])
        save_row.pack(fill="x", pady=(10, 0))
        self._make_button(save_row, "💾  Save Keys", self._save_api_keys).pack(side="left")
        self._api_save_label = tk.Label(
            save_row, text="", font=self.font_body,
            fg=COLOURS["safe"], bg=COLOURS["panel"], anchor="w"
        )
        self._api_save_label.pack(side="left", padx=(12, 0))

        # Help text for obtaining keys
        tk.Label(
            api_card,
            text="Get a free VirusTotal key at virustotal.com → Profile → API key.\n"
                 "Get a free Google Safe Browsing key at console.cloud.google.com.",
            font=self.font_small, fg=COLOURS["subtext"], bg=COLOURS["panel"],
            anchor="w", justify="left",
        ).pack(fill="x", pady=(8, 0))

        api_card.pack(fill="x", pady=(0, 4), padx=(0, 10))

        return page

    def _flash_save_confirmation(self, label: tk.Label, text: str = "Saved ✓"):
        """Briefly show a green confirmation next to a save button, then fade it."""
        label.configure(text=text)
        def clear():
            try:
                label.configure(text="")
            except tk.TclError:
                pass
        self.root.after(3000, clear)

    def _save_contact(self):
        with self.config.batch_update():
            self.config.trusted_contact_name  = self._contact_name_var.get().strip()
            self.config.trusted_contact_email = self._contact_email_var.get().strip()
        self._flash_save_confirmation(self._contact_save_label, "✅  Contact saved!")
        self._set_status_temp("Trusted contact saved ✓")

    def _browse_dl_folder(self):
        folder = filedialog.askdirectory(title="Select your Downloads folder", parent=self.root)
        if folder:
            self._dl_folder_var.set(folder)

    def _save_dl_folder(self):
        self.config.downloads_folder = self._dl_folder_var.get().strip()
        self._flash_save_confirmation(self._dl_save_label, "✅  Folder saved! Restart to apply.")
        self._set_status_temp("Downloads folder saved ✓ (restart the app to apply)")

    def _save_api_keys(self):
        with self.config.batch_update():
            self.config.virustotal_api_key       = self._vt_key_var.get().strip()
            self.config.google_safe_browsing_key = self._gsb_key_var.get().strip()
        self._flash_save_confirmation(self._api_save_label, "✅  Keys saved successfully!")
        self._set_status_temp("API keys saved ✓")

    # ------------------------------------------------------------------
    # Result display
    # ------------------------------------------------------------------
    def _display_result(self, result: dict, container: tk.Frame):
        self._clear(container)

        risk = result.get("overall_risk", RISK_CAUTION)
        fg_colour, bg_colour, risk_label = RISK_COLOURS.get(risk, (COLOURS["caution"], COLOURS["caution_bg"], "⚠️ CAUTION"))

        # Big risk banner
        banner = tk.Frame(container, bg=bg_colour, pady=14, padx=20)
        banner.pack(fill="x", pady=(6, 4))
        tk.Label(
            banner, text=risk_label,
            font=self.font_risk, fg=fg_colour, bg=bg_colour
        ).pack(side="left")

        name = result.get("filename") or result.get("url", "")
        file_size = result.get("file_size")
        display_name = f"{name}  ({file_size})" if file_size else name
        name_lbl = tk.Label(
            banner, text=display_name,
            font=self.font_body, fg=COLOURS["subtext"], bg=bg_colour,
            justify="left"
        )
        name_lbl.bind("<Configure>", lambda e, l=name_lbl: l.configure(wraplength=max(100, e.width - 20)))
        name_lbl.pack(side="left", padx=20, fill="x", expand=True)

        # Findings
        findings_frame = tk.Frame(container, bg=COLOURS["bg"])
        findings_frame.pack(fill="both", expand=True, pady=4)

        canvas = tk.Canvas(findings_frame, bg=COLOURS["bg"], highlightthickness=0)
        scroll = tk.Scrollbar(findings_frame, command=canvas.yview)
        scroll.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        canvas.configure(yscrollcommand=scroll.set)
        self._bind_mousewheel(canvas)

        inner = tk.Frame(canvas, bg=COLOURS["bg"])
        canvas_window = canvas.create_window((0, 0), window=inner, anchor="nw")

        def _on_resize(e):
            canvas.itemconfig(canvas_window, width=e.width)
        canvas.bind("<Configure>", _on_resize)

        def _on_frame_configure(e):
            canvas.configure(scrollregion=canvas.bbox("all"))
        inner.bind("<Configure>", _on_frame_configure)

        for finding in result.get("findings", []):
            frisk = finding.get("risk", RISK_CAUTION)
            ffg, fbg, _ = RISK_COLOURS.get(frisk, (COLOURS["caution"], COLOURS["caution_bg"], ""))
            card = tk.Frame(
                inner,
                bg=fbg,
                bd=0,
                relief="flat",
                highlightthickness=1,
                highlightbackground=COLOURS["industrial_light"],
                highlightcolor=COLOURS["industrial_light"],
                padx=16,
                pady=12,
            )
            card.pack(fill="x", pady=4, padx=4)
            self._wrap_label(
                card, text=finding["title"],
                font=self.font_heading, fg=ffg, bg=fbg,
            ).pack(fill="x")
            self._wrap_label(
                card, text=finding["detail"],
                font=self.font_body, fg=COLOURS["text"], bg=fbg,
            ).pack(fill="x", pady=(6, 0))

        # Action buttons in an industrial prompt shell.
        action_card = self._prompt_card(container, "What would you like to do next?")
        action_frame = tk.Frame(action_card, bg=COLOURS["prompt_bg"], pady=4)
        action_frame.pack(fill="x")

        filepath = result.get("filepath")
        if risk == RISK_DANGER and filepath and os.path.isfile(filepath):
            delete_label = "🗑️  Move to Recycle Bin" if _SEND2TRASH_AVAILABLE else "🗑️  Delete File"
            self._make_button(
                action_frame,
                delete_label,
                lambda fp=filepath, c=container: self._delete_file(fp, c),
                tone="industrial",
            ).pack(side="left", padx=(0, 8))

        if self.config.trusted_contact_email:
            self._make_button(
                action_frame,
                f"📨  Ask {self.config.trusted_contact_name or 'My Trusted Contact'} for Help",
                lambda r=result: self._ask_for_help(r),
                tone="industrial",
            ).pack(side="left", padx=(0, 8))

        self._make_button(
            action_frame, "🔄  Check Another",
            lambda: self._clear(container),
            tone="coast",
        ).pack(side="left")

    def _ask_for_help(self, result: dict):
        email = self.config.trusted_contact_email
        if not email:
            self._set_status("Please add a trusted contact email in Settings first.")
            return
        subject, body = compose_message(result)
        if open_mailto(email, subject, body):
            self._set_status_temp(f"Opening your email app to contact {self.config.trusted_contact_name or email}…")
        else:
            self._set_status_temp(f"The email address '{email}' doesn't look valid. Please check it in Settings.")

    def _delete_file(self, filepath: str, container: tk.Frame):
        filename = os.path.basename(filepath)
        if _SEND2TRASH_AVAILABLE:
            action_verb = "send this file to the Recycle Bin"
            undo_note = "You can restore it from the Recycle Bin later if needed."
        else:
            action_verb = "permanently delete this file"
            undo_note = "Warning: this cannot be undone (send2trash is not installed)."
        confirmed = messagebox.askyesno(
            "Delete File?",
            f"Are you sure you want to {action_verb}?\n\n"
            f"File: {filename}\n\n{undo_note}",
            parent=self.root,
        )
        if not confirmed:
            return
        try:
            if _SEND2TRASH_AVAILABLE:
                _send2trash.send2trash(filepath)
                done_msg = f"'{filename}' has been moved to the Recycle Bin. ✓"
            else:
                os.remove(filepath)
                done_msg = f"'{filename}' has been permanently deleted. ✓"
            self._clear(container)
            self._show_message(container, done_msg, RISK_SAFE)
            self._set_status_temp(done_msg)
        except Exception as exc:
            log.warning("Could not delete %s: %s", filepath, exc)
            self._set_status_temp(f"Could not delete '{filename}' — {exc}")

    # ------------------------------------------------------------------
    # Download monitor callback (called from background thread)
    # ------------------------------------------------------------------
    def on_new_download_detected(self, filepath: str):
        """Called by the DownloadMonitor when a new file appears."""
        self._safe_after(lambda fp=filepath: self._auto_scan_popup(fp))

    def _auto_scan_popup(self, filepath: str):
        filename = os.path.basename(filepath)
        self.root.bell()
        popup = tk.Toplevel(self.root)
        popup.title("New File Detected!")
        popup.geometry("620x320")
        popup.configure(bg=COLOURS["prompt_bg"])
        popup.grab_set()
        popup.lift()
        popup.resizable(False, False)

        shell = tk.Frame(popup, bg=COLOURS["industrial"], padx=2, pady=2)
        shell.pack(fill="both", expand=True, padx=18, pady=18)

        body = tk.Frame(shell, bg=COLOURS["prompt_bg"], padx=18, pady=16)
        body.pack(fill="both", expand=True)

        tk.Label(
            body,
            text="Prompt: New download detected",
            font=self.font_small,
            fg=COLOURS["industrial"],
            bg=COLOURS["prompt_bg"],
            anchor="w",
        ).pack(fill="x")
        self._wrap_label(
            body,
            text="⚠️  A new file just appeared in your Downloads!",
            font=self.font_heading, fg=COLOURS["caution"], bg=COLOURS["prompt_bg"],
        ).pack(fill="x", pady=(6, 6))
        tk.Label(
            body, text=f"File: {filename}",
            font=self.font_body, fg=COLOURS["text"], bg=COLOURS["prompt_bg"],
            anchor="w",
        ).pack(fill="x", pady=2)
        self._wrap_label(
            body,
            text="Would you like us to check if it's safe before you open it?",
            font=self.font_body, fg=COLOURS["subtext"], bg=COLOURS["prompt_bg"],
        ).pack(fill="x", pady=(4, 10))

        btn_row = tk.Frame(body, bg=COLOURS["prompt_bg"])
        btn_row.pack(anchor="w")

        def yes():
            popup.destroy()
            self._show_tab("file")
            self._run_file_scan(filepath)

        def no():
            popup.destroy()

        self._make_button(btn_row, "✅  Yes, check it for me!", yes, tone="coast").pack(side="left", padx=(0, 10))
        self._make_button(btn_row, "No thanks", no, tone="industrial").pack(side="left")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _safe_after(self, callback) -> bool:
        """Schedule a UI callback only while Tk is alive."""
        try:
            if not self.root.winfo_exists():
                return False
            self.root.after(0, callback)
            return True
        except tk.TclError:
            return False

    def _bind_mousewheel(self, canvas: tk.Canvas):
        """Enable scrolling for one active results canvas at a time."""
        canvas.bind("<Enter>", lambda _e: self._activate_mousewheel(canvas))
        canvas.bind("<Leave>", lambda _e: self._deactivate_mousewheel(canvas))

    def _activate_mousewheel(self, canvas: tk.Canvas):
        if self._mousewheel_canvas is canvas:
            return

        self._deactivate_mousewheel()
        self._mousewheel_canvas = canvas

        if self._platform == "Darwin":
            self.root.bind_all("<MouseWheel>", self._on_mousewheel_darwin)
        elif self._platform == "Windows":
            self.root.bind_all("<MouseWheel>", self._on_mousewheel_windows)
        else:
            self.root.bind_all("<Button-4>", self._on_mousewheel_linux_up)
            self.root.bind_all("<Button-5>", self._on_mousewheel_linux_down)

    def _deactivate_mousewheel(self, canvas: tk.Canvas | None = None):
        if canvas is not None and self._mousewheel_canvas is not canvas:
            return

        self.root.unbind_all("<MouseWheel>")
        self.root.unbind_all("<Button-4>")
        self.root.unbind_all("<Button-5>")
        self._mousewheel_canvas = None

    def _scroll_active_canvas(self, units: int):
        canvas = self._mousewheel_canvas
        if canvas is None:
            return
        try:
            canvas.yview_scroll(units, "units")
        except tk.TclError:
            self._mousewheel_canvas = None

    def _on_mousewheel_darwin(self, event):
        if event.delta:
            self._scroll_active_canvas(-int(event.delta))

    def _on_mousewheel_windows(self, event):
        if event.delta == 0:
            return
        units = -int(event.delta / 120)
        if units == 0:
            units = -1 if event.delta > 0 else 1
        self._scroll_active_canvas(units)

    def _on_mousewheel_linux_up(self, _event):
        self._scroll_active_canvas(-1)

    def _on_mousewheel_linux_down(self, _event):
        self._scroll_active_canvas(1)

    def _wrap_label(self, parent, text: str, font, fg: str, bg: str,
                    anchor="w", justify="left", padding: int = 40, **kwargs) -> tk.Label:
        """Create a Label whose wraplength tracks the widget's actual width."""
        lbl = tk.Label(
            parent, text=text, font=font, fg=fg, bg=bg,
            anchor=anchor, justify=justify, **kwargs
        )
        lbl.bind(
            "<Configure>",
            lambda e, l=lbl, p=padding: l.configure(wraplength=max(100, e.width - p))
        )
        return lbl

    def _make_secret_entry(self, parent, textvariable: tk.StringVar) -> tk.Entry:
        """Create a password-style Entry with an inline show/hide toggle button."""
        row = tk.Frame(parent, bg=parent.cget("bg"))
        entry = tk.Entry(row, textvariable=textvariable, font=self.font_body, show="•")
        self._style_entry(entry)
        entry.pack(side="left", fill="x", expand=True, ipady=5)

        def _toggle(btn=None, e=entry):
            if e.cget("show") == "•":
                e.configure(show="")
                if btn:
                    btn.configure(text="🙈")
            else:
                e.configure(show="•")
                if btn:
                    btn.configure(text="👁")

        toggle_btn = tk.Button(
            row, text="👁", font=self.font_small,
            bg=COLOURS["button"], fg=COLOURS["button_text"],
            bd=0, relief="flat", padx=8, pady=4, cursor="hand2",
        )
        toggle_btn.configure(command=lambda: _toggle(toggle_btn))
        toggle_btn.pack(side="left", padx=(4, 0))
        row.pack(side="left", fill="x", expand=True)
        return entry

    def _style_entry(self, entry: tk.Entry):
        entry.configure(
            bg=COLOURS["input_bg"],
            fg=COLOURS["text"],
            insertbackground=COLOURS["text"],
            bd=0,
            relief="flat",
            highlightthickness=2,
            highlightbackground=COLOURS["input_border"],
            highlightcolor=COLOURS["input_focus"],
        )

    def _card(self, parent: tk.Frame) -> tk.Frame:
        card = tk.Frame(
            parent,
            bg=COLOURS["panel"],
            bd=0,
            relief="flat",
            highlightthickness=1,
            highlightbackground=COLOURS["border"],
            highlightcolor=COLOURS["coast"],
            padx=18,
            pady=14,
        )
        return card

    def _prompt_card(self, parent: tk.Frame, title: str) -> tk.Frame:
        shell = tk.Frame(parent, bg=COLOURS["industrial"], padx=2, pady=2)
        shell.pack(fill="x", pady=(6, 4))
        card = tk.Frame(shell, bg=COLOURS["prompt_bg"], padx=16, pady=12)
        card.pack(fill="x")
        tk.Label(
            card,
            text=title,
            font=self.font_heading,
            fg=COLOURS["industrial"],
            bg=COLOURS["prompt_bg"],
            anchor="w",
            justify="left",
        ).pack(fill="x", pady=(0, 4))
        return card

    def _resolve_button_tone(self, tone: str) -> tuple[str, str]:
        if tone == "coast":
            return COLOURS["coast"], COLOURS["accent"]
        if tone == "industrial":
            return COLOURS["industrial"], "#4B565E"
        return COLOURS["button"], COLOURS["button_hover"]

    def _make_big_button(self, parent, text: str, command, width: int = 28, tone: str = "primary") -> tk.Button:
        base_bg, hover_bg = self._resolve_button_tone(tone)
        btn = tk.Button(
            parent, text=text,
            font=self.font_button,
            bg=base_bg, fg=COLOURS["button_text"],
            activebackground=hover_bg,
            activeforeground=COLOURS["button_text"],
            bd=0, relief="flat",
            highlightthickness=1,
            highlightbackground=COLOURS["border"],
            highlightcolor=COLOURS["coast"],
            padx=20, pady=14,
            width=width,
            cursor="hand2",
            command=command
        )
        btn.bind("<Enter>", lambda _e: btn.configure(bg=hover_bg))
        btn.bind("<Leave>", lambda _e: btn.configure(bg=base_bg))
        return btn

    def _make_button(self, parent, text: str, command, tone: str = "primary") -> tk.Button:
        base_bg, hover_bg = self._resolve_button_tone(tone)
        btn = tk.Button(
            parent, text=text,
            font=self.font_button,
            bg=base_bg, fg=COLOURS["button_text"],
            activebackground=hover_bg,
            activeforeground=COLOURS["button_text"],
            bd=0, relief="flat",
            highlightthickness=1,
            highlightbackground=COLOURS["border"],
            highlightcolor=COLOURS["coast"],
            padx=14, pady=8,
            cursor="hand2",
            command=command
        )
        btn.bind("<Enter>", lambda _e: btn.configure(bg=hover_bg))
        btn.bind("<Leave>", lambda _e: btn.configure(bg=base_bg))
        return btn

    def _build_statusbar(self):
        self.status_var = tk.StringVar(value="Ready - select a file or website to check")
        bar = tk.Frame(self.root, bg=COLOURS["status_bg"])
        bar.pack(fill="x", side="bottom")
        tk.Label(
            bar,
            textvariable=self.status_var,
            font=self.font_small,
            fg=COLOURS["subtext"], bg=COLOURS["status_bg"],
            anchor="w", padx=12, pady=4
        ).pack(fill="x")

    def _set_status(self, msg: str, auto_clear_ms: int = 0):
        """Update the status bar.  If *auto_clear_ms* > 0, revert to 'Ready'
        after that many milliseconds.  Transient messages (saves, confirmations)
        default to 5 seconds via _set_status_temp."""
        if self._status_clear_id is not None:
            self.root.after_cancel(self._status_clear_id)
            self._status_clear_id = None
        self.status_var.set(msg)
        if auto_clear_ms > 0:
            self._status_clear_id = self.root.after(
                auto_clear_ms,
                lambda: self.status_var.set("Ready"),
            )

    def _set_status_temp(self, msg: str):
        """Show a transient status message that auto-clears after 5 seconds."""
        self._set_status(msg, auto_clear_ms=5000)

    def _clear(self, frame: tk.Frame):
        self._deactivate_mousewheel()
        for w in frame.winfo_children():
            w.destroy()

    def _show_scanning(self, container: tk.Frame):
        self._clear(container)
        tk.Label(
            container,
            text="🔍  Checking… please wait",
            font=self.font_heading, fg=COLOURS["coast"], bg=COLOURS["bg"]
        ).pack(pady=40)

    def _show_message(self, container: tk.Frame, msg: str, risk: str):
        self._clear(container)
        fg, bg, _ = RISK_COLOURS.get(risk, (COLOURS["caution"], COLOURS["caution_bg"], ""))
        shell = tk.Frame(container, bg=COLOURS["industrial"], padx=2, pady=2)
        shell.pack(fill="x", pady=10)
        card = tk.Frame(shell, bg=bg, padx=20, pady=20)
        card.pack(fill="x")
        self._wrap_label(card, text=msg, font=self.font_body, fg=fg, bg=bg).pack(fill="x")
