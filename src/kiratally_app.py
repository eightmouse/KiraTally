import ctypes
import json
import os
import threading
import sys
import time
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

from PIL import Image, ImageTk

try:
    import pygame
except Exception:
    pygame = None


APP_NAME = "KiraTally"
UI_BG = "#11131a"
UI_PANEL_BG = "#0f1420"

if getattr(sys, "frozen", False):
    APP_DIR = Path(sys.executable).resolve().parent
    RESOURCE_DIR = Path(getattr(sys, "_MEIPASS", APP_DIR))
else:
    APP_DIR = Path(__file__).resolve().parent.parent
    RESOURCE_DIR = APP_DIR

DATA_FILE = APP_DIR / "kira_data.json"
LOCAL_SPRITE_DIR = APP_DIR / "assets" / "gen3"
BUNDLED_SPRITE_DIR = RESOURCE_DIR / "assets" / "gen3"
SPRITE_SEARCH_DIRS = [LOCAL_SPRITE_DIR, BUNDLED_SPRITE_DIR]
NAMES_CACHE_FILE = LOCAL_SPRITE_DIR / "gen3_names.json"
BUNDLED_NAMES_FILE = BUNDLED_SPRITE_DIR / "gen3_names.json"
APP_LOGO_CANDIDATES = [
    APP_DIR / "assets" / "logo.png",
    APP_DIR / "assets" / "Logo.png",
    RESOURCE_DIR / "assets" / "logo.png",
    RESOURCE_DIR / "assets" / "Logo.png",
]
APP_LOGO_PATH = next((path for path in APP_LOGO_CANDIDATES if path.exists()), APP_LOGO_CANDIDATES[0])

GEN3_MAX_DEX = 386

class RoundedButton(tk.Canvas):
    def __init__(self, master, text, command, bg_color, fg_color, width=90, height=30, radius=10):
        super().__init__(
            master,
            width=width,
            height=height,
            highlightthickness=0,
            bd=0,
            bg=master.cget("bg"),
            cursor="hand2",
        )
        self.text = text
        self.command = command
        self.bg_color = bg_color
        self.fg_color = fg_color
        self.radius = radius
        self._hover = False

        self.bind("<Configure>", self._draw)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)

    @staticmethod
    def _shade(color, factor):
        color = color.lstrip("#")
        r = max(0, min(255, int(int(color[0:2], 16) * factor)))
        g = max(0, min(255, int(int(color[2:4], 16) * factor)))
        b = max(0, min(255, int(int(color[4:6], 16) * factor)))
        return f"#{r:02x}{g:02x}{b:02x}"

    def _on_enter(self, _event):
        self._hover = True
        self._draw()

    def _on_leave(self, _event):
        self._hover = False
        self._draw()

    def _on_click(self, _event):
        if callable(self.command):
            self.command()

    def _draw(self, _event=None):
        self.delete("all")
        width = max(4, self.winfo_width())
        height = max(4, self.winfo_height())
        radius = min(self.radius, width // 2, height // 2)
        fill = self._shade(self.bg_color, 1.08) if self._hover else self.bg_color

        self.create_rectangle(radius, 0, width - radius, height, fill=fill, outline="")
        self.create_rectangle(0, radius, width, height - radius, fill=fill, outline="")
        self.create_oval(0, 0, radius * 2, radius * 2, fill=fill, outline="")
        self.create_oval(width - 2 * radius, 0, width, radius * 2, fill=fill, outline="")
        self.create_oval(0, height - 2 * radius, radius * 2, height, fill=fill, outline="")
        self.create_oval(width - 2 * radius, height - 2 * radius, width, height, fill=fill, outline="")
        self.create_text(width / 2, height / 2, text=self.text, fill=self.fg_color, font=("Segoe UI", 10, "bold"))


class KiraTallyApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.geometry("420x560")
        self.root.resizable(False, False)
        self.root.configure(bg=UI_BG)

        self.counter = 0
        self.sprite_path = ""
        self.current_dex = 1
        self.reset_input_text = "ctrl+r"

        self._photo = None
        self._app_icon_photo = None

        self.name_to_dex = {}
        self.alias_to_name = {}
        self.ordered_names = []
        self.suggestion_names = []
        self.suggestions_visible = False

        self.binding = {"type": "keyboard", "groups": [[0x11], [ord("R")]]}

        self.listener_running = False
        self.listener_thread = None

        self.controller_ready = False
        self.controllers = {}

        self._ensure_dirs()
        self._load_name_index()
        self._load_data()
        self._build_ui()
        self._apply_app_icon()
        self._apply_windows_titlebar_theme()

        if self.sprite_path and os.path.exists(self.sprite_path):
            self._render_sprite()
        else:
            self._load_sprite_by_dex(self.current_dex, show_error=False)

        self._apply_reset_binding(show_error=False)
        self._start_listener()
        self._refresh_counter()

    def _build_ui(self):
        sprite_frame = tk.Frame(self.root, bg="#0d1017", highlightbackground="#273352", highlightthickness=1, height=230)
        sprite_frame.pack(fill="x", padx=12, pady=(12, 8))
        sprite_frame.pack_propagate(False)

        self.sprite_label = tk.Label(sprite_frame, text="No Gen3 Shiny Sprite", bg="#0d1017", fg="#8fa1d1", font=("Segoe UI", 11))
        self.sprite_label.pack(fill="both", expand=True)

        select_row = tk.Frame(self.root, bg=UI_BG)
        select_row.pack(fill="x", padx=12, pady=(0, 8))

        tk.Label(select_row, text="Dex # (1-386)", fg="#d8e2ff", bg=UI_BG, font=("Segoe UI", 9, "bold")).pack(anchor="w")

        self.pokemon_var = tk.StringVar(value=str(self.current_dex))
        self.pokemon_entry = tk.Entry(
            select_row,
            textvariable=self.pokemon_var,
            bg="#1b2235",
            fg="#f4f6ff",
            insertbackground="#f4f6ff",
            relief="flat",
            font=("Consolas", 12),
        )
        self.pokemon_entry.pack(fill="x", ipady=6)
        self.pokemon_entry.bind("<KeyRelease>", self._on_entry_key_release)
        self.pokemon_entry.bind("<Return>", self._apply_pokemon_input)
        self.pokemon_entry.bind("<Down>", self._entry_focus_suggestions)

        self.suggest_list = tk.Listbox(
            select_row,
            height=6,
            bg="#121a2d",
            fg="#f1f5ff",
            selectbackground="#2e466e",
            selectforeground="#ffffff",
            relief="flat",
            highlightthickness=0,
            font=("Segoe UI", 10),
        )
        self.suggest_list.bind("<Double-Button-1>", self._choose_suggestion)
        self.suggest_list.bind("<Return>", self._choose_suggestion)
        self.suggest_list.bind("<Escape>", self._hide_suggestions)

        counter_frame = tk.Frame(self.root, bg=UI_BG)
        counter_frame.pack(fill="x", padx=12, pady=(2, 6))

        tk.Label(counter_frame, text="Resets", fg="#cbd6ff", bg=UI_BG, font=("Segoe UI", 11)).pack()

        self.counter_var = tk.StringVar(value="0")
        tk.Label(counter_frame, textvariable=self.counter_var, fg="#ffffff", bg=UI_BG, font=("Consolas", 38, "bold")).pack()

        controls = tk.Frame(self.root, bg=UI_BG)
        controls.pack(fill="x", padx=12, pady=(0, 8))

        undo_btn = RoundedButton(controls, "Undo", self.undo_increment, "#4f3b1f", "#fff2de")
        undo_btn.pack(side="left", fill="x", expand=True, padx=(0, 4), ipady=2)

        reset_btn = RoundedButton(controls, "Reset", self.reset_counter, "#5f2626", "#ffe9e9")
        reset_btn.pack(side="left", fill="x", expand=True, padx=(4, 0), ipady=2)

        input_box = tk.Frame(self.root, bg=UI_PANEL_BG, highlightbackground="#2b3552", highlightthickness=1)
        input_box.pack(fill="x", padx=12, pady=(0, 12))

        tk.Label(
            input_box,
            text="Reset Input",
            fg="#d8e2ff",
            bg=UI_PANEL_BG,
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor="w", padx=8, pady=(8, 6))

        self.reset_input_var = tk.StringVar(value=self.reset_input_text)
        self.reset_input_entry = tk.Entry(
            input_box,
            textvariable=self.reset_input_var,
            bg="#1b2235",
            fg="#f4f6ff",
            insertbackground="#f4f6ff",
            relief="flat",
            font=("Consolas", 10),
        )
        self.reset_input_entry.pack(fill="x", padx=8, pady=(0, 6), ipady=5)
        self.reset_input_entry.bind("<Return>", self._apply_reset_binding_ui)
        self.reset_input_entry.bind("<FocusOut>", self._apply_reset_binding_ui)

        tk.Label(
            input_box,
            text="Examples: ctrl+r   pad:a   pad:button0   pad:dpad_up",
            fg="#90a5d6",
            bg=UI_PANEL_BG,
            font=("Segoe UI", 8),
        ).pack(anchor="w", padx=8, pady=(0, 8))

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _update_title(self):
        self.root.title(APP_NAME)

    def _refresh_counter(self):
        self.counter_var.set(str(self.counter))
        self._update_title()

    def _apply_app_icon(self):
        try:
            if not APP_LOGO_PATH.exists():
                return
            img = Image.open(APP_LOGO_PATH).convert("RGBA")
            img.thumbnail((256, 256), Image.LANCZOS)
            self._app_icon_photo = ImageTk.PhotoImage(img)
            self.root.iconphoto(True, self._app_icon_photo)
        except Exception:
            pass

    @staticmethod
    def _display_name(name):
        return " ".join(part.capitalize() for part in name.replace("-", " ").split())

    @staticmethod
    def _normalize_name(text):
        out = text.strip().lower().replace("'", "").replace(".", "")
        out = out.replace("_", "-").replace(" ", "-")
        out = "-".join([p for p in out.split("-") if p])
        return out

    @staticmethod
    def _colorref(hex_color):
        hex_color = hex_color.lstrip("#")
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        return r | (g << 8) | (b << 16)

    def _apply_windows_titlebar_theme(self):
        if os.name != "nt":
            return
        try:
            self.root.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
            dwmapi = ctypes.windll.dwmapi

            dark = ctypes.c_int(1)
            dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(dark), ctypes.sizeof(dark))

            caption = ctypes.c_uint(self._colorref(UI_BG))
            dwmapi.DwmSetWindowAttribute(hwnd, 35, ctypes.byref(caption), ctypes.sizeof(caption))

            text = ctypes.c_uint(self._colorref("#e9efff"))
            dwmapi.DwmSetWindowAttribute(hwnd, 36, ctypes.byref(text), ctypes.sizeof(text))
        except Exception:
            pass

    def _ensure_dirs(self):
        # Sprite assets are bundled; no runtime download/cache directory is needed.
        return
    def _load_name_index(self):
        name_list = []
        for candidate in (NAMES_CACHE_FILE, BUNDLED_NAMES_FILE):
            if not candidate.exists():
                continue
            try:
                with open(candidate, "r", encoding="utf-8") as f:
                    cached = json.load(f)
                if isinstance(cached, list) and len(cached) >= GEN3_MAX_DEX:
                    name_list = cached[:GEN3_MAX_DEX]
                    break
            except (json.JSONDecodeError, OSError):
                continue

        for i, name in enumerate(name_list, start=1):
            if not name:
                continue
            canonical = name.lower()
            self.name_to_dex[canonical] = i
            self.ordered_names.append(canonical)
            normalized = self._normalize_name(canonical)
            self.alias_to_name[normalized] = canonical
            self.alias_to_name[normalized.replace("-", "")] = canonical
    def _load_data(self):
        if not DATA_FILE.exists():
            return
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return

        self.counter = int(data.get("count", 0))
        self.sprite_path = str(data.get("sprite_path", ""))
        self.current_dex = int(data.get("dex", 1))
        self.reset_input_text = str(data.get("hotkey", "ctrl+r"))

        if self.current_dex < 1 or self.current_dex > GEN3_MAX_DEX:
            self.current_dex = 1

    def _save_data(self):
        data = {
            "count": self.counter,
            "sprite_path": self.sprite_path,
            "dex": self.current_dex,
            "hotkey": self.reset_input_var.get().strip() if hasattr(self, "reset_input_var") else self.reset_input_text,
        }
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def _load_sprite_by_dex(self, dex, show_error=True):
        try:
            sprite_path = self._fetch_gen3_sprite(dex)
        except RuntimeError as exc:
            if show_error:
                messagebox.showerror("Sprite", str(exc))
            return False

        self.current_dex = dex
        self.sprite_path = sprite_path
        self._render_sprite()
        self._save_data()
        return True

    def _apply_pokemon_input(self, _event=None):
        raw = self.pokemon_var.get().strip()
        if not raw:
            return

        if raw.isdigit():
            dex = int(raw)
            if dex < 1 or dex > GEN3_MAX_DEX:
                messagebox.showerror("Dex", "Dex must be between 1 and 386.")
                return
            if self._load_sprite_by_dex(dex, show_error=True):
                self.pokemon_var.set(str(dex))
                self._hide_suggestions()
            return

        normalized = self._normalize_name(raw)
        canonical = self.alias_to_name.get(normalized) or self.alias_to_name.get(normalized.replace("-", ""))
        if not canonical:
            messagebox.showerror("Pokemon", "Unknown Gen3 Pokemon name. Try Dex number or choose suggestion.")
            return

        dex = self.name_to_dex.get(canonical)
        if not dex:
            messagebox.showerror("Pokemon", "Pokemon is not in the current Gen3 list.")
            return

        if self._load_sprite_by_dex(dex, show_error=True):
            self.pokemon_var.set(canonical)
            self._hide_suggestions()

    def _on_entry_key_release(self, event):
        if event.keysym in {"Return", "Up", "Down", "Escape"}:
            if event.keysym == "Escape":
                self._hide_suggestions()
            return

        query = self.pokemon_var.get().strip().lower()
        if not query or query.isdigit() or not self.ordered_names:
            self._hide_suggestions()
            return

        starts = [name for name in self.ordered_names if name.startswith(query)]
        if len(starts) < 8:
            contains = [name for name in self.ordered_names if query in name and name not in starts]
            starts.extend(contains)

        matches = starts[:8]
        if not matches:
            self._hide_suggestions()
            return

        self.suggestion_names = matches
        self.suggest_list.delete(0, tk.END)
        for name in matches:
            dex = self.name_to_dex.get(name, 0)
            self.suggest_list.insert(tk.END, f"#{dex:03d} {self._display_name(name)}")

        if not self.suggestions_visible:
            self.suggest_list.pack(fill="x", pady=(4, 0))
            self.suggestions_visible = True

    def _hide_suggestions(self, _event=None):
        if self.suggestions_visible:
            self.suggest_list.pack_forget()
            self.suggestions_visible = False
        return "break"

    def _entry_focus_suggestions(self, _event=None):
        if self.suggestions_visible and self.suggestion_names:
            self.suggest_list.focus_set()
            self.suggest_list.selection_clear(0, tk.END)
            self.suggest_list.selection_set(0)
            self.suggest_list.activate(0)
            return "break"
        return None

    def _choose_suggestion(self, _event=None):
        if not self.suggestions_visible:
            return "break"
        selected = self.suggest_list.curselection()
        if not selected:
            return "break"

        idx = selected[0]
        if idx < 0 or idx >= len(self.suggestion_names):
            return "break"

        name = self.suggestion_names[idx]
        self.pokemon_var.set(name)
        self._apply_pokemon_input()
        self.pokemon_entry.focus_set()
        return "break"

    def _fetch_gen3_sprite(self, dex):
        for folder in SPRITE_SEARCH_DIRS:
            sprite_path = folder / f"{dex}_shiny.png"
            if sprite_path.exists() and sprite_path.stat().st_size > 0:
                return str(sprite_path)

        raise RuntimeError("Missing bundled shiny sprite. Rebuild with assets/gen3 included.")
    def _render_sprite(self):
        if not self.sprite_path or not os.path.exists(self.sprite_path):
            self._photo = None
            self.sprite_label.configure(image="", text="No Gen3 Shiny Sprite")
            return

        try:
            img = Image.open(self.sprite_path).convert("RGBA")
            w, h = img.size
            max_dim = max(w, h)
            target = 250

            if max_dim < target:
                scale = max(1, target // max_dim)
                scale = min(scale, 8)
                img = img.resize((w * scale, h * scale), Image.NEAREST)

            if max(img.size) > target:
                img.thumbnail((target, target), Image.NEAREST)

            self._photo = ImageTk.PhotoImage(img)
            self.sprite_label.configure(image=self._photo, text="")
        except OSError:
            self._photo = None
            self.sprite_label.configure(image="", text="Invalid Sprite")

    def undo_increment(self):
        if self.counter > 0:
            self.counter -= 1
            self._refresh_counter()
            self._save_data()

    def reset_counter(self):
        if not messagebox.askyesno("Reset Counter", "Reset counter to 0?"):
            return
        self.counter = 0
        self._refresh_counter()
        self._save_data()

    @staticmethod
    def _vk_for_token(token):
        mapping = {
            "ctrl": [0x11],
            "control": [0x11],
            "shift": [0x10],
            "alt": [0x12],
            "win": [0x5B, 0x5C],
            "windows": [0x5B, 0x5C],
            "space": [0x20],
            "enter": [0x0D],
            "tab": [0x09],
            "esc": [0x1B],
            "escape": [0x1B],
        }
        if token in mapping:
            return mapping[token]
        if len(token) == 1 and token.isalpha():
            return [ord(token.upper())]
        if len(token) == 1 and token.isdigit():
            return [ord(token)]
        if token.startswith("f") and token[1:].isdigit():
            num = int(token[1:])
            if 1 <= num <= 24:
                return [0x70 + (num - 1)]
        return None

    def _parse_keyboard_binding(self, text):
        tokens = [part.strip().lower() for part in text.split("+") if part.strip()]
        if len(tokens) < 2:
            raise ValueError("Keyboard binding must be like ctrl+r")

        groups = []
        for token in tokens:
            vks = self._vk_for_token(token)
            if not vks:
                raise ValueError(f"Unsupported keyboard token: {token}")
            groups.append(vks)
        return {"type": "keyboard", "groups": groups}

    @staticmethod
    def _controller_button_alias(token):
        alias = {
            "a": 0,
            "cross": 0,
            "south": 0,
            "b": 1,
            "circle": 1,
            "east": 1,
            "x": 2,
            "square": 2,
            "west": 2,
            "y": 3,
            "triangle": 3,
            "north": 3,
            "lb": 4,
            "l1": 4,
            "rb": 5,
            "r1": 5,
            "back": 6,
            "select": 6,
            "share": 6,
            "minus": 6,
            "start": 7,
            "options": 7,
            "plus": 7,
            "l3": 8,
            "r3": 9,
        }
        return alias.get(token)

    def _parse_controller_binding(self, text):
        payload = text[4:].strip().lower()
        if not payload:
            raise ValueError("Controller binding format: pad:a or pad:button0")

        parts = [p.strip() for p in payload.split("+") if p.strip()]
        reqs = []
        dpad_map = {
            "dpad_up": (0, 1),
            "dpad_down": (0, -1),
            "dpad_left": (-1, 0),
            "dpad_right": (1, 0),
        }

        for part in parts:
            if part in dpad_map:
                reqs.append({"type": "hat", "value": dpad_map[part]})
                continue
            if part.startswith("button") and part[6:].isdigit():
                reqs.append({"type": "button", "index": int(part[6:])})
                continue

            idx = self._controller_button_alias(part)
            if idx is not None:
                reqs.append({"type": "button", "index": idx})
                continue

            raise ValueError(f"Unsupported controller token: {part}")

        if not reqs:
            raise ValueError("Controller binding is empty")

        return {"type": "controller", "requirements": reqs}

    def _apply_reset_binding(self, show_error=True):
        raw = self.reset_input_var.get().strip() if hasattr(self, "reset_input_var") else self.reset_input_text
        if not raw:
            if show_error:
                messagebox.showerror("Reset Input", "Reset input cannot be empty.")
            return False

        try:
            if raw.lower().startswith("pad:"):
                parsed = self._parse_controller_binding(raw)
                if pygame is None:
                    raise ValueError("Controller input requires pygame. Install with: pip install pygame")
            else:
                parsed = self._parse_keyboard_binding(raw)
        except ValueError as exc:
            if show_error:
                messagebox.showerror("Reset Input", str(exc))
            return False

        self.binding = parsed
        self.reset_input_text = raw
        self._save_data()
        self._update_title()
        return True

    def _apply_reset_binding_ui(self, _event=None):
        if not self._apply_reset_binding(show_error=True):
            self.reset_input_var.set(self.reset_input_text)
        return None

    @staticmethod
    def _any_pressed(vks):
        user32 = ctypes.windll.user32
        for vk in vks:
            if user32.GetAsyncKeyState(vk) & 0x8000:
                return True
        return False

    def _is_keyboard_binding_active(self, binding):
        for group in binding["groups"]:
            if not self._any_pressed(group):
                return False
        return True

    def _ensure_controller_runtime(self):
        if pygame is None:
            return False
        if not self.controller_ready:
            pygame.init()
            pygame.joystick.init()
            self.controller_ready = True
        return True

    def _refresh_controllers(self):
        pygame.event.pump()
        count = pygame.joystick.get_count()

        for idx in range(count):
            if idx not in self.controllers:
                js = pygame.joystick.Joystick(idx)
                js.init()
                self.controllers[idx] = js

        for idx in list(self.controllers.keys()):
            if idx >= count:
                try:
                    self.controllers[idx].quit()
                except Exception:
                    pass
                del self.controllers[idx]

    @staticmethod
    def _joystick_matches(joy, requirements):
        for req in requirements:
            if req["type"] == "button":
                idx = req["index"]
                if idx >= joy.get_numbuttons() or joy.get_button(idx) != 1:
                    return False
            elif req["type"] == "hat":
                wanted = req["value"]
                matched = False
                for i in range(joy.get_numhats()):
                    if joy.get_hat(i) == wanted:
                        matched = True
                        break
                if not matched:
                    return False
            else:
                return False
        return True

    def _is_controller_binding_active(self, binding):
        if not self._ensure_controller_runtime():
            return False
        self._refresh_controllers()
        if not self.controllers:
            return False

        reqs = binding["requirements"]
        for joy in self.controllers.values():
            if self._joystick_matches(joy, reqs):
                return True
        return False

    def _is_binding_active(self):
        if self.binding["type"] == "keyboard":
            return self._is_keyboard_binding_active(self.binding)
        if self.binding["type"] == "controller":
            return self._is_controller_binding_active(self.binding)
        return False

    def _listener_loop(self):
        held = False
        while self.listener_running:
            active = self._is_binding_active()
            if active and not held:
                held = True
                self.root.after(0, self._increment_from_binding)
            elif not active:
                held = False
            time.sleep(0.03)

    def _start_listener(self):
        if self.listener_running:
            return
        self.listener_running = True
        self.listener_thread = threading.Thread(target=self._listener_loop, daemon=True)
        self.listener_thread.start()

    def _stop_listener(self):
        self.listener_running = False
        if self.controller_ready and pygame is not None:
            try:
                for js in self.controllers.values():
                    js.quit()
                self.controllers.clear()
                pygame.joystick.quit()
                pygame.quit()
            except Exception:
                pass

    def _increment_from_binding(self):
        self.counter += 1
        self._refresh_counter()
        self._save_data()

    def on_close(self):
        self._stop_listener()
        self._save_data()
        self.root.destroy()


def main():
    root = tk.Tk()
    KiraTallyApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()





