# tabby_anim – Animations-Pipeline

Erzeugt GIFs im Format der Taby-Firmware (280 × 456, um 90° gedreht, 24 fps, reines Schwarz, globale Palette, Delta-optimiert).
Hintergrund und Stilguide: [docs/spec/animationen.md](../../docs/spec/animationen.md).

```sh
pip install -r requirements.txt          # Pillow; gifsicle optional (apt install gifsicle) für kleinere Dateien
cd tools/anim
python -m tabby_anim build ../../animations/src --out ../../dist/animations
python -m tabby_anim extract some.gif --out frames/   # GIF → quer liegende PNG-Frames
python -m tabby_anim preview ../../animations/src/<id> --out sheet.png   # Kontaktbogen mit Zeitstempeln
python -m tabby_anim catalog --out catalog.png                     # alle Augenformen, Hände, Gegenstände
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
| `tears` | 0 | 0–1 Tränen laufen aus beiden Augen (bewegen sich von selbst) |
| `sweat` | 0 | 0–1 Schweißtropfen an der Kopfseite |
| `face_x`, `face_y` | 0 | ganzes Gesicht verschieben (px), z. B. nach rechts, wenn links ein Gegenstand liegt |
| `face_scale` | 1 | Gesichtsgröße 0,5–1,2 |
| `turn` | 0 | −1…1 Kopf zur Seite drehen (− = nach links): Augen und Mund wandern mit, der Abstand wird kleiner, das Auge in Blickrichtung wird schmaler (Dreiviertelansicht) |
| `eye_shape` | `pill` | `pill`, `happy` (^ ^), `closed`, `angry`, `sad`, `squint` (> <), `heart`, `star`, `dizzy`. Wechselt am Keyframe ohne Überblenden. |

Easing: `linear`, `in`, `out`, `inOut` (Standard), `back` (Überschwingen), `hold` (springt am Ende).

## Hände und Gegenstände: `props`

Zusätzlich zu `keyframes` (Gesicht) kann eine Animation Spuren für Hände und Gegenstände haben:

```json
"props": [
  { "type": "hand", "name": "hand", "side": "right",
    "keyframes": [ { "t": 0, "x": 330, "y": 250, "rot": -8, "shape": "hold" },
                   { "t": 1.2, "x": 236, "y": 246, "rot": -18 } ] },
  { "type": "water_glass", "attach_to": "hand",
    "keyframes": [ { "t": 0, "x": 0, "y": -62, "progress": 1 }, { "t": 2.6, "progress": 0.45, "ease": "linear" } ] }
]
```

| Feld der Spur | Bedeutung |
|---|---|
| `type` | `hand` oder ein Gegenstand (siehe unten) |
| `name` | optional, damit andere Spuren sich daran hängen können |
| `attach_to` | Name einer anderen Spur: `x`/`y`/`rot` gelten dann **relativ** zu ihr (Hand hält Glas) |
| `side` | nur Hände: `right` (Standard) oder `left` (gespiegelt) |
| `layer` | `front` (über dem Gesicht, Standard) oder `back` (dahinter, z. B. Feuerwerk) |

Keyframe-Felder (flach, ohne `pose`): `t`, `ease`, `x`, `y` (Mittelpunkt, Bildschirm 456 × 280), `rot` (Grad, im Uhrzeigersinn), `scale`, `arm` (nur Hände), `show` (0 = unsichtbar; mit `ease: "back"` von 0 auf 1 ploppt es auf), `progress` (je Gegenstand, siehe unten), `shape` (Hände), `variant` (Farbe oder Modus). Die Zeichenreihenfolge folgt der Liste: Spätere Spuren liegen oben.

**Hände** (`shape`): `open`, `fist`, `point`, `thumbs_up`, `peace`, `hold`, `side` (Handkante zum Betrachter, nur ein Finger und die Daumenspitze sichtbar) sowie die **Griffe** `grip` und `grip_behind`.

**Greifen (`grip`, `grip_behind`):** Die Hand wird in zwei Ebenen gezeichnet. Handrücken bzw. Handfläche liegen **hinter** dem Gegenstand, die Finger laufen **vorne** darum herum. Dafür: Hand-Spur mit `name` **zuerst** in die Liste, den Gegenstand mit `attach_to` auf die Hand bei `x: 0, y: -34` (Griffmitte; tiefer, z. B. `y: -54`, greift die Hand weiter unten). Bei `grip` liegen drei Finger und der Daumen vorne. Bei `grip_behind` ist nur der Daumen vorne zu sehen, die Finger bleiben verdeckt.

**Nicht immer alle Finger zeigen:** Je nach Blickwinkel sind Finger verdeckt, durch den Gegenstand (`grip_behind`) oder durch die Hand selbst (`side`). Die Form passend zur Blickrichtung wählen, statt immer die ganze Hand zu zeigen.

Klassische Formen: Klassische Cartoon-Handschuhe: **drei pummelige Finger und ein Daumen**, runde Handfläche, kleine ausgestellte Stulpe mit Falten, etwa 90 px hoch bei `scale` 1 (in Szenen mit Gegenständen oft 0,85).
- `variant`: `filled` (Standard, weißer Handschuh mit dünnen schwarzen Innenlinien) oder `outline` (weiße Kontur auf Schwarz wie die Handschuhe im Original)
- `variant: "sprite"`: **handgezeichnete Hände** aus `animations/assets/hands/*.png` (ausgeschnitten mit `scripts/extract_hand_sprites.py` aus einer eigenen Zeichnung). Fehlt die Zeichnung für eine Form, wird die programmierte Hand verwendet. Zusätzliche Form `rock` (Zeigefinger und kleiner Finger).
- `arm`: optionaler Gummischlauch-Arm. Bei gezeichneten Händen (`sprite`) läuft er als Kurve von der Stulpe zu einem festen Schulterpunkt unterhalb des Bildrands (Wert = Reichweite, z. B. 220). So liest sich die Stulpe auch bei gedrehter Hand als Handgelenk und nicht als loser Finger.

**Gegenstände:**

| `type` | `progress` | `variant` | Größe bei scale 1 |
|---|---|---|---|
| `water_glass` | Wasserstand 0–1 (Oberfläche bleibt beim Kippen waagerecht) | – | 52 × 70 |
| `bottle` | Füllstand 0–1 (Oberfläche waagerecht). Öffnung bei lokal (0, −64) | Etikettfarbe | 40 × 110 |
| `water_stream` | 0–1 Strahl wächst nach unten, 1–2 Ende fällt ab. Immer senkrecht, auch angehängt | – | 100 lang |
| `straw` | wie weit das Getränk im Halm hochgestiegen ist (0–1) | Streifenfarbe | Knick-Strohhalm, Fuß bei (0, 0), Spitze bei (−30, −86). Mit `attach_to` ins Glas hängen (`x: 8, y: 18`) und **vor** dem Glas in die Liste, dann liegt er im Glas |
| `water_drop` | – | Farbe | 24 × 32 |
| `fireworks` | 0–0,35 Rakete steigt, 0,35–1 Explosion und Verblassen | `gold`, `pink`, `blue`, `green`, `purple`, `mix` | Ø 150 |
| `book` | offen: jede ganze Zahl = eine Seite umgeblättert | `open` (Standard), `closed` | 124 × 66 |
| `checklist` | 0–3 Häkchen nacheinander | – | 68 × 92 |
| `coffee` | – (Dampf bewegt sich von selbst) | – | 66 × 90 |
| `heart` | – | Farbe | 60 × 55 |
| `sparkle` | – | Farbe | 44 × 44 |
| `star` | – | – | 76 × 72 |
| `trophy` | – | – | 76 × 74 |
| `clock` | Minutenzeiger (1 = eine Umdrehung) | – | 80 × 90 |
| `zzz` | – (steigt von selbst) | – | 60 × 90 |

**Gießen:** `water_stream` mit `attach_to` an die Flasche hängen (`x: 0, y: -66`), Flasche um ca. −115° kippen, Strahl und Füllstände zeitlich koppeln (Beispiel `refill_water`).

Tipp: `show` von 0 auf 1 mit `ease: "back"` = Aufploppen. Eine Spur vor ihrem Auftritt mit `show: 0` verstecken, sonst ist sie ab 0 s sichtbar (bei `fireworks` stünde die Rakete schon unten bereit).
