# Spec: Protokoll Gerät ↔ Cloud (MQTT)

> Ersetzt den WebSocket-Entwurf aus dem ursprünglichen Konzept, siehe [ADR-0001](../adr/0001-mqtt-statt-websocket.md).
> Wir nutzen das **MQTT-Protokoll der Upstream-Firmware** und ergänzen nur `event` und `status`.

## 1. Verbindung

| Parameter | Wert |
|---|---|
| Broker | Mosquitto 2.x, `mqtts://mqtt.<domain>:8883` (TLS, Let's-Encrypt-Zertifikat) |
| Gerät: Username / Passwort | `device_id` / `device_secret` aus dem Factory-Record |
| Keepalive | 30 s (upstream) |
| QoS | 1 für `cmd`, `ack`, `event`; 0 für `state` |
| Backend-Client | eigener User `tabby-api`, darf `devices/+/cmd` schreiben und `devices/+/#` lesen |

### ACLs (Mosquitto Dynamic Security)
- Rolle `device`: `publishClientSend` auf `devices/%u/ack`, `devices/%u/state`, `devices/%u/event`, `devices/%u/status`; `subscribe` auf `devices/%u/cmd`. (`%u` = eigener Username.)
- Rolle `api`: `subscribe` auf `devices/+/#`, `publishClientSend` auf `devices/+/cmd`
- **Ein Gerät kann niemals Topics eines anderen Geräts lesen oder schreiben** (Guardrail S3).

## 2. Topics

| Topic | Richtung | Payload | Herkunft |
|---|---|---|---|
| `devices/<id>/cmd` | Cloud → Gerät | Text-Befehl (Abschnitt 3) oder `{"command":"<text>"}`, **max. 383 Byte** | upstream |
| `devices/<id>/ack` | Gerät → Cloud | `{"ok":bool,"device_id","state","input","command"?,"error"?}` | upstream |
| `devices/<id>/state` | Gerät → Cloud | `{"device_id","state","wifi_mode","connected","reason","ts_ms"}` alle 15 s + bei Änderung | upstream |
| `devices/<id>/event` | Gerät → Cloud | `{"type":"choice","signal":N,"selection":"yes\|later\|..."}` / `{"type":"touch","gesture":"tap\|double\|long"}` | **neu (FW-2)** |
| `devices/<id>/status` | Gerät → Cloud | `online` / `offline` (retained, `offline` per LWT) | **neu (FW-5)** |

> **Korrelation:** `ack` enthält kein Message-ID-Feld, nur `input`. Das Backend schickt pro Gerät **einen Befehl nach dem anderen**
> (Queue, Timeout 5 s) und ordnet das `ack` über die Reihenfolge und `input` zu.

## 3. Befehlssprache (upstream, identisch für USB/BLE/MQTT)

| Befehl | Wirkung |
|---|---|
| `<animation_id>` | Animation abspielen, z. B. `confirmation`, `task_completed`, `working_loop` |
| `<intro>><loop>` | Intro, danach Loop, z. B. `working_in>working_loop` |
| `CLEAR` | aktuelle Karte oder Animation beenden, zurück zu Idle |
| `UI/title_subtitle?<ctx>:<TITEL>\|<UNTERTITEL>` | Textkarte |
| `UI/choice_2?<ctx>:<FRAGE>\|<OPTION1>\|<OPTION2>[\|<FUSSZEILE>]` | Auswahl mit 2 Optionen, Ergebnis per `event` |
| `UI/choice_1?<ctx>:<FRAGE>\|<OPTION>` | eine Option (Bestätigen) |
| `UI/timer?<ctx>:<LABEL>\|<rest_s>\|<gesamt_s>\|\|<run\|pause>\|0` | Countdown |
| `UI/progress:<LABEL>\|<prozent>` | Fortschrittsbalken (0–100) |

**Karten-Modifikatoren** (aus den Upstream-Tests abgeleitet, Details in `taby_reusable_ui.c` prüfen):
`!<animation>` Animation zur Karte · `@<sekunden>` Anzeigedauer · `&<effekt>/<s>` Deko-Effekt · `~<effekt>/<s>` Text-Effekt · `#<rrggbb>` Farbe.

**Regeln** (aus dem Upstream-README, gelten auch für uns):
- Steuerwörter englisch, Anzeigetext darf deutsch sein, **aber nur Glyphen, die der Font kann.** Umlaute testen! Notfalls `ä→ae`.
- Nutzertexte dürfen **kein `|`, keinen Zeilenumbruch und keine Steuerzeichen** enthalten. Das Backend bereinigt sie (Guardrail K5).
- Titel werden gerätseitig auf < 96 Zeichen gekürzt. Wir begrenzen vorher auf **40 Zeichen Titel und 60 Zeichen Untertitel**.
- Unbekannte Animationen führen zu `ok:true` mit `unsupported_animation`. Das ist kein Fehler.

## 4. Mapping Features → Befehle

| Feature | Befehl(e) |
|---|---|
| Aufgabe anzeigen (F-05/F-08) | `UI/choice_2?task:<TITEL>\|ERLEDIGT\|FOKUS 25` |
| Aufgabe erledigt | `task_completed` |
| Aufgabe angelegt | `task_created` |
| Fokus starten (F-06) | `working_in>working_loop`, danach `UI/timer?focus:FOKUS\|<rest>\|<gesamt>\|\|run\|0` |
| Pause (Timer) | `UI/timer?focus:FOKUS\|<rest>\|<gesamt>\|\|pause\|0` |
| Pause (Pomodoro-Break) | `break_start`, danach `relaxing_01_loop` |
| Erinnerung (F-07) | `UI/choice_2?reminder:<TITEL>\|ERLEDIGT\|SPÄTER` |
| Fokus-Ende | `UI/choice_2?focus_end:GESCHAFFT!\|PAUSE\|WEITER` |
| KI-Bestätigung (K2) | `UI/choice_2?ai:<FRAGE>\|JA\|NEIN` |
| KI denkt (F-11) | `searching_loop` bzw. `claude_in>claude_loop` |
| KI fertig | `taby_response_ready_in>taby_response_ready_loop` oder Textkarte |
| Tag geplant (F-12) | `day_planned` |
| Wasser/Pause-Hinweise (F-15) | `drink_water`, `stretching`, `posture_check` |
| Ruhezeit (F-09) | `sleeping_loop`, danach Helligkeit runter (FW-6) |
| Erfolg/Streak | `trophy`, `thumbs_up`, `perfect_day_01` |

Vollständige Liste der 84 Animationen: `assets/amoled-1.64/manifest.json` im Firmware-Repo. Die Web-App liest sie aus dem Release-Bundle.

## 5. Zustände

Das Backend führt den **Soll-Zustand** pro Gerät (`idle | task | focus | break | reminder | thinking | sleep`).
Nach `status=online` (Reconnect) sendet es den Soll-Zustand erneut (z. B. den Timer mit neu berechneter Restzeit).
Die Restzeit wird immer aus `ends_at - now()` berechnet. Dadurch braucht das Gerät keine eigene Uhrzeit.

## 6. Sicherheitsregeln

- Über MQTT **nie** senden: `PROVISION`, `WIFI_*`, `CLAIM`, `DIAG`, `LOGS`, `TRANSPORT_*`. Das Backend hat eine **Allowlist**:
  Animations-IDs aus dem Manifest, `CLEAR`, `UI/(title_subtitle|choice_1|choice_2|timer|progress)`, `BRIGHTNESS`.
- Rate-Limit: max. 5 Befehle/s und 60/min pro Gerät (H5)
- Eingehende Payloads > 1 KB werden verworfen, `event` wird per Schema validiert.
