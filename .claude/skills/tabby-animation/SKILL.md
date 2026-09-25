---
name: tabby-animation
description: Create or change Tabby face animations in the upstream Taby style. Three cases, (1) a new clip from a description ("Tabby niest") via keyframes for the procedural face rig, (2) changing one of our own clips in animations/src/, (3) changing or remixing one of the 84 original Taby clips (trim, speed, loop, recolor, add props) via edit.json. Builds the firmware GIF, reviews a contact sheet, iterates and checks the storage budget. Use whenever the user wants a new Tabby animation, expression, reaction or mood clip, or wants to change an existing one, including originals like drink_water or task_completed.
argument-hint: "<Beschreibung, z. B. „Tabby niest“ oder „drink_water mit Saft statt Wasser“>"
---

# Tabby-Animationen erstellen und verändern

Hintergrund und Stilguide: `docs/spec/animationen.md`. Vollständige Referenz: `tools/anim/README.md`.
Alle Befehle laufen in `tools/anim/` (vorher einmal `pip install -q -r requirements.txt`).

## 0. Welcher Fall?

| Der Nutzer will … | Fall | Quelle in `animations/src/<id>/` |
|---|---|---|
| etwas **Neues** („Tabby ist stolz“, „Tabby trinkt Kaffee“) | **A: neu mit dem Rig** | `keyframes.json` |
| einen **eigenen** Clip ändern (steht schon in `animations/src/`) | **B: eigenen Clip ändern** | vorhandene `keyframes.json` bzw. `edit.json` bearbeiten |
| ein **Original** ändern (`drink_water`, `task_completed`, `wow` …) oder daraus etwas Neues machen | **C: Original bearbeiten** | `edit.json` |

Unklar, ob ein Name ein Original ist? `python -m tabby_anim originals list` zeigt alle 84 mit Länge, Loop und Größe. Ist das Gewünschte eine Mischung (Original + neue Bewegung), ist es Fall C mit `overlay`. Muss das Gesicht selbst sich anders bewegen als im Original, geht das nicht per `edit.json` (die Pixel des Originals sind fest). Dann baue es als Fall A nach und nimm das Original als Vorlage fürs Timing.

**Originale bleiben unangetastet.** Eine Änderung erzeugt immer einen **neuen Clip mit eigener ID** (z. B. `drink_juice` aus `drink_water`). Das Original bleibt auf dem Gerät.

## Ablauf (alle Fälle)

1. **Verstehen.** Nimm die Beschreibung aus den Argumenten. Frag nur nach, wenn Wesentliches fehlt, sonst entscheide selbst:
   - **Loop oder einmalig?** Zustände (wartet, arbeitet, schläft) → Loop. Ereignisse (freut sich, niest, erschrickt) → einmalig.
   - **Länge:** Loops 1,5–3 s, Ereignisse 1,5–4 s (Remixe von Originalen dürfen länger sein, max. 12 s).
   - **ID:** kurz, englisch, `a-z0-9_`, z. B. `sneeze`, `proud_loop`. Loops enden auf `_loop`. Sie darf weder in `animations/src/` noch unter den Originalen vorkommen.
2. **Ansehen, was es schon gibt.**
   - Fall B: die vorhandene Quelle lesen und den aktuellen Kontaktbogen erzeugen (`preview`, siehe unten).
   - Fall C: `python -m tabby_anim originals show <original>` erzeugt `dist/originals/<original>.sheet.png` mit Zeitstempeln. Mit Read ansehen, bevor du Zeiten festlegst. Für mehr Bilder in einem Abschnitt: `--count 24`. Farben für `recolor`: `python -m tabby_anim originals colors <original>`.
3. **Planen.** Schreib dir 3–6 Schlüsselposen bzw. Schnittpunkte mit Zeitpunkt auf, bevor du JSON schreibst.
4. **Schreiben.** `meta.json` plus `keyframes.json` (Fall A/B) oder `edit.json` (Fall C).
5. **Bauen und prüfen:**
   ```sh
   python -m tabby_anim build ../../animations/src/<id> --out ../../dist/animations
   python -m tabby_anim preview ../../animations/src/<id> --out ../../dist/animations/<id>.sheet.png --count 12
   ```
   Der Build meldet Frames, Farben und KB. Schlägt er fehl (Budget, unbekannter Parameter), behebe die Ursache.
6. **Selbst ansehen.** Öffne den Kontaktbogen mit Read und prüfe ihn ehrlich gegen die Checkliste unten. Bessere nach und baue neu, bis sie erfüllt ist (meist 1–3 Runden).
7. **Zeigen.** Schicke dem Nutzer Kontaktbogen und GIF (`dist/animations/<id>.gif`) und beschreibe in 2–3 Sätzen, was passiert bzw. was sich gegenüber vorher geändert hat. Das GIF liegt im Gerätespeicherformat vor, ist also um 90° gedreht. Der Kontaktbogen zeigt die richtige Ansicht.
8. **Speicher prüfen.** `python -m tabby_anim build ../../animations/src --out ../../dist/animations` gibt am Ende die Summe aller eigenen Clips aus. Auf dem Gerät sind neben den 84 Originalen nur **etwa 1,2 MB** frei. Liegt die Summe darüber, sag das dem Nutzer deutlich. Es passen dann nicht alle eigenen Clips gleichzeitig aufs Gerät: Er muss auswählen, oder Clips müssen kleiner werden. Lösch nie selbst etwas.
9. **Abschließen.** Tests laufen lassen (`python -m unittest discover -s tests`) und `animations/src/<id>/` committen. `dist/` wird nicht committet (steht in .gitignore).

## Fall C: Original bearbeiten (`edit.json`)

Die Originale liegen nicht im Repo. Beim ersten Aufruf holt das Werkzeug sie aus dem Upstream-Repo `TRIIIS-LABS/firmware-taby` in einen Cache (`~/.cache/tabby_anim`) und prüft jede Datei gegen die sha256 im Upstream-Katalog. `TABBY_ORIGINALS=<pfad>/assets/amoled-1.64` nutzt stattdessen eine vorhandene Kopie.

```json
{
  "base": "drink_water",
  "loop": false,
  "ops": [
    { "op": "trim", "end_s": 5.2 },
    { "op": "recolor", "from": "#0097cb", "to": "#e0780a", "tolerance": 60 },
    { "op": "overlay", "from_s": 3.7, "props": [ { "type": "sparkle", "keyframes": [
        { "t": 0, "x": 330, "y": 70, "show": 0, "variant": "gold" }, { "t": 0.35, "show": 1, "ease": "back" } ] } ] }
  ]
}
```

- `base`: ID des Originals. `loop` (optional) überschreibt, ob der Clip in Schleife läuft; Standard ist die Einstellung des Originals.
- `ops` laufen **der Reihe nach** auf 24-fps-Bildern. Zeiten beziehen sich immer auf den Stand **nach** den vorigen Operationen. Nach einem `trim` ab 1 s ist die alte Sekunde 2 also die neue Sekunde 1. Deshalb erst schneiden, dann Tempo, dann Bild-Operationen.

| `op` | Felder | Wirkung |
|---|---|---|
| `trim` | `start_s`, `end_s` | Ausschnitt behalten |
| `speed` | `factor` 0,25–4 | > 1 schneller, < 1 langsamer (Bilder werden wiederholt, nicht überblendet) |
| `reverse` | – | rückwärts |
| `pingpong` | – | vorwärts, dann rückwärts; macht aus einer Bewegung einen nahtlosen Loop |
| `hold` | `at_s`, `duration_s` | Bild bei `at_s` stehen lassen (Pause, Pointe) |
| `repeat` | `times` | Clip mehrfach hintereinander |
| `concat` | `base`, `start_s`, `end_s` | Ausschnitt eines anderen Originals anhängen (Intro + Loop verbinden) |
| `recolor` | `from`, `to` (`#rrggbb`), `tolerance` (Standard 40), `from_s`, `to_s` | Farbe tauschen, inklusive geglätteter Kanten; Weiß und Schwarz bleiben |
| `move` | `x`, `y`, `scale`, `from_s`, `to_s` | ganzes Bild verschieben/skalieren, um Platz für Gegenstände zu schaffen |
| `erase` | `rect` [x0, y0, x1, y1], `from_s`, `to_s` | Bereich schwarz machen, etwa um ein Detail zu entfernen |
| `overlay` | `props`, `from_s`, `to_s` | Hände und Gegenstände des Rigs darüberlegen (gleiche Spuren wie in `keyframes.json`; `t` zählt ab `from_s`). Es wird **kein zweites Gesicht** gezeichnet. |

Tipps für Fall C:
- **Farben:** Die Originale haben wenige, klare Farben. `originals colors` listet sie. Für stimmige Varianten auch die hellere Nebenfarbe mitändern (in `drink_water`: `#0097cb` und `#00cafd`).
- **Gegenstände platzieren:** Aus dem Kontaktbogen des Originals ablesen, wo Platz ist (Bild 456 × 280, Ursprung oben links), damit nichts über Augen oder Mund liegt. Schwarz im Overlay ist durchsichtig: Schwarze Linien innerhalb eines Gegenstands verschwinden über hellem Hintergrund.
- **Schnitte an ruhigen Stellen:** Schneide dort, wo sich wenig bewegt (Augen offen, neutral), sonst springt es. Bei Loops müssen erstes und letztes Bild zusammenpassen: im Kontaktbogen prüfen oder `pingpong` nutzen.
- **Größe:** Originale sind oft groß (Median 80 KB, einige > 200 KB). Kürzen ist der wirksamste Hebel, `max_kb` in `meta.json` passend setzen (≤ 200).
- Soll das Gesicht im Original etwas **anderes tun** (anderer Mund, andere Augen), ist das mit `edit.json` nicht sauber möglich. Dann Fall A: mit dem Rig nachbauen.

## Fall A und B: Face-Rig (`keyframes.json`)

Du malst keine Pixel. Das Rig (`tools/anim/tabby_anim/rig.py`) zeichnet Augen, Mund und Wangen mit den Maßen, die aus den Originalen vermessen wurden. Deine Aufgabe sind **Timing und Ausdruck**. Bei Fall B nur ändern, was verlangt ist, und den Rest der Keyframes stehen lassen. `prompt` in `meta.json` um die Änderung ergänzen.

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
| `mouth_o` | 0 | 0 / 12…16 | runder „O“-Mund (Radius, saugen, staunen); > 1 ersetzt den normalen Mund |
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
- **Gegenstände**: `water_glass`, `straw`, `bottle`, `water_stream`, `water_drop`, `fireworks`, `book`, `checklist`, `coffee`, `heart`, `sparkle`, `star`, `trophy`, `clock`, `zzz` (Bedeutung von `progress` und `variant` in der README)
- Keyframe-Felder flach: `t`, `ease`, `x`, `y`, `rot`, `scale`, `show`, `progress`, `shape`, `variant`, `arm`
- **Umgreifen (bevorzugt für Glas, Flasche, Tasse):** `shape: "grip"`. Die Hand kommt **zuerst** in die Liste (mit `name`), der Gegenstand danach mit `attach_to` auf die Hand bei `x: 0, y: -34` (tiefer, z. B. `-54`, greift weiter unten; dann bleibt der Füllstand sichtbar). Das Rig legt die Handfläche automatisch hinter und die Finger vor den Gegenstand. Soll ein Gegenstand eine Hand bewegen (Flasche wird gekippt), bewegt man die **Hand** und hängt den Gegenstand daran (Beispiel `refill_water`).
- **Ohne Hände (Stil der Original-Taby-Clips):** Gegenstände dürfen allein schweben, z. B. ein Glas mit `straw`, dessen Spitze am Mund liegt (`drink_straw`, **Standard fürs Trinken**), oder ein Glas, das sich allein an den Mund legt und kippt. Positionen aus `rig.face_layout(...)` berechnen, damit Glasrand bzw. Halmspitze genau am Mund sitzen. Beim Saugen `mouth_o` 13–15 setzen und die Halmspitze auf `rig.mouth_center(pose)` legen: Die Lippen werden dann über den Halm gezeichnet, er steckt im Mund. Oft die ruhigere Lösung als eine Hand.
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
- [ ] Fall C: Schnitte springen nicht, Overlays verdecken weder Augen noch Mund, umgefärbte Kanten haben keine Reste der alten Farbe.

## Beispiele

Gute Vorlagen in `animations/src/`:
- nur Gesicht: `blink_idle_loop` (Loop, Blick, Blinzeln), `happy_bounce` (Antizipation, Sprung, Squash, Wangen), `sleepy_yawn` (langsames Timing), `sneeze`, `crying_loop` (Tränen, Zittern)
- mit Teilen: `drink_straw` (Glas mit Strohhalm schwebt unter den Mund, Getränk steigt im Halm, O-Mund umschließt die Spitze, Pegel sinkt), `refill_water` (Flasche gießt mit Strahl ins Glas, Gesicht rückt zur Seite und schaut zu), `fireworks_celebrate` (Hintergrund-Effekte, Sternenaugen, winkende Hände), `reading_loop` (Buch mit zwei Händen, Seite blättert), `checklist_done` (Liste links, Gesicht rechts und seitlich gedreht, Zeigefinger tippt jede Zeile, Daumen hoch), `in_love_loop` (Herzaugen, aufsteigende Herzen nahtlos im Loop)

- Original bearbeitet (Fall C): `drink_juice` (`drink_water` gekürzt, Wasser zu Orangensaft umgefärbt, goldenes Funkeln per `overlay`)

## Grenzen und Lizenz

Die Taby-Figur ist nur privat nutzbar (Guardrail L2 in `docs/KONZEPT.md`). Erzeugte Clips nicht veröffentlichen oder verkaufen.
