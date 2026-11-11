#!/usr/bin/env python3
"""Void's Game Launcher — a small, dependency-free macOS game launcher.

Run with: python3 main.py

The launcher stores its library in ~/Library/Application Support/Void's Game
Launcher/games.json, while the app itself remains a single Python file.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
except ModuleNotFoundError as error:
    if error.name == "_tkinter":
        raise SystemExit(
            "Void's Game Launcher needs Tk support. Install the official macOS "
            "Python from python.org, then run this file with that python3."
        ) from error
    raise


APP_NAME = "Void's Game Launcher"
ACCENT = "#ff7a59"
ACCENT_HOVER = "#ff906f"
BG = "#111318"
SURFACE = "#191c23"
SURFACE_2 = "#20242d"
BORDER = "#2c313c"
TEXT = "#f5f5f7"
MUTED = "#9da3b0"


def tk_font(family: str, size: int, weight: str = "normal") -> str:
    """Return a Tcl font description that keeps space-containing family names intact."""
    return f"{{{family}}} {size} {weight}"


def library_file() -> Path:
    return Path.home() / "Library" / "Application Support" / "Void's Game Launcher" / "games.json"


def default_games() -> list[dict[str, Any]]:
    return [
        {
            "id": str(uuid.uuid4()),
            "name": "Your first game",
            "path": "",
            "genre": "Ready when you are",
            "favorite": True,
            "last_played": 0,
            "accent": "#ff7a59",
            "emoji": "✦",
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Add a game to begin",
            "path": "",
            "genre": "Tip: use the + button",
            "favorite": False,
            "last_played": 0,
            "accent": "#6f8cff",
            "emoji": "◈",
        },
    ]


class GameStore:
    def __init__(self) -> None:
        self.path = library_file()
        self.games: list[dict[str, Any]] = []
        self.load()

    def load(self) -> None:
        try:
            with self.path.open("r", encoding="utf-8") as handle:
                loaded = json.load(handle)
            if isinstance(loaded, list):
                self.games = loaded
        except (OSError, json.JSONDecodeError):
            self.games = []
        if not self.games:
            self.games = default_games()
            self.save()

    def save(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.path.with_suffix(".tmp")
            with temporary.open("w", encoding="utf-8") as handle:
                json.dump(self.games, handle, indent=2)
            temporary.replace(self.path)
        except OSError:
            # The launcher is still usable if a locked-down machine blocks persistence.
            pass

    def add(self, game: dict[str, Any]) -> None:
        self.games.append(game)
        self.save()

    def remove(self, game_id: str) -> None:
        self.games = [game for game in self.games if game.get("id") != game_id]
        self.save()


class RoundedButton(tk.Frame):
    """A lightweight button with a macOS-like hover state."""

    def __init__(self, master: tk.Misc, text: str, command, *, filled: bool = False, width: int | None = None):
        self.filled = filled
        self.command = command
        background = ACCENT if filled else SURFACE_2
        super().__init__(master, bg=background, highlightthickness=0, bd=0)
        self.label = tk.Label(
            self,
            text=text,
            bg=background,
            fg=TEXT,
            font=tk_font("SF Pro Display", 11, "bold"),
            padx=15,
            pady=9,
            cursor="pointinghand",
        )
        self.label.pack(fill="both", expand=True)
        if width:
            self.configure(width=width)
            self.pack_propagate(False)
        for widget in (self, self.label):
            widget.bind("<Button-1>", self._clicked)
            widget.bind("<Enter>", self._hover)
            widget.bind("<Leave>", self._leave)

    def _clicked(self, _event=None) -> None:
        self.command()

    def _hover(self, _event=None) -> None:
        color = ACCENT_HOVER if self.filled else "#2a303b"
        self.configure(bg=color)
        self.label.configure(bg=color)

    def _leave(self, _event=None) -> None:
        color = ACCENT if self.filled else SURFACE_2
        self.configure(bg=color)
        self.label.configure(bg=color)


class GameCard(tk.Frame):
    def __init__(self, master: tk.Misc, app: "Launcher", game: dict[str, Any]):
        super().__init__(master, bg=SURFACE, highlightbackground=BORDER, highlightthickness=1, bd=0)
        self.app = app
        self.game = game
        self.columnconfigure(1, weight=1)

        cover = tk.Frame(self, bg=game.get("accent", ACCENT), width=82, height=82)
        cover.grid(row=0, column=0, rowspan=2, padx=(15, 13), pady=15, sticky="nw")
        cover.pack_propagate(False)
        tk.Label(cover, text=game.get("emoji", "✦"), bg=game.get("accent", ACCENT), fg="#ffffff", font=tk_font("SF Pro Display", 28)).place(relx=.5, rely=.5, anchor="center")

        title = tk.Label(self, text=game.get("name", "Unnamed game"), bg=SURFACE, fg=TEXT, font=tk_font("SF Pro Display", 14, "bold"), anchor="w")
        title.grid(row=0, column=1, padx=(0, 10), pady=(17, 1), sticky="ew")
        details = game.get("genre") or "Game"
        if game.get("path"):
            details += "  ·  " + Path(game["path"]).name
        tk.Label(self, text=details, bg=SURFACE, fg=MUTED, font=tk_font("SF Pro Text", 10), anchor="w").grid(row=1, column=1, padx=(0, 10), sticky="ew")

        favorite = "★" if game.get("favorite") else "☆"
        favorite_button = tk.Label(self, text=favorite, bg=SURFACE, fg="#ffc857" if game.get("favorite") else MUTED, font=tk_font("SF Pro Display", 19), cursor="pointinghand")
        favorite_button.grid(row=0, column=2, padx=(0, 10), pady=(12, 0), sticky="ne")
        favorite_button.bind("<Button-1>", lambda _event: app.toggle_favorite(game))

        launch = tk.Label(self, text="PLAY", bg=game.get("accent", ACCENT), fg="#ffffff", font=tk_font("SF Pro Text", 9, "bold"), padx=12, pady=6, cursor="pointinghand")
        launch.grid(row=1, column=2, padx=(0, 10), pady=(0, 15), sticky="e")
        launch.bind("<Button-1>", lambda _event: app.launch(game))

        more = tk.Label(self, text="···", bg=SURFACE, fg=MUTED, font=tk_font("SF Pro Display", 15, "bold"), cursor="pointinghand")
        more.grid(row=0, column=3, padx=(0, 12), pady=(13, 0), sticky="ne")
        more.bind("<Button-1>", lambda _event: app.remove_game(game))
        self.bind("<Double-Button-1>", lambda _event: app.launch(game))
        for child in self.winfo_children():
            child.bind("<Double-Button-1>", lambda _event: app.launch(game), add="+")


class Launcher(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.store = GameStore()
        self.filter_name = "All Games"
        self.search_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Pick a game and press play")
        self.title(APP_NAME)
        self.geometry("1040x700")
        self.minsize(800, 560)
        self.configure(bg=BG)
        self.option_add("*Font", tk_font("SF Pro Text", 11))
        self._setup_styles()
        self._build_ui()
        self._bind_shortcuts()
        self.refresh()

    def _setup_styles(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Dark.Horizontal.TScrollbar", troughcolor=BG, background=BORDER, bordercolor=BG, arrowcolor=MUTED)

    def _build_ui(self) -> None:
        self.sidebar = tk.Frame(self, bg="#15171d", width=220)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        brand = tk.Frame(self.sidebar, bg="#15171d")
        brand.pack(fill="x", padx=22, pady=(27, 30))
        tk.Label(brand, text="VOID'S", bg="#15171d", fg=TEXT, font=tk_font("SF Pro Display", 12, "bold"), anchor="w").pack(fill="x")
        tk.Label(brand, text="GAME LAUNCHER", bg="#15171d", fg=ACCENT, font=tk_font("SF Pro Display", 10, "bold"), anchor="w").pack(fill="x", pady=(2, 0))

        self.nav = tk.Frame(self.sidebar, bg="#15171d")
        self.nav.pack(fill="x", padx=12)
        self.nav_buttons: dict[str, tk.Label] = {}
        for label, icon in (("All Games", "⌘"), ("Favorites", "★"), ("Recently Played", "◷")):
            self._add_nav(label, icon)

        tk.Frame(self.sidebar, bg="#15171d").pack(fill="both", expand=True)
        bottom = tk.Frame(self.sidebar, bg="#15171d")
        bottom.pack(fill="x", padx=12, pady=18)
        self._small_action(bottom, "⌘  Open Games Folder", self.open_games_folder)
        self._small_action(bottom, "⚙  Settings", self.show_settings)

        main = tk.Frame(self, bg=BG)
        main.pack(side="left", fill="both", expand=True)

        header = tk.Frame(main, bg=BG)
        header.pack(fill="x", padx=34, pady=(29, 20))
        heading = tk.Frame(header, bg=BG)
        heading.pack(side="left")
        self.heading_label = tk.Label(heading, text="All Games", bg=BG, fg=TEXT, font=tk_font("SF Pro Display", 25, "bold"), anchor="w")
        self.heading_label.pack(anchor="w")
        self.count_label = tk.Label(heading, text="", bg=BG, fg=MUTED, font=tk_font("SF Pro Text", 10), anchor="w")
        self.count_label.pack(anchor="w", pady=(3, 0))

        actions = tk.Frame(header, bg=BG)
        actions.pack(side="right", anchor="n")
        self.search = tk.Entry(actions, textvariable=self.search_var, bg=SURFACE, fg=TEXT, insertbackground=TEXT, relief="flat", highlightthickness=1, highlightbackground=BORDER, highlightcolor=ACCENT, width=22, font=tk_font("SF Pro Text", 11))
        self.search.pack(side="left", ipady=9, padx=(0, 10))
        self.search.insert(0, "  Search games")
        self.search.configure(fg=MUTED)
        self.search.bind("<FocusIn>", self._clear_search_placeholder)
        self.search.bind("<FocusOut>", self._restore_search_placeholder)
        self.search_var.trace_add("write", lambda *_args: self.refresh())
        RoundedButton(actions, "+  Add Game", self.add_game, filled=True).pack(side="left")

        content = tk.Frame(main, bg=BG)
        content.pack(fill="both", expand=True, padx=(34, 22), pady=(0, 22))
        self.canvas = tk.Canvas(content, bg=BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(content, orient="vertical", command=self.canvas.yview, style="Dark.Horizontal.TScrollbar")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.cards_frame = tk.Frame(self.canvas, bg=BG)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.cards_frame, anchor="nw")
        self.cards_frame.bind("<Configure>", lambda _event: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda event: self.canvas.itemconfigure(self.canvas_window, width=event.width))
        self.canvas.bind_all("<MouseWheel>", self._scroll)

        status = tk.Label(main, textvariable=self.status_var, bg="#15171d", fg=MUTED, anchor="w", padx=34, pady=8, font=tk_font("SF Pro Text", 9))
        status.pack(side="bottom", fill="x")

    def _add_nav(self, label: str, icon: str) -> None:
        button = tk.Label(self.nav, text=f"  {icon}    {label}", bg="#15171d", fg=MUTED, anchor="w", padx=8, pady=10, font=tk_font("SF Pro Text", 11), cursor="pointinghand")
        button.pack(fill="x", pady=1)
        button.bind("<Button-1>", lambda _event, name=label: self.select_filter(name))
        button.bind("<Enter>", lambda _event, item=button: item.configure(bg=SURFACE_2))
        button.bind("<Leave>", lambda _event, item=button: item.configure(bg=ACCENT if self.filter_name == label else "#15171d"))
        self.nav_buttons[label] = button

    def _small_action(self, parent: tk.Misc, text: str, command) -> None:
        action = tk.Label(parent, text=text, bg="#15171d", fg=MUTED, anchor="w", padx=8, pady=8, font=tk_font("SF Pro Text", 10), cursor="pointinghand")
        action.pack(fill="x")
        action.bind("<Button-1>", lambda _event: command())
        action.bind("<Enter>", lambda _event: action.configure(fg=TEXT))
        action.bind("<Leave>", lambda _event: action.configure(fg=MUTED))

    def _bind_shortcuts(self) -> None:
        self.bind("<Command-f>", lambda _event: self.search.focus_set())
        self.bind("<Command-o>", lambda _event: self.add_game())
        self.bind("<Command-r>", lambda _event: self.refresh())

    def _clear_search_placeholder(self, _event=None) -> None:
        if self.search_var.get() == "  Search games":
            self.search.delete(0, "end")
            self.search.configure(fg=TEXT)

    def _restore_search_placeholder(self, _event=None) -> None:
        if not self.search_var.get().strip():
            self.search.insert(0, "  Search games")
            self.search.configure(fg=MUTED)

    def _scroll(self, event) -> None:
        self.canvas.yview_scroll(int(-event.delta / 120), "units")

    def select_filter(self, name: str) -> None:
        self.filter_name = name
        self.heading_label.configure(text=name)
        for label, button in self.nav_buttons.items():
            button.configure(bg=ACCENT if label == name else "#15171d", fg="#ffffff" if label == name else MUTED)
        self.refresh()

    def filtered_games(self) -> list[dict[str, Any]]:
        games = list(self.store.games)
        if self.filter_name == "Favorites":
            games = [game for game in games if game.get("favorite")]
        elif self.filter_name == "Recently Played":
            games = [game for game in games if game.get("last_played", 0)]
            games.sort(key=lambda game: game.get("last_played", 0), reverse=True)
        query = self.search_var.get().strip().lower()
        if query and query != "search games":
            games = [game for game in games if query in game.get("name", "").lower() or query in game.get("genre", "").lower()]
        return games

    def refresh(self) -> None:
        if not hasattr(self, "cards_frame"):
            return
        for child in self.cards_frame.winfo_children():
            child.destroy()
        games = self.filtered_games()
        self.count_label.configure(text=f"{len(games)} game" + ("s" if len(games) != 1 else ""))
        if not games:
            empty = tk.Frame(self.cards_frame, bg=BG)
            empty.pack(fill="x", pady=72)
            tk.Label(empty, text="No games here yet", bg=BG, fg=TEXT, font=tk_font("SF Pro Display", 18, "bold")).pack()
            tk.Label(empty, text="Add an app or game to build your library.", bg=BG, fg=MUTED, font=tk_font("SF Pro Text", 11)).pack(pady=(8, 18))
            RoundedButton(empty, "+  Add Game", self.add_game, filled=True).pack()
        else:
            for game in games:
                GameCard(self.cards_frame, self, game).pack(fill="x", pady=(0, 10))
        self.canvas.yview_moveto(0)

    def add_game(self) -> None:
        selected = filedialog.askopenfilename(title="Choose a game or app", filetypes=[("Applications and executables", "*.app *.game *.exe *"), ("Applications", "*.app"), ("All files", "*")])
        if not selected:
            return
        path = Path(selected)
        if path.suffix.lower() not in {".app", ".game"} and not os.access(selected, os.X_OK):
            proceed = messagebox.askyesno("This file is not executable", "Add it anyway? You can edit the file later by removing and re-adding it.")
            if not proceed:
                return
        name = path.stem
        if path.suffix.lower() == ".app":
            name = path.stem
        game = {"id": str(uuid.uuid4()), "name": name, "path": str(path), "genre": "Mac game", "favorite": False, "last_played": 0, "accent": ACCENT, "emoji": "◈"}
        self.store.add(game)
        self.status_var.set(f"Added {name} to your library")
        self.refresh()

    def launch(self, game: dict[str, Any]) -> None:
        path_value = game.get("path", "")
        if not path_value:
            messagebox.showinfo("Ready to play", "This starter card is waiting for a game. Click + Add Game to choose an application.")
            return
        path = Path(path_value).expanduser()
        if not path.exists():
            messagebox.showerror("Game not found", f"I couldn't find:\n\n{path}\n\nRemove it and add the game again.")
            return
        try:
            if path.suffix.lower() == ".app":
                subprocess.Popen(["open", str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                subprocess.Popen([str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            game["last_played"] = time.time()
            self.store.save()
            self.status_var.set(f"Launching {game.get('name', 'game')}…")
            self.refresh()
        except OSError as error:
            messagebox.showerror("Couldn't launch game", str(error))

    def toggle_favorite(self, game: dict[str, Any]) -> None:
        game["favorite"] = not game.get("favorite", False)
        self.store.save()
        self.status_var.set(("Added to" if game["favorite"] else "Removed from") + " favorites")
        self.refresh()

    def remove_game(self, game: dict[str, Any]) -> None:
        name = game.get("name", "this game")
        if messagebox.askyesno("Remove game", f"Remove {name} from your library?\n\nThis does not delete the app."):
            self.store.remove(game.get("id", ""))
            self.status_var.set(f"Removed {name} from your library")
            self.refresh()

    def open_games_folder(self) -> None:
        folder = Path.home() / "Applications"
        folder.mkdir(parents=True, exist_ok=True)
        subprocess.Popen(["open", str(folder)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def show_settings(self) -> None:
        messagebox.showinfo("About Void's Game Launcher", "A tiny, local-first game launcher for macOS.\n\nLibrary file:\n" + str(self.store.path))


if __name__ == "__main__":
    if sys.platform != "darwin":
        # Tk works on many Unix systems too; this warning keeps the file useful for testing.
        print("Note: this launcher is designed for macOS, but can be previewed on other systems with Tk installed.")
    app = Launcher()
    app.mainloop()
