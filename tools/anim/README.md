# tabby_anim – Animations-Pipeline

Erzeugt GIFs im Format der Taby-Firmware (280 × 456, um 90° gedreht, 24 fps, reines Schwarz, globale Palette, Delta-optimiert).
Hintergrund und Stilguide: [docs/spec/animationen.md](../../docs/spec/animationen.md).

```sh
pip install -r requirements.txt          # Pillow; gifsicle optional (apt install gifsicle) für kleinere Dateien
cd tools/anim
python -m tabby_anim build ../../animations/src --out ../../dist/animations
python -m tabby_anim extract some.gif --out frames/   # GIF → quer liegende PNG-Frames
python -m tabby_anim preview ../../animations/src/<id> --out sheet.png   # Kontaktbogen mit Zeitstempeln
python -m unittest discover -s tests -v
```

Lokal ist das optional: Der Workflow `.github/workflows/animations.yml` baut bei jedem Push alles und hängt GIFs, Vorschauen und `report.json` als Artefakt an.

**Mit Claude Code:** `/tabby-animation <Beschreibung>`. Der Skill (`.claude/skills/tabby-animation/`) schreibt die Keyframes, baut, prüft den Kontaktbogen und bessert nach.

## Quellen: `animations/src/<id>/`

| Datei | Pflicht | Inhalt |
|---|---|---|
| `meta.json` | ja | `id` (= Ordnername, `a-z0-9_`), `label`, `max_colors` (Standard 16), `max_kb` (Standard 150), optional `prompt` (Beschreibung, aus der die Keyframes entstanden sind), `loop` (nur für PNG-Quellen) |
| `keyframes.json` | entweder | Face-Rig-Animation (siehe unten) |
| `frames/*.png` | oder | Export aus einem Animationsprogramm: **456 × 280 quer**, 24 fps, schwarzer Hintergrund |

## Face-Rig: `keyframes.json`

```json
{
  "duration_s": 3.0,
  "loop": true,
  "keyframes": [
    { "t": 0.0, "pose": { "eye_open": 1, "mouth_curve": 12 } },
    { "t": 1.3, "pose": { "eye_open": 0.08 }, "ease": "in" },
    { "t": 1.42, "pose": { "eye_open": 1 }, "ease": "out" }
  ]
}
```

Nicht gesetzte Parameter übernehmen den Wert des vorigen Keyframes. `ease` gilt für den Weg **zu** diesem Keyframe.

| Parameter | Standard | Bedeutung |
|---|---|---|
| `look_x`, `look_y` | 0 | Blickrichtung in px (Mund bewegt sich 60 % mit) |
| `bounce` | 0 | ganzes Gesicht hoch (negativ) / runter |
| `eye_open` | 1 | 0 = zu (Strich), 1 = offen; staucht zur Unterkante wie im Original |
| `eye_scale` | 1 | Augengröße |
| `squash` | 1 | > 1 breiter und flacher, < 1 schmaler und höher (Volumen bleibt) |
| `happy` | 0 | ≥ 0,5 = „^ ^“-Bogenaugen |
| `mouth_curve` | 12 | px, > 0 Lächeln, < 0 traurig, 0 gerade |
| `mouth_width` | 94 | px |
| `mouth_open` | 0 | > 1 = offener Mund (Höhe in px) |
| `blush` | 0 | 0–1 Wangen-Striche |

Easing: `linear`, `in`, `out`, `inOut` (Standard), `back` (Überschwingen), `hold` (springt am Ende).
