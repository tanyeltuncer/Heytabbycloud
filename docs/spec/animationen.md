# Spec: Eigene Animationen

Ziel: neue Animationen im **gleichen Stil und in der gleichen Qualität** wie die 84 Originale, die ohne Firmware-Hack auf Tabby laufen.

---

## 1. Was die Originale technisch sind (gemessen)

Analysiert am Asset-Pack `assets/amoled-1.64` (Version 0.3.3) der Upstream-Firmware:

| Eigenschaft | Messwert | Bedeutung für uns |
|---|---|---|
| Format | **GIF**, Palettenmodus (`P`) | Die Firmware spielt GIFs mit dem LVGL-Decoder `lv_gif` (LVGL 8.3.11). Andere Formate gehen nicht ohne Firmware-Änderung. |
| Dateigröße (Pixel) | **280 × 456** (alle 84) | exakt die Displaygröße |
| Ausrichtung | **Inhalt um 90° gedreht** gespeichert | Man zeichnet **quer (456 × 280)** und dreht beim Export um **90° im Uhrzeigersinn**. |
| Hintergrund | **reines Schwarz `#000000`** (75 von 84) | AMOLED: Schwarz = Pixel aus. Das spart Strom und lässt die Figur „schweben“. |
| Farben pro Bild | Median **8**, Figur meist nur Schwarz, Weiß und Grautöne für die Kanten | flacher Vektor-Look mit wenigen Akzentfarben |
| Bildrate | Frame-Delays **40 ms und alle 6 Frames 50 ms** | **24 fps** Quelle (6 Frames = 250 ms). GIF kennt nur Hundertstelsekunden, daher dieses Muster. |
| Länge | Median **61 Frames** (~2,5 s), max. 310 | Loops kurz (1,5–3 s), Einzelaktionen 3–8 s |
| Dateigröße | Median **80 KB**, max. 485 KB (`f1_car`) | großes Budget-Thema, siehe §5 |
| Frame-Disposal | fast überall `1` (Bild stehen lassen) | Es werden nur die geänderten Bereiche gespeichert (Delta-Optimierung). |
| Metadaten | keine Werkzeug-Signatur, 3 Dateien mit `ImageMagick`-Block | Die Endkonvertierung lief mindestens teilweise über ImageMagick. |
| Abspielmodi | 53× `play_once`, 31× `loop`; Ketten wie `working_in>working_loop` | Intro-Clip plus Loop-Clip ist das übliche Muster. |

## 2. Welche Werkzeuge wurden genutzt?

**Das ist nicht dokumentiert.** Upstream schreibt ausdrücklich, dass die *„private editing projects“* nicht veröffentlicht wurden. Die GIFs enthalten keine Autoren-Software-Kennung, nur bei 3 Dateien den Konverter ImageMagick.

Was man aus den Merkmalen **ableiten** kann (Indizien, keine Gewissheit):
- **24-fps-Timeline, weiche Easing-Kurven, Squash & Stretch, saubere Vektorkanten mit Kantenglättung** → typisch für ein **Vektor-Animationsprogramm** mit Keyframes, z. B. After Effects (Shape Layers), Adobe Animate, Rive, Jitter/Figma-Motion oder Toon Boom.
- Einige Clips wirken **gezeichnet** (Boxhandschuhe mit Glanzlichtern, „Rubber-Hose“-Handschuhhände) → eventuell zusätzlich Frame-by-Frame-Zeichnung.
- Ablauf vermutlich: **Animation → Video oder PNG-Sequenz → Drehen, Palette reduzieren, GIF optimieren** (ImageMagick/gifsicle).

Für uns reicht das: Wir brauchen nicht dasselbe Programm, sondern **dieselben Regeln** (Stilguide §3) und **dieselbe Export-Pipeline** (§4).

## 3. Stilguide „Tabby-Look“

Abgeleitet aus den Originalen:

**Figur**
- Das Gesicht besteht aus **zwei weißen, abgerundeten Rechteck-Augen** und einem **dünnen Mund-Strich**. Emotionen entstehen durch Form (Augen zu Bögen, `>` `<`, Klammern), nicht durch Details.
- Hände sind **weiße Outline-Handschuhe** (Cartoon-Stil der 1930er), kein Körper.
- Requisiten sind flache Formen mit **1 Grundfarbe, 1 Schatten- und 1 Glanzton** (z. B. rote Boxhandschuhe, goldene Medaille, blaues Glas).

**Farben**
- Hintergrund immer `#000000`
- Figur `#FFFFFF`, Kantenglättung in Grautönen
- Akzente sparsam: Rot/Orange (Energie), Blau (Wasser, Ruhe), Grün (Erfolg), Gelb/Gold (Belohnung), Rosa (Wangen, Liebe)
- **max. 16 Farben pro Clip** (inkl. Graustufen), Ziel 8

**Bewegung**
- 24 fps, **Ease-in/Ease-out** statt linear, **Squash & Stretch** bei Sprüngen und Treffern
- **Antizipation** (kurz ausholen) vor großen Bewegungen, **Overshoot** beim Ankommen
- Loops müssen **nahtlos** sein (erstes Bild = Bild nach dem letzten)
- **Intro/Loop-Paar**: `xyz_in` (play_once, 1–2 s) führt in `xyz_loop` (loop, 1,5–3 s)

**Komposition** (auf der 456 × 280 Querfläche)
- Das Gesicht sitzt mittig, Augen etwa im oberen Drittel, **Rand ≥ 16 px** (Gehäusekante)
- Große, klare Silhouetten: Das Display ist nur 1,64" groß, Details unter ~4 px verschwinden.
- Keine großen weißen Flächen über längere Zeit (Einbrenn-Gefahr, Stromverbrauch)

## 4. Werkzeug-Kette (ohne Installation möglich)

| Schritt | Empfehlung | Alternativen |
|---|---|---|
| **Design** (Figur, Requisiten, Posen) | **Figma** (Browser, kostenlos): Komponenten für Augen, Mund, Hände | Penpot (Open Source, Browser) |
| **Animation** | **Jitter** (Browser, importiert direkt aus Figma, Keyframes + Easing, Export als **PNG-Sequenz/MP4 in eigener Größe und fps**) | Rive (Browser, Bones und State Machines; Exportoptionen vorher prüfen) · After Effects (Profi, Installation) · Procreate Dreams (iPad, Frame-by-Frame) · Blender Grease Pencil (kostenlos, Installation) |
| **Export** | **PNG-Sequenz 456 × 280, 24 fps**, schwarzer Hintergrund (nicht transparent!) | MP4 (H.264, verlustarm), wird von der Pipeline zerlegt |
| **Konvertierung** | **unsere Pipeline im CI** (siehe unten) | – |
| **Vorschau** | Web-App → Simulator (gleiche GIF-Datei) | – |
| **Test am Gerät** | Firmware-Build mit neuem Asset-Pack, per USB im Browser flashen | – |

### Pipeline `tools/anim/` (läuft in GitHub Actions) – ✅ umgesetzt, siehe [tools/anim/README.md](../../tools/anim/README.md)

Eingabe: Ordner `animations/src/<id>/` mit `frames/*.png` oder `clip.mp4` sowie `meta.yml`:

```yaml
id: coffee_break          # a-z, 0-9, _, max. 80 Zeichen
label: COFFEE             # fallback_label (Anzeige, falls der Clip fehlt)
loop: false               # play_once / loop
fps: 24
max_colors: 12
max_kb: 150               # hartes Budget, Build schlägt sonst fehl
```

Schritte:
1. Frames laden (bei MP4 per `ffmpeg` zerlegen), auf **456 × 280** prüfen
2. **90° im Uhrzeigersinn drehen** → 280 × 456
3. Hintergrund auf exakt `#000000` klemmen (Werte < 8 → 0, gegen Rauschen und Einbrennen)
4. **Globale Palette** über alle Frames bilden (max. `max_colors`, Schwarz und Weiß fest reserviert), ohne Dithering, weil der flache Look sonst „grieselt“
5. GIF schreiben mit dem **24-fps-Delay-Muster** `4,4,4,4,4,5` (Hundertstelsekunden), Loop-Flag passend
6. Optimieren: `gifsicle -O3` (Delta-Frames, Disposal 1). **Kein `--lossy`**, das erzeugt Artefakte an den Kanten.
7. Prüfen: Größe ≤ `max_kb`, Frame-Anzahl, Farbzahl, bei Loops erster = letzter + 1
8. Metadaten erzeugen: `duration_ms`, `byte_length`, `sha256` → Eintrag in `catalog.json`, Hashes in `manifest.json` aktualisieren (LF-Zeilenenden, Manifest < 16 KiB)
9. Bei neuer ID: Zeile in `firmware/main/taby_animation_assets.c` generieren (`{"id", "/assets/animations/id.gif", NULL, 0, duration, loop}`)
10. WebP-Vorschau für die Galerie der Web-App erzeugen

Werkzeuge in der Pipeline: Python + Pillow, `ffmpeg`, `gifsicle` (alles im CI-Container, nichts lokal).

## 4b. KI-Generierung

Getestet und bewertet (Stand September 2026):

| Ansatz | Ergebnis im Tabby-Stil | Bewertung |
|---|---|---|
| **A: KI schreibt Keyframes für ein Gesichts-Rig** (umgesetzt in `tools/anim`) | pixelsauber, exakt der Upstream-Look, 50–60 KB pro Clip, perfekte Loops | ✅ **Empfohlen für alle Gesichts- und Emotions-Animationen** |
| B: KI-Videogenerator (Text/Bild → Video) | Raster-Video mit Rauschen, Figur „driftet“ (Augen ändern Form), kein reines Schwarz, Loops schwierig. Mit Nachbearbeitung (Palette, Schwarz-Klemme) brauchbar für Hintergründe und Effekte, aber selten „on model“ | ⚠️ nur für Ideen, Effekte, Requisiten-Skizzen |
| C: KI-Bildgenerator für Requisiten (Tasse, Pokal …) → vektorisieren → im Rig oder in Jitter animieren | gute Requisiten, wenn man im Prompt flach, 3 Farben, schwarzer Hintergrund und dicke Konturen vorgibt | 🟨 sinnvoll als Zuarbeit |

**Warum A so gut funktioniert:** Tabbys Gesicht besteht aus wenigen geometrischen Formen. Das Rig (`tools/anim/tabby_anim/rig.py`) zeichnet sie mit den **aus den Originalen vermessenen Maßen**: Augen 73 × 124 px an x = 112/348, Mund 94 px breit bei y ≈ 195, Blinzeln zur Unterkante hin. Die KI muss nur noch **Timing und Ausdruck** entscheiden, also wenige Zahlen pro Keyframe. Das können Sprachmodelle sehr gut.

**Beispiele im Repo** (`animations/src/`), jeweils aus einem Satz entstanden, der Satz steht im Feld `prompt` in `meta.json`:
- `blink_idle_loop`: „Tabby wartet entspannt, schaut kurz nach links und rechts und blinzelt einmal.“
- `happy_bounce`: „Tabby freut sich riesig über eine erledigte Aufgabe: holt Schwung, hüpft hoch, landet mit Squash und strahlt mit roten Wangen.“
- `sleepy_yawn`: „Tabby wird müde: Augen werden schwer, großes Gähnen, Augen fallen langsam zu.“

**Rundlauf-Test der Pipeline mit Originalen:** GIF zerlegen → Pipeline → GIF. Jedes Bild ist **pixelgenau identisch**, und die Dateien sind mit gifsicle im Schnitt ~14 % kleiner (6 Clips: 883 → 761 KB).

**Teile-Katalog (umgesetzt):**
- **9 Augenformen:** normal, `happy` (^ ^), `closed`, `angry`, `sad`, `squint` (> <), `heart`, `star`, `dizzy`, dazu Tränen, Schweiß und Wangen
- **6 Handschuh-Hände** im klassischen Cartoon-Stil (drei Finger und Daumen, weiß gefüllt, dünne Innenlinien, Stulpe mit Falten): `open`, `fist`, `point`, `thumbs_up`, `peace`, `hold`, links und rechts, optional im Umriss-Stil des Originals und mit Gummischlauch-Arm. Dazu kommen **Griffe in zwei Ebenen** (`grip`: Handfläche hinter, Finger vor dem Gegenstand; `grip_behind`: nur der Daumen vorne) und die Seitenansicht `side`. Finger, die aus dem Blickwinkel verdeckt wären, werden weggelassen.
- **Gesicht beweglich:** `face_x`/`face_y`/`face_scale` und `turn` (Dreiviertelansicht, das Auge in Blickrichtung wird schmaler)
- **14 Gegenstände:** Wasserglas (Füllstand mit waagerechter Oberfläche, auch gekippt), Flasche, Wasserstrahl, Tropfen, Feuerwerk (Rakete und Explosion), Buch (offen/zu, blättern), Checkliste (Häkchen nacheinander), Kaffee (mit Dampf), Herz, Funkeln, Stern, Pokal, Wecker (Zeiger), Zzz

Gegenstände lassen sich an Hände hängen (`attach_to`). Übersicht: `python -m tabby_anim catalog`. Referenz: [tools/anim/README.md](../../tools/anim/README.md).

Beispiele mit Teilen: `refill_water`, `drink_water_sip`, `fireworks_celebrate`, `reading_loop`, `checklist_done`, `in_love_loop`, `crying_loop`. Die automatischen Tests prüfen jedes Teil, die Spiegelung links/rechts, ungültige Angaben und die Loop-Nahtstellen.

**Noch offen:** schräge Blinzel-Striche wie im Original, Text, Körper. Jede neue Form ist eine kleine Zeichenfunktion und danach für die KI nur ein weiterer Parameter.

**In Claude Code (umgesetzt):** Skill `/tabby-animation <Beschreibung>` (`.claude/skills/tabby-animation/SKILL.md`). Getestet mit „Tabby niest“ → `animations/src/sneeze` (47 Frames, 7 Farben, 45 KB), nach zwei Korrekturrunden anhand des Kontaktbogens.

**In der Web-App (F-23):** Beschreibung eintippen → Claude erzeugt `keyframes.json` (Structured Output gegen das Schema des Rigs) → Backend rendert eine Vorschau → im Simulator ansehen → „Übernehmen“ legt einen Pull Request an, und die CI baut das Asset-Pack.

## 5. Speicher-Budget ⚠️

| Posten | Bytes |
|---|---|
| Assets-Partition (SPIFFS) | 12 320 768 (~11,75 MB) |
| 84 Original-GIFs | 10 412 035 |
| Icons | 672 768 |
| **rechnerisch frei** | **~1,2 MB**, davon geht noch SPIFFS-Verwaltung ab |

**Praktisch ist der Speicher fast voll.** Optionen:
1. **Ungenutzte Originale entfernen**, z. B. `f1_car` (485 KB), `turn_off_reddit`/`_scroll`/`_tv`, `codex_*`, `basketball_*`, wenn wir sie nicht brauchen. Das bringt schnell 1–2 MB.
2. **Eigene Clips knapp halten**: Budget **≤ 150 KB pro Clip**, Loops ≤ 80 KB (kurz, wenige Farben, kleine bewegte Fläche)
3. **Größere Ausbaustufe**: Die microSD-Karte des Boards als zweiten Asset-Speicher nutzen (Firmware-Erweiterung, Phase 5+)

Der SPIFFS-Build im CI schlägt fehl, wenn es nicht passt. Das ist gut so, weil es kein kaputtes Gerät gibt.

## 6. Ablauf für eine neue Animation

1. **Idee und Zweck** festlegen: Welches Feature löst sie aus? (z. B. `coffee_break` für die Pomodoro-Pause)
2. **Storyboard**: 3–5 Schlüsselposen in Figma (quer, 456 × 280)
3. **Animieren** in Jitter (oder einem anderen Werkzeug), 24 fps
4. **Export** als PNG-Sequenz → `animations/src/coffee_break/` → Pull Request
5. **CI** baut das GIF, prüft das Budget, erzeugt die Vorschau und baut die Firmware.
6. **Vorschau** im Simulator ansehen, dann Firmware per USB-Update flashen
7. **Abnahme am Gerät** (Checkliste §7)
8. Im **Director** bzw. Feature-Mapping verwenden (`protocol.md` §4)

## 7. Qualitäts-Checkliste

- [ ] Sieht neben einem Original (z. B. `task_completed`) wie aus einem Guss aus: gleiche Strichstärke, gleiche Augenform, gleiche Farbwelt.
- [ ] 24 fps, Easing vorhanden, keine ruckelnden Stellen
- [ ] Loop nahtlos, kein „Springen“ beim Übergang
- [ ] Hintergrund exakt schwarz (Pipeline prüft das)
- [ ] ≤ 16 Farben, kein Dithering-Rauschen
- [ ] Größe im Budget
- [ ] Auf dem echten Display (nicht nur im Browser) gut lesbar, auch aus 60 cm Entfernung
- [ ] Richtige Ausrichtung am Gerät (Drehung!)

## 8. Lizenz (Guardrail L2)

- Die Taby-Figur und ihre Animationen stehen unter eigenen Bedingungen: **privat nutzen, Taby bleibt Taby, nicht als eigenen Charakter ausgeben.**
- Eigene Animationen **mit der Taby-Figur** sind abgeleitete Werke. Sie bleiben deshalb **privat**, werden nicht veröffentlicht und nicht verkauft.
- Soll das Projekt je öffentlich werden: **eigene Figur** entwerfen. Pipeline und Stilprinzipien (Bewegung, Farben, Technik) lassen sich 1:1 weiterverwenden.
- Beiträge zurück an upstream (neue Taby-Animationen) sind laut Upstream-README willkommen, per Pull Request dort.
