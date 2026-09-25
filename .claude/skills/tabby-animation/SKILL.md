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
- Budget: Loops `max_kb` ≤ 80 (mit Teilen ≤ 100), Ereignisse ≤ 150, mit Händen oder Gegenständen ≤ 200. `max_colors` 8–16. Wird es zu groß: weniger dauernde Bewegung (Winken, Hüpfen), kürzere Effekte, weniger Farben.

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
| `tears` | 0 | 0…1 | Tränen (laufen von selbst); mit `eye_shape: "sad"` und `mouth_curve` < 0 |
| `sweat` | 0 | 0…1 | Schweißtropfen: Stress, Verlegenheit, Anstrengung |
| `eye_shape` | `pill` | siehe unten | wechselt am Keyframe (kein Überblenden) |
| `face_x` / `face_y` | 0 | −150…150 / −60…40 | ganzes Gesicht verschieben, um Platz für Gegenstände zu machen |
| `face_scale` | 1 | 0,6…1,1 | kleiner, wenn Gegenstände viel Platz brauchen |
| `turn` | 0 | −1…1 | Kopf zur Seite drehen (− = nach links), für „schaut zur Liste/zum Glas“; 0,4–0,7 wirkt natürlich |

**Augenformen** (`eye_shape`): `pill` (normal), `happy` (^ ^ Freude), `closed` (Strich, Genuss, Schlaf), `angry` (innen tief), `sad` (außen tief), `squint` (> < Anstrengung, Lachen, Niesen), `heart` (verliebt), `star` (begeistert), `dizzy` (Spiralen, schwindelig). Wechsel wirken am natürlichsten während eines Blinzelns oder einer schnellen Bewegung.

## Hände und Gegenstände (`props`)

Vollständige Referenz: `tools/anim/README.md` → „Hände und Gegenstände“. Den Katalog aller Teile erzeugst du mit `python -m tabby_anim catalog --out ../../dist/catalog.png`. Sieh ihn dir an, bevor du Teile auswählst.

- **Hände** `type: "hand"`, `side` left/right, `shape`: `open`, `fist`, `point`, `thumbs_up`, `peace`, `hold`, `side`, `grip`, `grip_behind`. Klassische weiße Cartoon-Handschuhe mit drei Fingern und Daumen, ca. 90 px hoch; in Szenen mit Gegenständen `scale` 0,8–0,9. `variant: "outline"` für den Umriss-Stil des Originals, `arm` (px) für einen Gummischlauch-Arm.
- **Gegenstände**: `water_glass`, `bottle`, `water_stream`, `water_drop`, `fireworks`, `book`, `checklist`, `coffee`, `heart`, `sparkle`, `star`, `trophy`, `clock`, `zzz` (Bedeutung von `progress` und `variant` in der README)
- Keyframe-Felder flach: `t`, `ease`, `x`, `y`, `rot`, `scale`, `show`, `progress`, `shape`, `variant`, `arm`
- **Umgreifen (bevorzugt für Glas, Flasche, Tasse):** `shape: "grip"`. Die Hand kommt **zuerst** in die Liste (mit `name`), der Gegenstand danach mit `attach_to` auf die Hand bei `x: 0, y: -34` (tiefer, z. B. `-54`, greift weiter unten; dann bleibt der Füllstand sichtbar). Das Rig legt die Handfläche automatisch hinter und die Finger vor den Gegenstand. Soll ein Gegenstand eine Hand bewegen (Flasche wird gekippt), bewegt man die **Hand** und hängt den Gegenstand daran (Beispiel `refill_water`).
- **Ohne Hände (Stil der Original-Taby-Clips):** Gegenstände dürfen allein schweben, z. B. ein Glas, das sich an den Mund legt (`drink_float`), oder ein Glas mit `straw`, dessen Spitze am Mund liegt (`drink_straw`). Positionen aus `rig.face_layout(...)` berechnen, damit Glasrand bzw. Halmspitze genau am Mund sitzen. Oft die ruhigere Lösung als eine Hand.
- **Finger weglassen, wo sie verdeckt wären:** von hinten gehalten → `grip_behind` (nur der Daumen vorne); Handkante zum Betrachter → `side`. Zeig nicht immer die ganze Hand, sondern das, was man aus diesem Blickwinkel sähe.
- **Auflegen/Tragen ohne Umgreifen:** `hold`, Gegenstand vor der Hand in der Liste.
- **Auftritt**: `show` 0 → 1 mit `ease: "back"`; vorher `show: 0` setzen. Abgang: aus dem Bild fahren (`y` > 300) oder `show` → 0.

**Das Gesicht ist beweglich.** Es muss nicht in der Mitte bleiben: Liegt der Gegenstand links, rückt das Gesicht nach rechts (`face_x` 100–135, `face_scale` 0,7–0,8) und dreht sich zum Gegenstand (`turn` −0,5 bis −0,7). Zum Abschluss dreht es sich wieder nach vorn (`turn` 0) und kehrt zur Mitte zurück, weil die Firmware danach in den Idle-Zustand geht (Beispiel `checklist_done`, `refill_water`).

**Vollständige Abläufe statt Andeutungen.** Zeig die Handlung ganz: ein Glas wird **wirklich leer getrunken** (Füllstand 1 → 0, Glas kippt dabei immer weiter, weil das Wasser waagerecht bleibt), eine **Flasche gießt** das Glas voll (`bottle` + `water_stream`), alle drei Häkchen werden gesetzt. Ursache und Wirkung zeitlich koppeln (Strahl läuft genau, solange der Pegel steigt).

**Bildaufbau mit Teilen:** Das Gesicht füllt ohne Verschiebung die Fläche (Augen x ≈ 76–148 und 312–385, y ≈ 71–195, Mund y ≈ 195). Hände gehören in die unteren Ecken (y 230–260) oder kommen von unten ins Bild. Gegenstände dürfen Mund oder Augenunterkante überdecken, aber nie beide Augen. Hintergrund-Effekte (Feuerwerk) mit `layer: "back"` in die oberen Ecken. Achte darauf, dass eine Hand nicht den wichtigen Teil eines gehaltenen Gegenstands verdeckt (z. B. den Wasserstand).

Das Rig kann **nicht**: Text, Körper oder Arme, freie Formen außerhalb des Katalogs. Neue Teile = neue Zeichenfunktion in `props.py`/`hands.py` plus Eintrag in README und Katalog.

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

Gute Vorlagen in `animations/src/`:
- nur Gesicht: `blink_idle_loop` (Loop, Blick, Blinzeln), `happy_bounce` (Antizipation, Sprung, Squash, Wangen), `sleepy_yawn` (langsames Timing), `sneeze`, `crying_loop` (Tränen, Zittern)
- mit Teilen: `drink_water_sip` (Hand hält Glas per `attach_to`, wird von voll bis leer getrunken), `refill_water` (Flasche gießt mit Strahl ins Glas, Gesicht rückt zur Seite und schaut zu), `fireworks_celebrate` (Hintergrund-Effekte, Sternenaugen, winkende Hände), `reading_loop` (Buch mit zwei Händen, Seite blättert), `checklist_done` (Liste links, Gesicht rechts und seitlich gedreht, Zeigefinger tippt jede Zeile, Daumen hoch), `in_love_loop` (Herzaugen, aufsteigende Herzen nahtlos im Loop)

## Grenzen und Lizenz

Die Taby-Figur ist nur privat nutzbar (Guardrail L2 in `docs/KONZEPT.md`). Erzeugte Clips nicht veröffentlichen oder verkaufen.
