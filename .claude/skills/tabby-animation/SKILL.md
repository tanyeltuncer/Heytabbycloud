---
name: tabby-animation
description: Create a new Tabby face animation in the upstream Taby style from a short description (e.g. "Tabby niest", "Tabby ist stolz"). Writes keyframes for the procedural face rig in tools/anim, builds the firmware GIF, reviews a contact sheet and iterates. Use when the user asks for a new Tabby animation, expression, reaction or mood clip, or wants to change an existing one in animations/src/.
argument-hint: "<Beschreibung der Animation>"
---

# Tabby-Animation erstellen

Du erzeugst eine Animation für das Tabby-Gesicht, indem du **Keyframes für das Gesichts-Rig** schreibst.
Du malst keine Pixel: Das Rig (`tools/anim/tabby_anim/rig.py`) zeichnet Augen, Mund und Wangen mit den Maßen, die aus den Original-Animationen vermessen wurden. Deine Aufgabe sind **Timing und Ausdruck**.

Hintergrund und Stilguide: `docs/spec/animationen.md`. Parameter-Referenz: `tools/anim/README.md`.

## Ablauf

1. **Verstehen.** Nimm die Beschreibung aus den Argumenten. Kläre nur, wenn Wesentliches fehlt; sonst entscheide selbst:
   - **Loop oder einmalig?** Zustände (wartet, arbeitet, schläft) → Loop. Ereignisse (freut sich, niest, erschrickt) → einmalig.
   - **Länge:** Loops 1,5–3 s, Ereignisse 1,5–4 s.
   - **ID:** kurz, englisch, `a-z0-9_`, z. B. `sneeze`, `proud_loop`. Loops enden auf `_loop`. Prüfe, dass `animations/src/<id>/` noch nicht existiert.

2. **Planen.** Schreib dir 3–6 Schlüsselposen mit Zeitpunkt auf, bevor du JSON schreibst, etwa: Ausgangslage → Antizipation → Aktion → Überschwingen → Ruhe.

3. **Schreiben.** Lege `animations/src/<id>/meta.json` und `keyframes.json` an (Format unten).

4. **Bauen und prüfen** (aus `tools/anim/`):
   ```sh
   pip install -q -r requirements.txt   # falls Pillow fehlt
   python -m tabby_anim build ../../animations/src/<id> --out ../../dist/animations
   python -m tabby_anim preview ../../animations/src/<id> --out ../../dist/animations/<id>.sheet.png --count 12
   ```
   Der Build meldet Frames, Farben und KB. Schlägt er fehl (Budget, unbekannter Parameter), behebe die Ursache.

5. **Selbst ansehen.** Öffne den Kontaktbogen mit dem Read-Tool und bewerte ihn ehrlich gegen die Checkliste unten. Bessere nach und baue neu, bis sie erfüllt ist (meist 1–3 Runden).

6. **Zeigen.** Schicke dem Nutzer den Kontaktbogen und das GIF (`dist/animations/<id>.gif`) und beschreibe in 2–3 Sätzen, was passiert. Hinweis: Das GIF ist im Gerätespeicherformat abgelegt, also um 90° gedreht; der Kontaktbogen zeigt die richtige Ansicht.

7. **Abschließen.** Tests laufen lassen (`python -m unittest discover -s tests`) und `animations/src/<id>/` committen. `dist/` ist ignoriert und wird nicht committet.

## Dateiformat

`meta.json`:
```json
{ "id": "sneeze", "label": "HATSCHI", "max_colors": 12, "max_kb": 120,
  "prompt": "<die Beschreibung des Nutzers, wörtlich>" }
```
- `label`: max. 12 Zeichen, Großbuchstaben, erscheint, falls das Gerät den Clip nicht hat
- Budget: Loops `max_kb` ≤ 80, Ereignisse ≤ 150. `max_colors` 8–16.

`keyframes.json`:
```json
{
  "duration_s": 2.0,
  "loop": false,
  "keyframes": [
    { "t": 0.0, "pose": { "eye_open": 1, "mouth_curve": 12 } },
    { "t": 0.4, "pose": { "squash": 1.15, "bounce": 8 }, "ease": "out" }
  ]
}
```
- Nicht gesetzte Parameter übernehmen den vorigen Wert. Unbekannte Parameter brechen den Build ab.
- `ease` gilt für den Weg **zu** diesem Keyframe: `inOut` (Standard), `in`, `out`, `back` (Überschwingen), `linear`, `hold` (springt am Ende).
- Bei Loops muss der letzte Keyframe dieselbe Pose haben wie der erste (bei `t = duration_s`), sonst springt der Übergang.

## Parameter und sinnvolle Bereiche

| Parameter | neutral | Bereich | Wirkung und Tipps |
|---|---|---|---|
| `look_x` / `look_y` | 0 | −20…20 / −12…12 | Blick; ganze Pixel. Mund folgt zu 60 %. |
| `bounce` | 0 | −40…15 | ganzes Gesicht hoch (−) / runter (+); Sprung ≈ −30 |
| `eye_open` | 1 | 0…1 | Blinzeln: 1 → 0,08 in ~0,1 s (`in`), zurück in ~0,12 s (`out`); müde 0,3–0,5 |
| `eye_scale` | 1 | 0,7…1,3 | groß = Staunen/Schreck, klein = skeptisch |
| `squash` | 1 | 0,8…1,25 | Stauchen beim Aufkommen (>1), Strecken im Sprung (<1) |
| `happy` | 0 | 0 / 1 | ≥ 0,5 schaltet auf „^ ^“-Augen (kein Übergang, setze es genau auf 0 oder 1) |
| `mouth_curve` | 12 | −14…18 | Lächeln +, traurig −, neutral 0 |
| `mouth_width` | 94 | 50…110 | schmal bei offenem Mund (60–70) |
| `mouth_open` | 0 | 0 / 10…32 | offener Mund; > 1 zählt als offen |
| `blush` | 0 | 0…1 | Wangen; für Freude, Verlegenheit, Liebe |

Das Rig kann (noch) **nicht**: Hände, Requisiten, `> <`-Augen, Herzen, Tränen, Schweißtropfen, Text. Verlangt die Beschreibung so etwas, setze sie mit Gesichtsausdruck und Bewegung um und sag dem Nutzer offen, was fehlt (Ausbau: neue Zeichenfunktion in `rig.py`).

## Stilregeln (Original-Look)

- **Antizipation:** vor großen Bewegungen kurz in die Gegenrichtung (vor dem Sprung runter und stauchen).
- **Überschwingen:** beim Ankommen `ease: "back"` oder eine kleine Gegenbewegung. Achtung: `back` lässt **alle** Parameter überschwingen, die sich in diesem Keyframe ändern. Nutze es nur an Keyframes, die wenige Parameter ändern, typischerweise `bounce`/`squash`. Ändern sich dort auch `eye_scale` oder `squash` < 1, werden die Augen unschön lang. Dann lieber `out`.
- **Timing:** schnelle Aktionen 0,1–0,3 s, Halten/Nachwirken 0,4–1 s. Nicht alles gleich schnell.
- **Squash & Stretch** mit Maß: 0,85–1,2 wirkt lebendig, mehr wirkt kaputt.
- **Ruhe am Ende:** Ereignisse enden in einer ruhigen, freundlichen Pose (nahe neutral), weil die Firmware danach zurück in den Idle-Zustand geht.
- **Ein klarer Gedanke pro Clip.** Lieber zwei Clips (`_in` + `_loop`) als einer, der alles will.

## Checkliste für den Kontaktbogen

- [ ] Die Emotion ist ohne Erklärung erkennbar.
- [ ] Antizipation und Ruhe am Ende sind sichtbar, es gibt keine abrupten Sprünge zwischen Nachbarbildern (außer bewusst `hold`).
- [ ] Das Gesicht bleibt im Bild (Augen und Mund nicht am Rand abgeschnitten).
- [ ] Bei Loops passt das letzte Bild zum ersten.
- [ ] Der Build liegt im Budget (KB, Farben).

## Beispiele

Gute Vorlagen im Repo: `animations/src/blink_idle_loop` (Loop, Blick und Blinzeln), `happy_bounce` (Ereignis mit Antizipation, Sprung, Squash, Überschwingen, Wangen) und `sleepy_yawn` (langsames Timing, offener Mund).

## Grenzen und Lizenz

Die Taby-Figur ist nur privat nutzbar (Guardrail L2 in `docs/KONZEPT.md`). Erzeugte Clips nicht veröffentlichen oder verkaufen.
