# Hey Tabby Cloud – Feature-Katalog

Ergänzt [KONZEPT.md](KONZEPT.md). Jedes Feature hat eine ID, eine Priorität, eine Phase und prüfbare Akzeptanzkriterien (AK).
Guardrail-Verweise wie `S3` oder `K2` beziehen sich auf Abschnitt 7 im Konzept.

**Priorität:** 🟥 Must (MVP) · 🟧 Should · 🟨 Could
**Annahmen** (siehe [ADR-0003](adr/0003-stack.md)): SvelteKit, VPS mit Docker Compose, Mosquitto/MQTT, Claude API, Board 1,64" V1.
Technische Details: [spec/](spec/).

---

## Übersicht

| ID | Feature | Prio | Phase |
|---|---|---|---|
| F-01 | Konto & Login | 🟥 | 1 |
| F-02 | Einrichtungs-Assistent (Flashen, Gerätezugang, WLAN) | 🟥 | 2 |
| F-03 | Geräteverwaltung & Status | 🟥 | 2 |
| F-04 | Animationen & Fernsteuerung | 🟥 | 2 |
| F-05 | Aufgaben | 🟥 | 3 |
| F-06 | Fokus-Timer | 🟥 | 3 |
| F-07 | Erinnerungen | 🟥 | 3 |
| F-08 | Touch-Bedienung am Gerät | 🟥 | 3 |
| F-09 | Geräte-Einstellungen (Helligkeit, Ruhezeiten) | 🟥 | 3 |
| F-10 | Tabby-Simulator im Browser | 🟧 | 2–3 |
| F-11 | KI-Chat mit Aktionen | 🟧 | 4 |
| F-12 | Tagesplanung mit KI | 🟧 | 4 |
| F-13 | KI-Kostenkontrolle | 🟥 *(sobald F-11 existiert)* | 4 |
| F-14 | Notizen | 🟨 | 5 |
| F-15 | Gewohnheiten (Habits) | 🟨 | 5 |
| F-16 | Sprache (Push-to-Talk) | 🟨 | 5 |
| F-17 | Kalender-Import (ICS) | 🟨 | 5 |
| F-18 | Firmware-Updates über die Web-App (OTA) | 🟨 | 5 |
| F-19 | Statistiken | 🟨 | 5 |
| F-20 | Datenexport & Konto löschen | 🟧 | 3 |
| F-21 | PWA & Browser-Benachrichtigungen | 🟧 | 3 |
| F-22 | Eigene Animationen (Pipeline) | 🟨 | 5 (Pipeline ✅) |
| F-23 | Animation per Beschreibung (KI) | 🟨 | 5 |

---

## F-01 Konto & Login 🟥
**Story:** Als Nutzer will ich mich sicher einloggen, damit nur ich mein Tabby steuern kann.
- Login per **Magic-Link** (E-Mail), optional Passkey
- Nur ein Nutzer bzw. wenige eingeladene Nutzer. Registrierung nur über Einladungscode oder Allowlist, keine offene Registrierung.
- Die Session läuft nach 30 Tagen ab und lässt sich auf allen Geräten gleichzeitig abmelden.

**AK**
- [ ] Ohne gültige Session sind alle Seiten außer Login gesperrt (`401`/Redirect).
- [ ] Ein Magic-Link ist 15 min gültig und nur einmal nutzbar.
- [ ] Rate-Limit: max. 5 Login-Mails pro Stunde und Adresse.
- [ ] Cookies sind `HttpOnly`, `Secure` und `SameSite=Lax` (S7).

---

## F-02 Einrichtungs-Assistent 🟥
**Story:** Als Nutzer will ich mein Tabby komplett im Browser einrichten, ohne etwas zu installieren.

**Ablauf** (Details und Technik: [spec/webapp.md](spec/webapp.md) §2.4)
1. **Vorbereiten:** Board (V1) per USB-Datenkabel anstecken.
2. **Verbinden:** Button „Tabby verbinden“ öffnet die USB-Auswahl im Browser (Web Serial). Chip und Flash-Größe werden geprüft.
3. **Registrieren:** Name vergeben. Das Backend erzeugt den Gerätezugang (`device_id`, `device_secret`, [ADR-0002](adr/0002-identitaet-per-factory-record.md)).
4. **Flashen:** Firmware aus unserem CI plus Factory-Record (Zugangsdaten), Fortschrittsbalken, ca. 2–4 min
5. **WLAN:** Netzwerk und Passwort eingeben, Übertragung per USB-Befehl `PROVISION`. Das Passwort wird **nicht** an den Server geschickt.
6. **Online-Check:** Warten, bis Tabby sich beim Broker meldet, dann spielt die Test-Animation `confirmation`.

**AK**
- [ ] Browser ohne Web Serial (Safari, Firefox) bekommen einen klaren Hinweis: „Einrichtung bitte einmalig in Chrome/Edge“.
- [ ] Falscher Chip oder falsche Flash-Größe → Abbruch **vor** dem Flashen.
- [ ] Das Geräte-Secret landet nie in `localStorage`, Logs oder der Browser-Konsole (S5).
- [ ] Nach Schritt 6 erscheint das Gerät in F-03 als „online“ (Timeout 60 s mit Hilfetext).
- [ ] **Update-Modus:** Ein vorhandenes Gerät kann neu geflasht werden, ohne den Zugang zu verlieren (`factory_data` bleibt).
- [ ] Alternative WLAN-Einrichtung über das Captive Portal (Handy → Tabby-WLAN → `192.168.4.1`) ist im Assistenten erklärt.

---

## F-03 Geräteverwaltung & Status 🟥
**Story:** Als Nutzer will ich sehen, ob mein Tabby online ist, und es verwalten.
- Liste der Geräte mit Name, Status (online/offline, zuletzt gesehen), Firmware-Version, WLAN-Signal
- Umbenennen, „primäres Gerät“ festlegen, **Entkoppeln** (löscht den MQTT-Zugang, S3)

**AK**
- [ ] Der Status wird live aktualisiert (≤ 2 s nach Connect, ≤ 90 s nach Verbindungsabbruch).
- [ ] Nach dem Entkoppeln wird die Verbindung des Geräts sofort getrennt, ein erneutes Verbinden schlägt fehl.

---

## F-04 Animationen & Fernsteuerung 🟥
**Story:** Als Nutzer will ich Tabby aus dem Browser Animationen abspielen lassen.
- Galerie mit allen 84 Animationen aus dem Manifest der installierten Firmware (Vorschau als WebP)
- Klick → Animations-ID als Befehl (z. B. `confirmation`, `working_in>working_loop`)
- Kurzen Text senden (`UI/title_subtitle`, Titel max. 40, Untertitel max. 60 Zeichen, bereinigt, K5)
- „Zurücksetzen“ → `CLEAR`

**AK**
- [ ] Vom Klick bis zur Animation am Gerät vergehen < 300 ms (im selben Land).
- [ ] Unbekannte Animationen führen nicht zu einem Fehler (Firmware antwortet `unsupported_animation`).
- [ ] Max. 5 Befehle pro Sekunde pro Gerät, alles darüber wird verworfen (H5).

---

## F-05 Aufgaben 🟥
**Story:** Als Nutzer will ich Aufgaben verwalten, und Tabby zeigt mir, woran ich gerade arbeite.
- Anlegen, bearbeiten, abhaken, löschen, sortieren (Drag & Drop)
- Felder: Titel, Notiz, Fälligkeitsdatum, Priorität (niedrig/mittel/hoch), Status
- Ansichten: **Heute**, **Demnächst**, **Erledigt**
- **„Jetzt dran“:** genau eine Aufgabe ist aktiv und wird auf dem Gerät als Auswahlkarte angezeigt (siehe F-08).
- Abhaken im Browser oder am Gerät löst am Gerät die Animation „happy“ aus.

**AK**
- [ ] Änderungen erscheinen ohne Reload auf allen offenen Browsern und am Gerät (≤ 1 s).
- [ ] Wird die aktive Aufgabe erledigt, schlägt Tabby die nächste Aufgabe aus „Heute“ vor.
- [ ] Löschen verlangt eine Bestätigung oder bietet ein Undo innerhalb von 5 s.

---

## F-06 Fokus-Timer 🟥
**Story:** Als Nutzer will ich fokussiert arbeiten, und Tabby begleitet mich dabei.
- Presets: 25/5 (Pomodoro), 50/10, frei wählbar
- Start, Pause und Stopp im Browser **oder** am Gerät. Beide Seiten sind immer synchron.
- Optional mit einer Aufgabe verknüpft
- Während des Fokus: Gesicht „focus“, Countdown am Gerät. In der Pause: Animation „relax“.
- Am Ende: Animation und Browser-Benachrichtigung (F-21)

**AK**
- [ ] Der Timer arbeitet mit **absoluter Endzeit** (`ends_at`). Die Anzeige bleibt nach Reload oder Reconnect korrekt.
- [ ] Bei WLAN-Abbruch läuft der Timer am Gerät weiter (H3). Nach dem Reconnect sendet das Backend die Timer-Karte mit neu berechneter Restzeit.
- [ ] Jede abgeschlossene Session wird für F-19 gespeichert.

---

## F-07 Erinnerungen 🟥
**Story:** Als Nutzer will ich zu einer bestimmten Zeit von Tabby erinnert werden.
- Einmalig oder wiederkehrend (täglich, werktags, wöchentlich)
- Optional an eine Aufgabe gebunden
- Auslösung: Auswahlkarte `UI/choice_2?reminder:<TITEL>|ERLEDIGT|SPÄTER` am Gerät plus Browser-Benachrichtigung
- Am Gerät „ERLEDIGT“ tippen = erledigt, „SPÄTER“ = 10 min Schlummern

**AK**
- [ ] Auslösung mit höchstens 30 s Verzögerung
- [ ] Während der Ruhezeiten (F-09) nur stumm im Browser, das Gerät bleibt dunkel.
- [ ] Ist das Gerät offline, wird die Erinnerung nachgeholt, sofern sie nicht älter als 1 h ist.

---

## F-08 Touch-Bedienung am Gerät 🟥
**Story:** Als Nutzer will ich Tabby direkt antippen können, ohne zum Browser zu wechseln.

Wir nutzen die **Auswahlkarten der Upstream-Firmware** (`UI/choice_2`). Getippte Optionen meldet das Gerät per `event` (FW-2). Dafür braucht es keine neue Gestenerkennung in der Firmware.

| Zustand am Gerät | Karte | Option 1 | Option 2 |
|---|---|---|---|
| Aufgabe „Jetzt dran“ | `UI/choice_2?task:<TITEL>\|ERLEDIGT\|FOKUS 25` | Aufgabe erledigt → `task_completed`, nächste Aufgabe | Fokus 25 min für diese Aufgabe |
| Fokus-Ende | `UI/choice_2?focus_end:GESCHAFFT!\|PAUSE\|WEITER` | 5 min Pause | nächster Fokusblock |
| Pausen-Ende | `UI/choice_2?break_end:PAUSE VORBEI\|LOS\|NOCH 5` | Fokus starten | Pause verlängern |
| Erinnerung | `UI/choice_2?reminder:<TITEL>\|ERLEDIGT\|SPÄTER` | erledigt | 10 min schlummern |
| KI-Bestätigung (K2) | `UI/choice_2?ai:<FRAGE>\|JA\|NEIN` | Aktion bestätigen | ablehnen |

*Optional (🟨, FW-2b):* freie Gesten im Idle-Zustand (Tap = nächste Aufgabe, lang drücken = Fokus). Nur wenn die Firmware das einfach hergibt.

**AK**
- [ ] Jedes Antippen gibt sofort sichtbares Feedback am Gerät (< 100 ms), auch offline.
- [ ] Eine Auswahl wird innerhalb von 1 s im Browser sichtbar.
- [ ] Offline getippte Auswahlen gehen verloren. Das Gerät zeigt dann „offline“, und die Karte bleibt nach dem Reconnect stehen (kein stiller Datenverlust).

---

## F-09 Geräte-Einstellungen 🟥
- Helligkeit (Tag/Nacht), **Ruhezeiten** (Standard 22–7 Uhr), Zeitzone
- Screensaver nach X Minuten Inaktivität (Standard 10 min, H1)
- Entkoppeln und Werksreset erklärt (siehe F-03, H6)

**AK**
- [ ] Helligkeit wird sofort übertragen (FW-6). Ruhezeiten und Screensaver steuert das Backend (Director → `sleeping_loop` + Helligkeit runter).
- [ ] In den Ruhezeiten ist das Display aus oder minimal gedimmt.

---

## F-10 Tabby-Simulator 🟧
**Story:** Als Entwickler will ich ohne Hardware testen können.
- Ein virtuelles Tabby im Browser (Canvas mit dem Displayformat 280×456), das sich wie ein echtes Gerät per MQTT (über WebSocket) am Broker anmeldet
- Es spielt dieselben Animationen (WebP) und simuliert Touch per Maus.
- Auch nützlich als „zweites Tabby“ auf dem Handy

**AK**
- [ ] Der Simulator nutzt exakt dasselbe Protokoll wie die Firmware, ohne Sonderpfade im Backend.

---

## F-11 KI-Chat mit Aktionen 🟧
**Story:** Als Nutzer will ich in normaler Sprache sagen, was passieren soll.
- Chat in der Web-App mit gestreamter Antwort
- **Tools**, die die KI aufrufen darf (K1): `list_tasks`, `create_task`, `update_task`, `complete_task`, `start_focus`, `stop_focus`, `create_reminder`, `play_animation`, `show_text`
- **Nicht erlaubt ohne Klick** (K2): `delete_task`, Massenänderungen (mehr als 3 Objekte)
- Während die KI antwortet, spielt am Gerät die Animation „thinking“.
- Der Chat-Verlauf wird pro Tag gespeichert und lässt sich löschen.

**AK**
- [ ] „Leg mir für morgen 3 Aufgaben an: A, B, C“ erzeugt 3 Aufgaben mit dem Datum von morgen.
- [ ] Jede ausgeführte Aktion erscheint im Chat als Karte („✔ Aufgabe ‚A‘ angelegt“, mit Undo).
- [ ] Ist die KI nicht erreichbar, erscheint eine klare Fehlermeldung, der Rest der App läuft weiter (K7).

---

## F-12 Tagesplanung mit KI 🟧
- Button „Plane meinen Tag“: Die KI nimmt die offenen Aufgaben, Termine (F-17) und verfügbaren Stunden und erstellt einen Vorschlag mit Reihenfolge und Fokusblöcken.
- Der Vorschlag wird als Vorschau angezeigt und erst nach „Übernehmen“ gespeichert (K2, K6).

**AK**
- [ ] Ohne Klick auf „Übernehmen“ ändert sich nichts an den Daten.

---

## F-13 KI-Kostenkontrolle 🟥 (ab Phase 4)
- Die Tokens jedes Aufrufs werden gezählt und in € umgerechnet angezeigt (Tag/Monat).
- Hartes Tages- und Monatslimit (konfigurierbar), Warnung ab 80 % (K4)
- Modell per Env (`TABBY_AI_MODEL`, Standard `claude-opus-5`), Effort `low` im Chat, `medium` für F-12

**AK**
- [ ] Bei überschrittenem Limit lehnt das Backend weitere KI-Aufrufe ab, *bevor* die API aufgerufen wird.

---

## F-14 Notizen 🟨
- Markdown-Notizen mit Suche, optional mit einer Aufgabe verknüpft
- Die KI kann Notizen lesen, der Inhalt wird aber als Daten markiert (K3).

## F-15 Gewohnheiten 🟨
- Gewohnheit anlegen (täglich oder x-mal pro Woche) und abhaken, am Gerät per Wischen möglich
- Streak-Anzeige am Gerät, bei Meilensteinen (7/30 Tage) eine Feier-Animation

## F-16 Sprache (Push-to-Talk) 🟨
- Mikrofon-Button in der Web-App, **gedrückt halten = aufnehmen** (D3)
- Die Transkription läuft per API, der Text geht in den KI-Chat (F-11). Audio wird nicht gespeichert (D2).

## F-17 Kalender-Import 🟨
- ICS-URL eintragen (nur lesend), Abruf alle 15 min
- 10 min vor einem Termin kommt eine Erinnerung am Gerät, F-12 berücksichtigt die Termine.

## F-18 OTA-Updates 🟨
- **Voraussetzung:** Das Partitionslayout erlaubt zwei App-Slots ([ADR-0004](adr/0004-kein-ota-im-mvp.md)). Bis dahin: Update per USB im Assistenten (F-02).
- Die Web-App zeigt „Update verfügbar“, auf Klick lädt das Gerät die signierte Firmware (S6).
- Fehlgeschlagener Boot führt zum automatischen Rollback. Die Web-App zeigt das Ergebnis an.

## F-19 Statistiken 🟨
- Fokuszeit pro Tag und Woche, erledigte Aufgaben, Habit-Streaks
- Einfache Diagramme, keine Weitergabe an Dritte

## F-20 Datenexport & Löschen 🟧
- Export aller Daten als JSON (D5)
- Konto löschen: entfernt alle Daten und entkoppelt alle Geräte.

## F-21 PWA & Benachrichtigungen 🟧
- Die Web-App ist installierbar (Manifest und Service Worker), ohne App Store.
- Web-Push für Timer-Ende und Erinnerungen, der Nutzer muss aktiv zustimmen.

---

## F-22 Eigene Animationen 🟨
**Story:** Als Nutzer will ich eigene Animationen im Tabby-Stil erstellen und auf mein Gerät bringen.
- Quelle: PNG-Sequenz oder MP4 (quer 456 × 280, 24 fps, schwarzer Hintergrund) plus `meta.yml`
- Die CI-Pipeline erzeugt ein GIF im Upstream-Format (gedreht, Palette, Delta-optimiert), Metadaten und eine Vorschau (Details: [spec/animationen.md](spec/animationen.md)).

**AK**
- [ ] Ein neuer Clip landet per Pull Request ohne Handarbeit im Asset-Pack und in der Galerie.
- [ ] Budget- oder Formatverstöße lassen den Build fehlschlagen, statt ein kaputtes Image zu erzeugen.
- [ ] Der Clip läuft am Gerät in richtiger Ausrichtung und im Stil der Originale (Checkliste §7).

---

## F-23 Animation per Beschreibung (KI) 🟨
**Story:** Als Nutzer will ich in einem Satz beschreiben, wie Tabby reagieren soll, und bekomme eine passende Animation im Original-Stil.
- Eingabe: Beschreibung, optional Länge und Loop/einmalig
- Claude erzeugt `keyframes.json` für das Gesichts-Rig (Structured Output gegen das Rig-Schema, nur erlaubte Parameter)
- Das Backend rendert eine Vorschau (gleicher Code wie in der CI), und die Web-App zeigt sie im Simulator.
- „Übernehmen“ legt einen Pull Request mit `animations/src/<id>/` an. Die CI baut das Asset-Pack, geflasht wird per USB-Update.

**AK**
- [ ] Ungültige oder unbekannte Parameter werden abgelehnt, bevor gerendert wird.
- [ ] Budget (KB, Farben) wird vor dem PR geprüft.
- [ ] Kosten laufen über das KI-Budget (F-13).

---

## Anhang A – Zustände am Gerät

Den Soll-Zustand berechnet der **Device Director** im Backend ([spec/backend.md](spec/backend.md) §5), Priorität von oben nach unten:

```
sleep      Ruhezeit → sleeping_loop, gedimmt
reminder   offene Erinnerung → Auswahlkarte ERLEDIGT/SPÄTER
thinking   KI antwortet → searching_loop
focus      Timer läuft → working_loop + Timer-Karte
break      Pause läuft → relaxing_01_loop + Timer-Karte
task       „Jetzt dran“ gesetzt → Auswahlkarte ERLEDIGT/FOKUS 25
idle       sonst → Idle-Animation der Firmware
```
Gerätseitig (Firmware, upstream): Setup/Captive Portal, falls kein WLAN eingerichtet ist. Offline-Anzeige, falls der Broker nicht erreichbar ist.

## Anhang B – Datenmodell

Siehe [spec/backend.md](spec/backend.md) §4.
