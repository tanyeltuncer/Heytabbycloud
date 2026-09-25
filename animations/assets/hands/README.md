# Handgezeichnete Hände (Sprites)

Hier liegen transparente PNGs der Handformen im Stil `variant: "sprite"` (`open.png`, `peace.png`, `rock.png`, `thumbs_up.png`, `fist.png`, `point.png`). Fehlt eine Datei, zeichnet das Rig die programmierte Hand.

Erzeugen aus einer eigenen Zeichnung:

```sh
cd tools/anim
python scripts/extract_hand_sprites.py <zeichnung.jpg|png> ../../animations/assets/hands
```

**Herkunft der aktuellen Dateien:** ausgeschnitten aus der Handzeichnung, die der Projektinhaber am 2026-09-25 bereitgestellt hat. Die Nutzungsrechte hat er bestätigt.

Nur Zeichnungen ablegen, an denen du die Rechte hast (selbst gezeichnet oder passend lizenziert). Am besten eignen sich Originaldateien in hoher Auflösung oder als SVG, dann entfällt das Glätten von JPEG-Rauschen.
