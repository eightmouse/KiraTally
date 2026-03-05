![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![Target](https://img.shields.io/badge/Target-GBA-orange)
![Stage](https://img.shields.io/badge/Stage-Archived-brown.svg)
![Support](https://img.shields.io/badge/Support-None-lightgrey.svg)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey)
[![Support me on Ko-fi](https://img.shields.io/badge/Support%20Me-Ko--fi-F16061?logo=ko-fi&logoColor=white)](https://ko-fi.com/eightmouse)

# KiraTally

Minimal shiny hunting reset counter (Gen 3).

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

Keyboard examples:
- `ctrl+r`
- `ctrl+shift+r`

Controller examples (Xbox/Sony/Switch via SDL/pygame):
- `pad:a`
- `pad:button0`
- `pad:dpad_up`
- `pad:lb+rb`

Supported controller tokens:
- face: `a`, `b`, `x`, `y`, `cross`, `circle`, `square`, `triangle`
- shoulder: `lb`, `rb`, `l1`, `r1`
- system: `start`, `back`, `select`, `options`, `share`, `plus`, `minus`
- sticks: `l3`, `r3`
- dpad: `dpad_up`, `dpad_down`, `dpad_left`, `dpad_right`
- raw: `button0`, `button1`, ...

## Build EXE (Windows)

```powershell
& "$env:APPDATA\Python\Python313\Scripts\pyinstaller.exe" --noconfirm --clean --windowed --name KiraTally --icon "assets\logo.ico" --add-data "assets\logo.png;assets" --add-data "assets\gen3;assets\gen3" main.py
```

Output:
- `dist/KiraTally/KiraTally.exe`
