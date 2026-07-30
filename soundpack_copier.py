import json
import os
import shutil
import sys
import threading
import tkinter as tk
import ctypes
import xml.etree.ElementTree as ET
from tkinter import filedialog

import customtkinter as ctk
from PIL import Image


ctk.set_appearance_mode("dark")

# Glass-inspired palette. CustomTkinter supplies the rounded, antialiased surfaces.
BLACK = "#000000"
SURFACE = "#160a12"
SURFACE_RAISED = "#21101b"
SURFACE_HOVER = "#301525"
SURFACE_SELECTED = "#431a31"
FIELD = "#10070d"
BORDER = "#4a2037"
BORDER_SOFT = "#351726"
TEXT = "#fff8fc"
MUTED = "#a98f9d"
MUTED_DARK = "#735f6a"
THEMES = {
    "Pink": {
        "accent": "#ff3b98", "hover": "#ff68b0", "divider": "#672b49",
        "selected": "#431a31", "dark": "#67203f", "border": "#7a2a55",
        "glow": ("#46102d", "#8f1c54", "#f13b91", "#ffb0d3"),
    },
    "Red": {
        "accent": "#ff4545", "hover": "#ff7777", "divider": "#672f2f",
        "selected": "#421b1b", "dark": "#642727", "border": "#7a3030",
        "glow": ("#471414", "#8d2424", "#ef4242", "#ffb0b0"),
    },
    "Blue": {
        "accent": "#3b8cff", "hover": "#70adff", "divider": "#29466b",
        "selected": "#172d4b", "dark": "#204b78", "border": "#2e5f91",
        "glow": ("#10294a", "#1d5293", "#3487ed", "#afd4ff"),
    },
    "Green": {
        "accent": "#35c978", "hover": "#69df9d", "divider": "#285b40",
        "selected": "#173b29", "dark": "#246b45", "border": "#2d7d50",
        "glow": ("#113b26", "#1f7447", "#32bd70", "#aceac8"),
    },
    "Orange": {
        "accent": "#ff8738", "hover": "#ffad73", "divider": "#6a432a",
        "selected": "#482916", "dark": "#75421f", "border": "#8a5229",
        "glow": ("#4b2911", "#96501d", "#f48031", "#ffd0ac"),
    },
}


def _appearance_file():
    base = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
    return os.path.join(base, "BunnyManager", "appearance.json")


def _saved_theme():
    try:
        with open(_appearance_file(), "r", encoding="utf-8") as config_file:
            name = json.load(config_file).get("theme", "Pink")
            return name if name in THEMES else "Pink"
    except (OSError, ValueError, AttributeError):
        return "Pink"


CURRENT_THEME = _saved_theme()
ACCENT = THEMES[CURRENT_THEME]["accent"]
ACCENT_HOVER = THEMES[CURRENT_THEME]["hover"]
DIVIDER = THEMES[CURRENT_THEME]["divider"]
SURFACE_SELECTED = THEMES[CURRENT_THEME]["selected"]
ACCENT_DARK = THEMES[CURRENT_THEME]["dark"]
ACCENT_BORDER = THEMES[CURRENT_THEME]["border"]
SUCCESS = "#60d7a0"
WARNING = "#ffc66d"
ERROR = "#ff7083"

FONT = "Orbitron"


def resource_path(relative_path):
    base_path = getattr(sys, "_MEIPASS", os.path.abspath("."))
    return os.path.join(base_path, relative_path)


def load_bundled_fonts():
    if sys.platform != "win32":
        return
    private_font = 0x10
    for filename in ("Orbitron-Medium.ttf", "Orbitron-Bold.ttf"):
        font_path = resource_path(os.path.join("assets", "fonts", filename))
        if os.path.isfile(font_path):
            ctypes.windll.gdi32.AddFontResourceExW(font_path, private_font, 0)


load_bundled_fonts()


class BunnyManager(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Bunny Manager")
        try:
            self.iconbitmap(
                resource_path(
                    os.path.join("assets", "images", "BunnyManager.ico")
                )
            )
        except (OSError, tk.TclError):
            pass
        self.geometry("780x650")
        self.minsize(720, 600)
        self.configure(fg_color=BLACK)

        self.source_dir = tk.StringVar(value=r"E:\Soundpacks")
        self.gta_dir = tk.StringVar(value=self._default_gta_directory())
        self.pack_count = tk.StringVar(value="0 soundpacks")
        self.status = tk.StringVar(value="Ready to install")
        self.settings_xml_path = tk.StringVar(value=self._default_settings_path())
        self.preset_name = tk.StringVar()
        self.selected_preset = tk.StringVar(value="Select preset")
        self.theme_name = tk.StringVar(value=CURRENT_THEME)
        self.selected_pack = None
        self.pack_rows = {}
        self.xml_tree = None
        self.xml_fields = {}
        self.presets = self._load_presets()
        self.installing = False
        self.current_page = "INSTALLER"
        self.toast_after_id = None
        self.toast_animation_id = None
        self.background_draw_id = None
        logo_path = resource_path(
            os.path.join("assets", "images", "bunny-logo.png")
        )
        with Image.open(logo_path) as logo_file:
            logo_source = logo_file.copy()
        self.logo_image = ctk.CTkImage(
            light_image=logo_source,
            dark_image=logo_source,
            size=(120, 77),
        )

        self._build_background()
        self._build_shell()
        self._show_page("INSTALLER")
        self.load_soundpacks(show_feedback=False)

    @staticmethod
    def _default_gta_directory():
        candidates = [
            r"E:\SteamLibrary\steamapps\common\Grand Theft Auto V",
            os.path.join(
                os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"),
                "Steam",
                "steamapps",
                "common",
                "Grand Theft Auto V",
            ),
            os.path.join(
                os.environ.get("PROGRAMFILES", r"C:\Program Files"),
                "Rockstar Games",
                "Grand Theft Auto V",
            ),
        ]
        return next((path for path in candidates if os.path.isdir(path)), candidates[0])

    @staticmethod
    def _default_settings_path():
        candidates = []
        if os.environ.get("OneDrive"):
            candidates.append(
                os.path.join(
                    os.environ["OneDrive"],
                    "Documents",
                    "Rockstar Games",
                    "GTA V",
                    "settings.xml",
                )
            )
        candidates.append(
            os.path.join(
                os.path.expanduser("~"),
                "Documents",
                "Rockstar Games",
                "GTA V",
                "settings.xml",
            )
        )
        return next((path for path in candidates if os.path.isfile(path)), candidates[0])

    def _sfx_directory(self):
        return os.path.join(self.gta_dir.get().strip(), "x64", "audio", "sfx")

    def _resolve_settings_xml(self):
        self.settings_xml_path.set(self._default_settings_path())
        return self.settings_xml_path.get()

    @staticmethod
    def _preset_file():
        base = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
        return os.path.join(base, "BunnyManager", "gta_settings_presets.json")

    def _load_presets(self):
        try:
            with open(self._preset_file(), "r", encoding="utf-8") as preset_file:
                data = json.load(preset_file)
                return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}

    # --- Structure ---------------------------------------------------------
    def _build_background(self):
        self.background = tk.Canvas(
            self, bg=BLACK, highlightthickness=0, borderwidth=0
        )
        self.background.place(x=0, y=0, relwidth=1, relheight=1)
        self.background.bind("<Configure>", self._queue_background_draw)

    def _queue_background_draw(self, event):
        if self.background_draw_id:
            self.after_cancel(self.background_draw_id)
        self.background_draw_id = self.after(
            24, self._draw_background, event.width, event.height
        )

    def _draw_background(self, width=None, height=None):
        self.background_draw_id = None
        width = width or self.background.winfo_width()
        height = height or self.background.winfo_height()
        self.background.delete("all")
        self.background.create_rectangle(
            0, 0, width, height, fill=BLACK, outline=""
        )

        # Soft neon horizon; black remains the dominant background.
        left, right = -100, width + 100
        top, bottom = height * 0.72, height * 1.55
        glow = THEMES[self.theme_name.get()]["glow"]
        for width, color in (
            (26, "#080608"),
            (18, "#120c10"),
            (11, glow[0]),
            (6, glow[1]),
            (3, glow[2]),
            (1, glow[3]),
        ):
            self.background.create_arc(
                left,
                top,
                right,
                bottom,
                start=18,
                extent=144,
                style="arc",
                outline=color,
                width=width,
            )

    def _build_shell(self):
        # Shadow layers add depth without a hard outline.
        self.shadow = ctk.CTkFrame(
            self, fg_color="#090306", corner_radius=34, border_width=0
        )
        self.shadow.place(
            relx=0.5, rely=0.5, y=8, anchor="center", relwidth=0.91, relheight=0.90
        )

        self.shell = ctk.CTkFrame(
            self,
            fg_color=SURFACE,
            corner_radius=32,
            border_width=1,
            border_color=BORDER,
        )
        self.shell.place(
            relx=0.5, rely=0.5, anchor="center", relwidth=0.91, relheight=0.90
        )

        header = ctk.CTkFrame(self.shell, fg_color="transparent")
        header.pack(fill="x", padx=32, pady=(27, 18))

        brand_logo = ctk.CTkLabel(
            header,
            text="",
            image=self.logo_image,
            width=120,
            height=77,
            fg_color="transparent",
        )
        brand_logo.pack(side="left", padx=(0, 15))

        heading = ctk.CTkFrame(header, fg_color="transparent")
        heading.pack(side="left")
        ctk.CTkLabel(
            heading,
            text="BUNNY MANAGER",
            text_color=TEXT,
            font=ctk.CTkFont(FONT, 21, "bold"),
            anchor="w",
        ).pack(anchor="w")
        ctk.CTkLabel(
            heading,
            text="Manage all your FiveM settings",
            text_color=MUTED,
            font=ctk.CTkFont(FONT, 12),
            anchor="w",
        ).pack(anchor="w", pady=(1, 0))

        self.ready_pill = ctk.CTkFrame(
            header,
            height=30,
            corner_radius=15,
            fg_color="#24111c",
            border_width=1,
            border_color=BORDER,
        )
        self.ready_pill.pack(side="right")
        ctk.CTkLabel(
            self.ready_pill,
            text="●  Ready",
            text_color=SUCCESS,
            font=ctk.CTkFont(FONT, 11),
        ).pack(padx=13, pady=4)

        nav_wrap = ctk.CTkFrame(
            self.shell,
            fg_color="transparent",
            height=43,
            corner_radius=0,
        )
        nav_wrap.pack(fill="x", padx=32)
        nav_wrap.pack_propagate(False)
        nav_wrap.grid_columnconfigure((0, 1, 2, 3), weight=1)
        self.nav_buttons = {}
        pages = ("INSTALLER", "GTA SETTINGS", "SETTINGS", "INFO")
        for column, page in enumerate(pages):
            button = ctk.CTkButton(
                nav_wrap,
                text=page,
                command=lambda value=page: self._show_page(value),
                height=41,
                corner_radius=20,
                fg_color="#10080d",
                hover_color=SURFACE_HOVER,
                text_color=TEXT,
                font=ctk.CTkFont(FONT, 12, "bold"),
                border_width=1,
                border_color=BORDER_SOFT,
            )
            button.grid(
                row=0,
                column=column,
                sticky="ew",
                padx=(
                    (0, 7)
                    if column == 0
                    else ((7, 7) if column < len(pages) - 1 else (7, 0))
                ),
            )
            self.nav_buttons[page] = button

        self.page_host = ctk.CTkFrame(self.shell, fg_color="transparent")
        self.page_host.pack(fill="both", expand=True, padx=32, pady=(18, 28))

        self.installer_page = ctk.CTkFrame(
            self.page_host, fg_color="transparent"
        )
        self.settings_page = ctk.CTkFrame(
            self.page_host, fg_color="transparent"
        )
        self.gta_settings_page = ctk.CTkFrame(
            self.page_host, fg_color="transparent"
        )
        self.info_page = ctk.CTkFrame(
            self.page_host, fg_color="transparent"
        )
        self._build_installer_page()
        self._build_gta_settings_page()
        self._build_settings_page()
        self._build_info_page()
        self._build_toast()

    def _show_page(self, page):
        if not hasattr(self, "installer_page"):
            return
        self.installer_page.pack_forget()
        self.gta_settings_page.pack_forget()
        self.settings_page.pack_forget()
        self.info_page.pack_forget()
        pages = {
            "INSTALLER": self.installer_page,
            "GTA SETTINGS": self.gta_settings_page,
            "SETTINGS": self.settings_page,
            "INFO": self.info_page,
        }
        target = pages.get(page, self.installer_page)
        target.pack(fill="both", expand=True)
        self.current_page = page
        if hasattr(self, "nav_buttons"):
            for name, button in self.nav_buttons.items():
                selected = name == page
                button.configure(
                    fg_color=SURFACE_SELECTED if selected else "#10080d",
                    border_color=ACCENT_BORDER if selected else BORDER_SOFT,
                    text_color=TEXT if selected else MUTED,
                )
        if page == "GTA SETTINGS" and self.xml_tree is None:
            self.after_idle(self.load_settings_xml)

    # --- Installer ---------------------------------------------------------
    def _build_installer_page(self):
        heading = ctk.CTkFrame(self.installer_page, fg_color="transparent")
        heading.pack(fill="x", pady=(0, 12))
        ctk.CTkLabel(
            heading,
            text="CHOOSE A SOUNDPACK",
            text_color=TEXT,
            font=ctk.CTkFont(FONT, 15, "bold"),
        ).pack(side="left")
        ctk.CTkLabel(
            heading,
            textvariable=self.pack_count,
            text_color=MUTED,
            font=ctk.CTkFont(FONT, 11),
        ).pack(side="right")

        self.pack_list = ctk.CTkScrollableFrame(
            self.installer_page,
            fg_color=FIELD,
            corner_radius=20,
            border_width=1,
            border_color=BORDER_SOFT,
            scrollbar_button_color=ACCENT_DARK,
            scrollbar_button_hover_color=ACCENT,
            label_text="",
        )
        self.pack_list.pack(fill="both", expand=True)

        footer = ctk.CTkFrame(self.installer_page, fg_color="transparent")
        footer.pack(fill="x", pady=(16, 0))

        status_wrap = ctk.CTkFrame(footer, fg_color="transparent")
        status_wrap.pack(side="left", fill="x", expand=True)
        self.status_dot = ctk.CTkLabel(
            status_wrap,
            text="●",
            width=14,
            text_color=SUCCESS,
            font=ctk.CTkFont(FONT, 10),
        )
        self.status_dot.pack(side="left", padx=(1, 6))
        ctk.CTkLabel(
            status_wrap,
            textvariable=self.status,
            text_color=MUTED,
            font=ctk.CTkFont(FONT, 11),
        ).pack(side="left")

        self.install_button = ctk.CTkButton(
            footer,
            text="Install soundpack",
            command=self.install_pack,
            height=42,
            corner_radius=21,
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            text_color="#2b081a",
            font=ctk.CTkFont(FONT, 12, "bold"),
            border_width=1,
            border_color=ACCENT_HOVER,
        )
        self.install_button.pack(side="right")

    def _make_pack_row(self, name, show_divider=False):
        row = ctk.CTkButton(
            self.pack_list,
            text=f"♫     {name}",
            command=lambda value=name: self._select_pack(value),
            height=52,
            corner_radius=14,
            anchor="w",
            fg_color="transparent",
            hover_color=SURFACE_HOVER,
            text_color=TEXT,
            border_width=0,
            font=ctk.CTkFont(FONT, 12),
        )
        row.pack(fill="x", padx=5, pady=3)
        row.bind("<Double-Button-1>", lambda _event: self.install_pack())
        self.pack_rows[name] = row
        if show_divider:
            ctk.CTkFrame(
                self.pack_list,
                height=2,
                corner_radius=1,
                fg_color=DIVIDER,
                border_width=0,
            ).pack(fill="x", padx=(24, 64), pady=(1, 1))

    def _select_pack(self, pack):
        self.selected_pack = pack
        for name, row in self.pack_rows.items():
            if name == pack:
                row.configure(
                    fg_color=SURFACE_SELECTED,
                    hover_color=ACCENT_DARK,
                    border_width=1,
                    border_color=ACCENT_BORDER,
                )
            else:
                row.configure(
                    fg_color="transparent",
                    hover_color=SURFACE_HOVER,
                    border_width=0,
                )
        if not self.installing:
            self.status.set(f"{pack} selected")
            self.status_dot.configure(text_color=ACCENT)

    # --- GTA V settings.xml ------------------------------------------------
    def _build_gta_settings_page(self):
        heading = ctk.CTkFrame(self.gta_settings_page, fg_color="transparent")
        heading.pack(fill="x", pady=(0, 10))
        title_group = ctk.CTkFrame(heading, fg_color="transparent")
        title_group.pack(side="left")
        ctk.CTkLabel(
            title_group,
            text="GTA V SETTINGS",
            text_color=TEXT,
            font=ctk.CTkFont(FONT, 16, "bold"),
        ).pack(anchor="w")
        ctk.CTkLabel(
            title_group,
            text="Edit settings.xml and keep reusable presets.",
            text_color=MUTED,
            font=ctk.CTkFont(FONT, 9),
        ).pack(anchor="w", pady=(2, 0))

        path_row = ctk.CTkFrame(
            self.gta_settings_page,
            fg_color=FIELD,
            corner_radius=15,
            border_width=1,
            border_color=BORDER_SOFT,
        )
        path_row.pack(fill="x", pady=(0, 10))
        auto_group = ctk.CTkFrame(
            path_row,
            fg_color="transparent",
        )
        auto_group.pack(
            side="left", fill="x", expand=True, padx=(15, 8), pady=10
        )
        ctk.CTkLabel(
            auto_group,
            text="SETTINGS.XML",
            text_color=TEXT,
            font=ctk.CTkFont(FONT, 9, "bold"),
        ).pack(anchor="w")
        ctk.CTkLabel(
            auto_group,
            text="Detected automatically from your Game Directory",
            text_color=MUTED,
            font=ctk.CTkFont(FONT, 8),
        ).pack(anchor="w")
        self._small_action(
            path_row, "RELOAD", self.load_settings_xml, primary=True
        ).pack(side="right", padx=(8, 12), pady=10)

        preset_row = ctk.CTkFrame(
            self.gta_settings_page, fg_color="transparent"
        )
        preset_row.pack(fill="x", pady=(0, 10))
        self.preset_name_entry = ctk.CTkEntry(
            preset_row,
            textvariable=self.preset_name,
            placeholder_text="New preset name",
            height=35,
            corner_radius=11,
            fg_color=FIELD,
            border_width=1,
            border_color=BORDER_SOFT,
            text_color=TEXT,
            font=ctk.CTkFont(FONT, 9),
        )
        self.preset_name_entry.pack(side="left", fill="x", expand=True)
        self._small_action(
            preset_row, "SAVE PRESET", self.save_preset
        ).pack(side="left", padx=8)

        self.preset_menu = ctk.CTkComboBox(
            preset_row,
            variable=self.selected_preset,
            values=self._preset_names(),
            height=35,
            width=150,
            corner_radius=11,
            fg_color=FIELD,
            border_width=1,
            border_color=BORDER_SOFT,
            button_color=SURFACE_RAISED,
            button_hover_color=SURFACE_HOVER,
            dropdown_fg_color=SURFACE_RAISED,
            dropdown_hover_color=SURFACE_HOVER,
            text_color=TEXT,
            font=ctk.CTkFont(FONT, 8),
            dropdown_font=ctk.CTkFont(FONT, 8),
            state="readonly",
        )
        self.preset_menu.pack(side="left")
        self._small_action(preset_row, "APPLY", self.apply_preset).pack(
            side="left", padx=(8, 0)
        )
        self._small_action(
            preset_row, "×", self.delete_preset, danger=True, width=35
        ).pack(side="right", padx=(8, 0))

        self.xml_editor = ctk.CTkScrollableFrame(
            self.gta_settings_page,
            fg_color=FIELD,
            corner_radius=18,
            border_width=1,
            border_color=BORDER_SOFT,
            scrollbar_button_color=ACCENT_DARK,
            scrollbar_button_hover_color=ACCENT,
        )
        self.xml_editor.pack(fill="both", expand=True)
        self.xml_empty = ctk.CTkLabel(
            self.xml_editor,
            text="LOAD SETTINGS.XML TO BEGIN",
            text_color=MUTED,
            font=ctk.CTkFont(FONT, 10, "bold"),
        )
        self.xml_empty.pack(expand=True, pady=45)

        action_row = ctk.CTkFrame(
            self.gta_settings_page, fg_color="transparent"
        )
        action_row.pack(fill="x", pady=(10, 0))
        self.xml_status = ctk.CTkLabel(
            action_row,
            text="No file loaded",
            text_color=MUTED,
            font=ctk.CTkFont(FONT, 9),
        )
        self.xml_status.pack(side="left")
        self.save_xml_button = ctk.CTkButton(
            action_row,
            text="SAVE SETTINGS",
            command=self.save_settings_xml,
            height=37,
            corner_radius=18,
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            text_color="#2b081a",
            font=ctk.CTkFont(FONT, 10, "bold"),
            border_width=1,
            border_color=ACCENT_HOVER,
            state="disabled",
        )
        self.save_xml_button.pack(side="right")

    def _small_action(self, parent, text, command, primary=False, danger=False, width=72):
        return ctk.CTkButton(
            parent,
            text=text,
            command=command,
            width=width,
            height=35,
            corner_radius=17,
            fg_color=ACCENT if primary else SURFACE_RAISED,
            hover_color=ERROR if danger else (ACCENT_HOVER if primary else SURFACE_HOVER),
            border_width=1,
            border_color=ERROR if danger else BORDER,
            text_color="#2b081a" if primary else (ERROR if danger else TEXT),
            font=ctk.CTkFont(FONT, 8, "bold"),
        )

    def _preset_names(self):
        return sorted(self.presets, key=str.lower) or ["Select preset"]

    def _refresh_preset_menu(self):
        names = self._preset_names()
        self.preset_menu.configure(values=names)
        if self.selected_preset.get() not in names:
            self.selected_preset.set(names[0])

    def load_settings_xml(self):
        path = self._resolve_settings_xml()
        if not os.path.isfile(path):
            self.show_toast(
                "Settings file not found",
                "Choose a valid GTA V settings.xml file.",
                "error",
            )
            return
        try:
            tree = ET.parse(path)
        except (ET.ParseError, OSError) as error:
            self.show_toast("Could not load XML", str(error), "error", 6500)
            return

        self.xml_tree = tree
        self.settings_xml_path.set(path)
        self._populate_xml_editor()
        self.save_xml_button.configure(state="normal")
        self.xml_status.configure(
            text=f"{len(self.xml_fields)} editable values loaded",
            text_color=SUCCESS,
        )
        self.show_toast(
            "Settings loaded",
            f"Found {len(self.xml_fields)} editable values.",
        )

    def _populate_xml_editor(self):
        for child in self.xml_editor.winfo_children():
            child.destroy()
        self.xml_fields.clear()
        root = self.xml_tree.getroot()
        visible_settings = {
            "shadowquality",
            "reflectionquality",
            "texturequality",
            "particlequality",
            "waterquality",
            "grassquality",
            "postfx",
        }
        quality_ranges = {
            "texturequality": 2,
            "particlequality": 2,
            "waterquality": 2,
            "shadowquality": 3,
            "reflectionquality": 3,
            "grassquality": 3,
            "postfx": 3,
        }

        def visit(element, path):
            current_path = f"{path}/{element.tag}" if path else element.tag
            children = list(element)
            if element.tag.lower() in visible_settings and "value" in element.attrib:
                key = f"{current_path}@value"
                self._add_xml_field(
                    key,
                    element,
                    "attribute",
                    element.attrib["value"],
                    quality_ranges[element.tag.lower()],
                )
            elif (
                element.tag.lower() in visible_settings
                and not children
                and element.text
                and element.text.strip()
            ):
                key = f"{current_path}#text"
                self._add_xml_field(
                    key,
                    element,
                    "text",
                    element.text.strip(),
                    quality_ranges[element.tag.lower()],
                )
            for child in children:
                visit(child, current_path)

        visit(root, "")
        if not self.xml_fields:
            ctk.CTkLabel(
                self.xml_editor,
                text="NO EDITABLE VALUES FOUND",
                text_color=MUTED,
                font=ctk.CTkFont(FONT, 10, "bold"),
            ).pack(pady=45)

    def _add_xml_field(self, key, element, value_type, value, maximum):
        row = ctk.CTkFrame(
            self.xml_editor,
            fg_color="transparent",
            corner_radius=12,
        )
        row.pack(fill="x", padx=5, pady=2)
        label = key.split("/")[-1].replace("@value", "").replace("#text", "")
        section = " / ".join(key.split("/")[-3:-1])
        copy = ctk.CTkFrame(row, fg_color="transparent")
        copy.pack(side="left", fill="x", expand=True, padx=(11, 8), pady=7)
        ctk.CTkLabel(
            copy,
            text=label.upper(),
            text_color=TEXT,
            font=ctk.CTkFont(FONT, 9, "bold"),
            anchor="w",
        ).pack(anchor="w")
        if section:
            ctk.CTkLabel(
                copy,
                text=section,
                text_color=MUTED_DARK,
                font=ctk.CTkFont(FONT, 7),
                anchor="w",
            ).pack(anchor="w")
        try:
            initial_value = max(0, min(maximum, int(float(value))))
        except (TypeError, ValueError):
            initial_value = 0
        variable = tk.DoubleVar(value=initial_value)
        control = ctk.CTkFrame(row, fg_color="transparent")
        control.pack(side="right", padx=(8, 11), pady=7)
        value_label = ctk.CTkLabel(
            control,
            text="",
            width=74,
            text_color=ACCENT_HOVER,
            font=ctk.CTkFont(FONT, 8, "bold"),
        )
        value_label.pack(side="right", padx=(9, 0))

        levels = (
            ("LOW", "MEDIUM", "HIGH")
            if maximum == 2
            else ("LOW", "MEDIUM", "HIGH", "ULTRA")
        )

        def update_label(slider_value):
            index = max(0, min(maximum, int(round(float(slider_value)))))
            value_label.configure(text=levels[index])

        slider = ctk.CTkSlider(
            control,
            variable=variable,
            from_=0,
            to=maximum,
            number_of_steps=maximum,
            width=180,
            height=16,
            corner_radius=8,
            button_corner_radius=8,
            fg_color="#26101c",
            progress_color=ACCENT,
            button_color=ACCENT_HOVER,
            button_hover_color=ACCENT_HOVER,
            command=update_label,
        )
        slider.pack(side="left")
        update_label(initial_value)
        self.xml_fields[key] = {
            "element": element,
            "type": value_type,
            "variable": variable,
            "maximum": maximum,
            "value_label": value_label,
            "levels": levels,
        }

    def _current_xml_values(self):
        return {
            key: str(int(round(field["variable"].get())))
            for key, field in self.xml_fields.items()
        }

    def _apply_xml_values(self, values):
        applied = 0
        for key, value in values.items():
            if key in self.xml_fields:
                field = self.xml_fields[key]
                try:
                    numeric = max(
                        0, min(field["maximum"], int(round(float(value))))
                    )
                except (TypeError, ValueError):
                    continue
                field["variable"].set(numeric)
                field["value_label"].configure(text=field["levels"][numeric])
                applied += 1
        return applied

    def save_settings_xml(self):
        if self.xml_tree is None:
            self.show_toast("Nothing to save", "Load settings.xml first.", "warning")
            return
        path = self.settings_xml_path.get().strip()
        try:
            for field in self.xml_fields.values():
                value = str(int(round(field["variable"].get())))
                if field["type"] == "attribute":
                    field["element"].set("value", value)
                else:
                    field["element"].text = value
            backup = f"{path}.backup"
            shutil.copy2(path, backup)
            self.xml_tree.write(path, encoding="utf-8", xml_declaration=True)
        except OSError as error:
            self.show_toast("Could not save settings", str(error), "error", 6500)
            return
        self.xml_status.configure(text="Saved • backup created", text_color=SUCCESS)
        self.show_toast(
            "GTA settings saved",
            "settings.xml was updated and settings.xml.backup was created.",
        )

    def _write_presets(self):
        path = self._preset_file()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as preset_file:
            json.dump(self.presets, preset_file, indent=2, sort_keys=True)

    def save_preset(self):
        if not self.xml_fields:
            self.show_toast("Nothing to capture", "Load settings.xml first.", "warning")
            return
        name = self.preset_name.get().strip()
        if not name:
            self.show_toast("Name your preset", "Enter a preset name first.", "warning")
            return
        self.presets[name] = self._current_xml_values()
        try:
            self._write_presets()
        except OSError as error:
            self.show_toast("Could not save preset", str(error), "error")
            return
        self.selected_preset.set(name)
        self.preset_name.set("")
        self._refresh_preset_menu()
        self.show_toast("Preset saved", f"{name} is ready to use.")

    def apply_preset(self):
        name = self.selected_preset.get()
        if name not in self.presets:
            self.show_toast("Select a preset", "Choose a saved preset first.", "warning")
            return
        if not self.xml_fields:
            self.show_toast("Load settings.xml", "Load the XML before applying a preset.", "warning")
            return
        count = self._apply_xml_values(self.presets[name])
        self.xml_status.configure(
            text=f"{name} applied • save to commit", text_color=WARNING
        )
        self.show_toast("Preset applied", f"Updated {count} values. Save to commit.")

    def delete_preset(self):
        name = self.selected_preset.get()
        if name not in self.presets:
            self.show_toast("Select a preset", "Choose a saved preset first.", "warning")
            return
        del self.presets[name]
        try:
            self._write_presets()
        except OSError as error:
            self.show_toast("Could not delete preset", str(error), "error")
            return
        self.selected_preset.set("Select preset")
        self._refresh_preset_menu()
        self.show_toast("Preset deleted", f"{name} was removed.", "warning")

    # --- Settings ----------------------------------------------------------
    def _build_settings_page(self):
        self.settings_scroll = ctk.CTkScrollableFrame(
            self.settings_page,
            fg_color="transparent",
            corner_radius=0,
            border_width=0,
            scrollbar_button_color=ACCENT_DARK,
            scrollbar_button_hover_color=ACCENT,
        )
        self.settings_scroll.pack(fill="both", expand=True)
        settings_scroll = self.settings_scroll

        ctk.CTkLabel(
            settings_scroll,
            text="FOLDER LOCATIONS",
            text_color=TEXT,
            font=ctk.CTkFont(FONT, 17, "bold"),
        ).pack(anchor="w")
        ctk.CTkLabel(
            settings_scroll,
            text="Manage where soundpacks are loaded from and installed.",
            text_color=MUTED,
            font=ctk.CTkFont(FONT, 11),
        ).pack(anchor="w", pady=(3, 18))

        self._settings_field(
            settings_scroll,
            "SOUNDPACKS FOLDER",
            "Folder containing your available soundpacks.",
            self.source_dir,
            self.browse_source,
        )
        self._settings_field(
            settings_scroll,
            "GTA GAME FOLDER",
            "SFX files are resolved automatically from this installation.",
            self.gta_dir,
            self.browse_gta,
        )

        ctk.CTkButton(
            settings_scroll,
            text="Refresh library",
            command=self.load_soundpacks,
            height=38,
            corner_radius=19,
            fg_color=SURFACE_RAISED,
            hover_color=SURFACE_HOVER,
            border_width=1,
            border_color=BORDER,
            text_color=TEXT,
            font=ctk.CTkFont(FONT, 11, "bold"),
        ).pack(anchor="e", pady=(2, 12))

    def _settings_field(self, parent, title, helper, variable, command):
        card = ctk.CTkFrame(
            parent,
            fg_color=FIELD,
            corner_radius=18,
            border_width=1,
            border_color=BORDER_SOFT,
        )
        card.pack(fill="x", pady=(0, 13))

        copy = ctk.CTkFrame(card, fg_color="transparent")
        copy.pack(fill="x", padx=18, pady=(14, 9))
        ctk.CTkLabel(
            copy,
            text=title,
            text_color=TEXT,
            font=ctk.CTkFont(FONT, 12, "bold"),
        ).pack(anchor="w")
        ctk.CTkLabel(
            copy,
            text=helper,
            text_color=MUTED,
            font=ctk.CTkFont(FONT, 10),
        ).pack(anchor="w", pady=(1, 0))

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=18, pady=(0, 15))
        entry = ctk.CTkEntry(
            row,
            textvariable=variable,
            height=39,
            corner_radius=12,
            fg_color="#0c060a",
            border_width=1,
            border_color=BORDER_SOFT,
            text_color=TEXT,
            placeholder_text_color=MUTED_DARK,
            font=ctk.CTkFont(FONT, 10),
        )
        entry.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(
            row,
            text="Browse",
            command=command,
            width=82,
            height=39,
            corner_radius=19,
            fg_color=SURFACE_RAISED,
            hover_color=SURFACE_HOVER,
            border_width=1,
            border_color=BORDER,
            text_color=TEXT,
            font=ctk.CTkFont(FONT, 10, "bold"),
        ).pack(side="right", padx=(10, 0))

    def change_theme(self, name):
        if name not in THEMES:
            return
        if self.installing:
            self.theme_name.set(CURRENT_THEME)
            self.show_toast(
                "Installation in progress",
                "Wait for the installation to finish before changing themes.",
                "warning",
            )
            return
        try:
            config_path = _appearance_file()
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            with open(config_path, "w", encoding="utf-8") as config_file:
                json.dump({"theme": name}, config_file, indent=2)
        except OSError as error:
            self.show_toast("Could not save theme", str(error), "error")
            return
        self.theme_name.set(name)
        self.after_idle(self._apply_theme, name)

    def _apply_theme(self, name):
        global CURRENT_THEME, ACCENT, ACCENT_HOVER, DIVIDER
        global SURFACE_SELECTED, ACCENT_DARK, ACCENT_BORDER

        old_palette = THEMES[CURRENT_THEME]
        palette = THEMES[name]
        color_map = {
            old_palette["accent"].lower(): palette["accent"],
            old_palette["hover"].lower(): palette["hover"],
            old_palette["divider"].lower(): palette["divider"],
            old_palette["selected"].lower(): palette["selected"],
            old_palette["dark"].lower(): palette["dark"],
            old_palette["border"].lower(): palette["border"],
        }

        CURRENT_THEME = name
        ACCENT = palette["accent"]
        ACCENT_HOVER = palette["hover"]
        DIVIDER = palette["divider"]
        SURFACE_SELECTED = palette["selected"]
        ACCENT_DARK = palette["dark"]
        ACCENT_BORDER = palette["border"]

        color_options = (
            "fg_color",
            "hover_color",
            "border_color",
            "button_color",
            "button_hover_color",
            "progress_color",
            "scrollbar_button_color",
            "scrollbar_button_hover_color",
            "text_color",
        )

        def recolor(widget):
            updates = {}
            for option in color_options:
                try:
                    value = widget.cget(option)
                except (AttributeError, TypeError, ValueError, tk.TclError):
                    continue
                if isinstance(value, str) and value.lower() in color_map:
                    updates[option] = color_map[value.lower()]
            if updates:
                try:
                    widget.configure(**updates)
                except (AttributeError, TypeError, ValueError, tk.TclError):
                    pass
            for child in widget.winfo_children():
                recolor(child)

        recolor(self)
        self._draw_background()
        self.show_toast("Theme updated", f"{name} theme is now active.")

    # --- Information -------------------------------------------------------
    def _build_info_page(self):
        heading = ctk.CTkFrame(self.info_page, fg_color="transparent")
        heading.pack(fill="x", pady=(0, 12))
        ctk.CTkLabel(
            heading,
            text="ABOUT BUNNY MANAGER",
            text_color=TEXT,
            font=ctk.CTkFont(FONT, 16, "bold"),
        ).pack(anchor="w")
        ctk.CTkLabel(
            heading,
            text="Everything you need to manage FiveM audio and GTA V graphics.",
            text_color=MUTED,
            font=ctk.CTkFont(FONT, 9),
        ).pack(anchor="w", pady=(2, 0))

        info_scroll = ctk.CTkScrollableFrame(
            self.info_page,
            fg_color=FIELD,
            corner_radius=18,
            border_width=1,
            border_color=BORDER_SOFT,
            scrollbar_button_color=ACCENT_DARK,
            scrollbar_button_hover_color=ACCENT,
        )
        info_scroll.pack(fill="both", expand=True)

        self._info_section(
            info_scroll,
            "01  INSTALL SOUNDPACKS",
            "Choose a soundpack on the Installer page, then select Install "
            "soundpack. Bunny Manager copies its files into GTA V's SFX "
            "folder automatically.",
        )
        self._info_section(
            info_scroll,
            "02  CHANGE GTA SETTINGS",
            "Open GTA Settings to adjust seven common graphics options with "
            "simple stepped sliders. Select Save Settings to write the values "
            "to settings.xml.",
        )
        self._info_section(
            info_scroll,
            "03  CREATE PRESETS",
            "Enter a preset name to capture the current slider values. Apply "
            "a saved preset, review its values, then save to commit the changes.",
        )
        self._info_section(
            info_scroll,
            "04  FILE SAFETY",
            "Select your GTA game folder once in Settings. The SFX destination "
            "and Documents-based settings.xml are resolved automatically. A "
            "settings.xml.backup file is created before every XML save.",
        )
        credit = ctk.CTkFrame(
            info_scroll,
            fg_color=SURFACE_SELECTED,
            corner_radius=16,
            border_width=1,
            border_color=ACCENT_BORDER,
        )
        credit.pack(fill="x", padx=7, pady=(8, 12))
        credit_copy = ctk.CTkFrame(credit, fg_color="transparent")
        credit_copy.pack(side="left", fill="x", expand=True, padx=17, pady=15)
        ctk.CTkLabel(
            credit_copy,
            text="CREATED BY NEX",
            text_color=TEXT,
            font=ctk.CTkFont(FONT, 12, "bold"),
        ).pack(anchor="w")
        ctk.CTkLabel(
            credit_copy,
            text="DISCORD  •  nexoffline",
            text_color=ACCENT_HOVER,
            font=ctk.CTkFont(FONT, 9, "bold"),
        ).pack(anchor="w", pady=(3, 0))
        ctk.CTkButton(
            credit,
            text="COPY DISCORD",
            command=self.copy_discord,
            width=112,
            height=35,
            corner_radius=17,
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            border_width=1,
            border_color=ACCENT_HOVER,
            text_color="#210914",
            font=ctk.CTkFont(FONT, 8, "bold"),
        ).pack(side="right", padx=15)

    def _info_section(self, parent, title, description):
        card = ctk.CTkFrame(
            parent,
            fg_color="transparent",
            corner_radius=14,
            border_width=0,
        )
        card.pack(fill="x", padx=7, pady=3)
        ctk.CTkLabel(
            card,
            text=title,
            text_color=TEXT,
            font=ctk.CTkFont(FONT, 10, "bold"),
            anchor="w",
        ).pack(fill="x", padx=14, pady=(11, 3))
        ctk.CTkLabel(
            card,
            text=description,
            text_color=MUTED,
            font=ctk.CTkFont(FONT, 9),
            justify="left",
            anchor="w",
            wraplength=500,
        ).pack(fill="x", padx=14, pady=(0, 11))
        ctk.CTkFrame(
            parent,
            height=1,
            fg_color=DIVIDER,
            corner_radius=0,
        ).pack(fill="x", padx=(24, 64), pady=1)

    def copy_discord(self):
        self.clipboard_clear()
        self.clipboard_append("nexoffline")
        self.update_idletasks()
        self.show_toast(
            "Discord copied",
            "nexoffline was copied to your clipboard.",
        )

    # --- Toasts ------------------------------------------------------------
    def _build_toast(self):
        self.toast = ctk.CTkFrame(
            self,
            fg_color="#24101c",
            corner_radius=18,
            border_width=1,
            border_color=BORDER,
            height=70,
        )
        self.toast.grid_columnconfigure(1, weight=1)
        self.toast_icon = ctk.CTkLabel(
            self.toast,
            text="✓",
            width=38,
            text_color=SUCCESS,
            font=ctk.CTkFont(FONT, 18, "bold"),
        )
        self.toast_icon.grid(row=0, column=0, rowspan=2, padx=(15, 7), pady=12)
        self.toast_title = ctk.CTkLabel(
            self.toast,
            text="Done",
            text_color=TEXT,
            anchor="w",
            font=ctk.CTkFont(FONT, 11, "bold"),
        )
        self.toast_title.grid(row=0, column=1, sticky="sw", pady=(11, 0))
        self.toast_message = ctk.CTkLabel(
            self.toast,
            text="",
            text_color=MUTED,
            anchor="w",
            font=ctk.CTkFont(FONT, 10),
        )
        self.toast_message.grid(row=1, column=1, sticky="nw", pady=(0, 11))
        ctk.CTkButton(
            self.toast,
            text="×",
            command=self._hide_toast,
            width=32,
            height=32,
            corner_radius=16,
            fg_color="transparent",
            hover_color=SURFACE_HOVER,
            text_color=MUTED,
            font=ctk.CTkFont(FONT, 16),
        ).grid(row=0, column=2, rowspan=2, padx=12)

    def show_toast(self, title, message, kind="success", duration=4200):
        styles = {
            "success": (SUCCESS, "✓"),
            "warning": (WARNING, "i"),
            "error": (ERROR, "!"),
        }
        color, icon = styles.get(kind, styles["success"])
        self.toast.configure(border_color=color)
        self.toast_icon.configure(text=icon, text_color=color)
        self.toast_title.configure(text=title.upper())
        self.toast_message.configure(text=message)

        if self.toast_after_id:
            self.after_cancel(self.toast_after_id)
        if self.toast_animation_id:
            self.after_cancel(self.toast_animation_id)

        self.toast.place(
            relx=0.5, rely=1.0, y=75, anchor="s", relwidth=0.72
        )
        self.toast.lift()
        self._animate_toast(75)
        self.toast_after_id = self.after(duration, self._hide_toast)

    def _animate_toast(self, y):
        next_y = max(-22, y - max(5, int((y + 22) * 0.24)))
        self.toast.place_configure(y=next_y)
        if next_y > -22:
            self.toast_animation_id = self.after(
                15, self._animate_toast, next_y
            )
        else:
            self.toast_animation_id = None

    def _hide_toast(self):
        self.toast.place_forget()
        if self.toast_after_id:
            self.after_cancel(self.toast_after_id)
            self.toast_after_id = None
        if self.toast_animation_id:
            self.after_cancel(self.toast_animation_id)
            self.toast_animation_id = None

    # --- Application logic -------------------------------------------------
    def load_soundpacks(self, show_feedback=True):
        for child in self.pack_list.winfo_children():
            child.destroy()
        self.pack_rows.clear()
        self.selected_pack = None

        folder = os.path.expandvars(os.path.expanduser(self.source_dir.get().strip()))
        if not os.path.isdir(folder):
            self.pack_count.set("0 soundpacks")
            self.status.set("Soundpacks folder not found")
            self.status_dot.configure(text_color=ERROR)
            ctk.CTkLabel(
                self.pack_list,
                text="No folder found\nChoose a valid location in Settings.",
                text_color=MUTED,
                font=ctk.CTkFont(FONT, 11),
            ).pack(expand=True, pady=55)
            if show_feedback:
                self.show_toast(
                    "Folder not found",
                    "Choose a valid soundpacks folder in Settings.",
                    "error",
                )
            return

        packs = [
            item
            for item in sorted(os.listdir(folder), key=str.lower)
            if os.path.isdir(os.path.join(folder, item))
        ]
        for index, pack in enumerate(packs):
            self._make_pack_row(pack, show_divider=index < len(packs) - 1)

        noun = "soundpack" if len(packs) == 1 else "soundpacks"
        self.pack_count.set(f"{len(packs)} {noun}")
        self.status.set("Ready to install" if packs else "No soundpacks found")
        self.status_dot.configure(text_color=SUCCESS if packs else WARNING)
        if not packs:
            ctk.CTkLabel(
                self.pack_list,
                text="This folder is empty.",
                text_color=MUTED,
                font=ctk.CTkFont(FONT, 11),
            ).pack(expand=True, pady=55)
        if show_feedback:
            self.show_toast("Library refreshed", f"Found {len(packs)} {noun}.")

    def install_pack(self):
        if self.installing:
            return
        if not self.selected_pack:
            self.show_toast(
                "Select a soundpack",
                "Choose a soundpack from the list before installing.",
                "warning",
            )
            return

        pack = self.selected_pack
        source = os.path.join(self.source_dir.get().strip(), pack)
        destination = self._sfx_directory()
        if not os.path.isdir(source):
            self.show_toast("Source not found", "Refresh the library and try again.", "error")
            return
        if not os.path.isdir(destination):
            self.show_toast(
                "Destination not found",
                "Choose a valid GTA game folder in Settings.",
                "error",
            )
            return

        self.installing = True
        self.install_button.configure(
            state="disabled", text="Installing…", fg_color=SURFACE_HOVER
        )
        self.status.set(f"Installing {pack}…")
        self.status_dot.configure(text_color=WARNING)
        threading.Thread(
            target=self._copy_pack,
            args=(pack, source, destination),
            daemon=True,
        ).start()

    def _copy_pack(self, pack, source, destination):
        try:
            for item in os.listdir(source):
                source_item = os.path.join(source, item)
                destination_item = os.path.join(destination, item)
                if os.path.isdir(source_item):
                    shutil.copytree(source_item, destination_item, dirs_exist_ok=True)
                else:
                    shutil.copy2(source_item, destination_item)
            self.after(0, self._install_finished, pack, None)
        except Exception as error:
            self.after(0, self._install_finished, pack, str(error))

    def _install_finished(self, pack, error):
        self.installing = False
        self.install_button.configure(
            state="normal", text="Install soundpack", fg_color=ACCENT
        )
        if error:
            self.status.set("Installation failed")
            self.status_dot.configure(text_color=ERROR)
            self.show_toast("Installation failed", error, "error", 6500)
        else:
            self.status.set(f"{pack} installed successfully")
            self.status_dot.configure(text_color=SUCCESS)
            self.show_toast(
                "Soundpack installed", f"{pack} is ready to use.", "success"
            )

    def browse_source(self):
        current = self.source_dir.get()
        folder = filedialog.askdirectory(
            parent=self,
            title="Choose soundpacks folder",
            initialdir=current if os.path.isdir(current) else None,
        )
        if folder:
            self.source_dir.set(folder)
            self.load_soundpacks()

    def browse_gta(self):
        current = self.gta_dir.get()
        folder = filedialog.askdirectory(
            parent=self,
            title="Choose GTA V game folder",
            initialdir=current if os.path.isdir(current) else None,
        )
        if folder:
            sfx_path = os.path.join(folder, "x64", "audio", "sfx")
            if not os.path.isdir(sfx_path):
                self.show_toast(
                    "GTA folder not recognized",
                    "The selected folder does not contain x64\\audio\\sfx.",
                    "warning",
                    6000,
                )
                return
            self.gta_dir.set(folder)
            self.show_toast(
                "GTA folder updated",
                "The SFX destination was detected automatically.",
            )


if __name__ == "__main__":
    BunnyManager().mainloop()
