![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
[![Support me on Ko-fi](https://img.shields.io/badge/Support%20Me-Ko--fi-F16061?logo=ko-fi&logoColor=white)](https://ko-fi.com/eightmouse)

# KiraTally
A Global, Hotkey-Driven Shiny Counter for Pokémon (3rd Gen). 
KiraTally is a lightweight, background-running counter designed to track shiny hunting resets. 
It eliminates the "false positives" of visual-based counters.

<img width="422" height="592" alt="Screenshot 2026-03-05 200722" src="https://github.com/user-attachments/assets/c4cfb37b-47d6-4ffb-a732-b29d01b739fa" />

## Project structure

- `main.py`: root launcher entrypoint.
- `src/kiratally_app.py`: app implementation.
- `assets/logo.png`: window/app logo source.
- `assets/logo.ico`: exe icon source.
- `assets/gen3/*_shiny.png`: bundled shiny sprites.
- `assets/gen3/gen3_names.json`: bundled autocomplete names.

## Current behavior

- Fixed-size window UI.
- Pokemon input accepts Dex number (`1-386`) or Gen3 name.
- Autocomplete loads locally from bundled `assets/gen3/gen3_names.json`.
- Sprite preview is **shiny-only** (`*_shiny.png`).
- No runtime sprite downloads.

## Reset Input

- Field starts empty and shows placeholder: `Input hotkey and press Enter...`
- Single-key keyboard inputs work (examples: `space`, `z`, `r`).
- Combo keyboard inputs work (examples: `ctrl+r`, `ctrl+shift+r`).
- Controller input works on Windows via built-in XInput (examples: `pad:rb`, `pad:a`, `pad:dpad_up`, `pad:lb+rb`).

Supported controller tokens:
- face: `a`, `b`, `x`, `y`, `cross`, `circle`, `square`, `triangle`
- shoulder: `lb`, `rb`, `l1`, `r1`
- system: `start`, `back`, `select`, `options`, `share`, `plus`, `minus`
- sticks: `l3`, `r3`
- dpad: `dpad_up`, `dpad_down`, `dpad_left`, `dpad_right`
- raw: `button0` ... `button9`

## Build EXE (Windows)

```powershell
& "$env:APPDATA\Python\Python313\Scripts\pyinstaller.exe" --noconfirm --clean --windowed --name KiraTally --icon "assets\logo.ico" --add-data "assets\logo.png;assets" --add-data "assets\gen3;assets\gen3" main.py
```

Output:
- `dist/KiraTally/KiraTally.exe`
