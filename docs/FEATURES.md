# Hey Tabby Cloud – Feature-Katalog

Ergänzt [KONZEPT.md](KONZEPT.md). Jedes Feature hat eine ID, eine Priorität, eine Phase und prüfbare Akzeptanzkriterien (AK).
Guardrail-Verweise wie `S3` oder `K2` beziehen sich auf Abschnitt 7 im Konzept.

**Priorität:** 🟥 Must (MVP) · 🟧 Should · 🟨 Could
**Annahmen** für offene Entscheidungen, jederzeit änderbar: SvelteKit, VPS mit Docker Compose, Claude API, Board 1,64".

---

## Übersicht

| ID | Feature | Prio | Phase |
|---|---|---|---|
| F-01 | Konto & Login | 🟥 | 1 |
| F-02 | Einrichtungs-Assistent (Flashen, WLAN, Pairing) | 🟥 | 2 |
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
| F-18 | Firmware-Updates über die Web-App (OTA) | 🟧 | 5 |
| F-19 | Statistiken | 🟨 | 5 |
| F-20 | Datenexport & Konto löschen | 🟧 | 3 |
| F-21 | PWA & Browser-Benachrichtigungen | 🟧 | 3 |

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

**Ablauf (Wizard mit 4 Schritten)**
1. **Verbinden:** Board per USB anstecken, Button „Tabby verbinden“. Im Browser öffnet sich der Dialog zur Auswahl des USB-Geräts (WebSerial).
2. **Firmware aufspielen:** Die aktuelle Firmware aus dem Server-Release wird per ESP Web Tools geflasht, mit Fortschrittsbalken.
3. **WLAN:** Netzwerk und Passwort eingeben, die Übertragung läuft per Improv-Protokoll. Das Passwort wird **nicht** an den Server geschickt.
4. **Koppeln:** Das Gerät zeigt einen 6-stelligen Code. Der Wizard erkennt ihn automatisch über die serielle Verbindung oder lässt ihn eintippen. Danach ist das Gerät verbunden.

**AK**
- [ ] Browser ohne WebSerial (Safari, Firefox) bekommen einen klaren Hinweis: „Einrichtung bitte einmalig in Chrome/Edge“.
- [ ] Nach erfolgreichem Pairing erscheint das Gerät in F-03 als „online“.
- [ ] Pairing-Code: 5 min gültig, nur einmal nutzbar, max. 5 Fehlversuche pro Code (S5).
- [ ] Ein bereits gekoppeltes Gerät kann nur nach Werksreset neu gekoppelt werden (H6).

---

## F-03 Geräteverwaltung & Status 🟥
**Story:** Als Nutzer will ich sehen, ob mein Tabby online ist, und es verwalten.
- Liste der Geräte mit Name, Status (online/offline, zuletzt gesehen), Firmware-Version, WLAN-Signal
- Umbenennen, „primäres Gerät“ festlegen, **Entkoppeln** (widerruft das Token, S3)

**AK**
- [ ] Der Status wird live aktualisiert (≤ 2 s nach Connect, ≤ 90 s nach Verbindungsabbruch).
- [ ] Nach dem Entkoppeln wird die Verbindung des Geräts sofort getrennt, ein erneutes Verbinden schlägt fehl.

---

## F-04 Animationen & Fernsteuerung 🟥
**Story:** Als Nutzer will ich Tabby aus dem Browser Animationen abspielen lassen.
- Galerie mit allen Animationen, die das Gerät im `hello` meldet (Vorschau als GIF/WebP)
- Klick → `animation.play`, optional in Schleife
- Grundstimmung setzen (`face.state`): idle, happy, focus, sleepy, alert
- Kurzen Text senden (`text.show`, max. 60 Zeichen, K5)

**AK**
- [ ] Vom Klick bis zur Animation am Gerät vergehen < 300 ms (im selben Land).
- [ ] Animationen, die das Gerät nicht kennt, werden in der Galerie nicht angeboten.
- [ ] Max. 5 Befehle pro Sekunde pro Gerät, alles darüber wird verworfen (H5).

---

## F-05 Aufgaben 🟥
**Story:** Als Nutzer will ich Aufgaben verwalten, und Tabby zeigt mir, woran ich gerade arbeite.
- Anlegen, bearbeiten, abhaken, löschen, sortieren (Drag & Drop)
- Felder: Titel, Notiz, Fälligkeitsdatum, Priorität (niedrig/mittel/hoch), Status
- Ansichten: **Heute**, **Demnächst**, **Erledigt**
- **„Jetzt dran“:** genau eine Aufgabe ist aktiv und wird auf dem Gerät angezeigt (`task.current`).
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
- [ ] Bei WLAN-Abbruch läuft der Timer am Gerät weiter (H3). Nach dem Reconnect gleicht `timer.state` den Zustand ab.
- [ ] Jede abgeschlossene Session wird für F-19 gespeichert.

---

## F-07 Erinnerungen 🟥
**Story:** Als Nutzer will ich zu einer bestimmten Zeit von Tabby erinnert werden.
- Einmalig oder wiederkehrend (täglich, werktags, wöchentlich)
- Optional an eine Aufgabe gebunden
- Auslösung: `reminder.fire` am Gerät (Animation „alert“ + Titel) plus Browser-Benachrichtigung
- Am Gerät antippen = erledigt, lange drücken = 10 min Schlummern

**AK**
- [ ] Auslösung mit höchstens 30 s Verzögerung
- [ ] Während der Ruhezeiten (F-09) nur stumm im Browser, das Gerät bleibt dunkel.
- [ ] Ist das Gerät offline, wird die Erinnerung nachgeholt, sofern sie nicht älter als 1 h ist.

---

## F-08 Touch-Bedienung am Gerät 🟥
**Story:** Als Nutzer will ich Tabby direkt antippen können, ohne zum Browser zu wechseln.

| Zustand am Gerät | Tap | Doppeltipp | Lang drücken | Wischen |
|---|---|---|---|---|
| Idle | nächste Aufgabe anzeigen | – | Fokus-Timer starten (Standard-Preset) | durch Aufgaben blättern |
| Aufgabe angezeigt | – | Aufgabe erledigt | Fokus für diese Aufgabe starten | nächste/vorige Aufgabe |
| Fokus läuft | Restzeit groß anzeigen | Pause/Weiter | Timer stoppen (mit Bestätigung) | – |
| Erinnerung | erledigt | – | 10 min Schlummern | wegwischen |
| Schlafmodus | aufwecken | – | – | – |

**AK**
- [ ] Jede Geste gibt sofort sichtbares Feedback am Gerät (< 100 ms), auch offline.
- [ ] Offline-Gesten, die Daten ändern, landen in einer Warteschlange und werden nach dem Reconnect gesendet.

---

## F-09 Geräte-Einstellungen 🟥
- Helligkeit (Tag/Nacht), **Ruhezeiten** (Standard 22–7 Uhr), Zeitzone
- Screensaver nach X Minuten Inaktivität (Standard 10 min, H1)
- Werksreset aus der Web-App auslösen (setzt zusätzlich das Token zurück)

**AK**
- [ ] Einstellungen werden sofort per `settings.set` übertragen und im Gerät dauerhaft gespeichert (NVS).
- [ ] In den Ruhezeiten ist das Display aus oder minimal gedimmt.

---

## F-10 Tabby-Simulator 🟧
**Story:** Als Entwickler will ich ohne Hardware testen können.
- Ein virtuelles Tabby im Browser (Canvas mit dem Displayformat 280×456), das sich wie ein echtes Gerät per WebSocket anmeldet
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
- Modellwahl: kleines Modell als Standard, großes nur für F-12

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

## F-18 OTA-Updates 🟧
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

## Anhang A – Zustände am Gerät

```
BOOT ─► kein WLAN? ─► SETUP (wartet auf Improv)
  │
  └► WLAN ok ─► CONNECTING ─► kein Token? ─► PAIRING (zeigt Code)
                    │                            │
                    │◄───────── Token erhalten ──┘
                    ▼
                  IDLE ◄──► TASK ◄──► FOCUS / BREAK
                    │  ▲
         Erinnerung │  │ erledigt/Schlummern
                    ▼  │
                  REMINDER
   jederzeit: OFFLINE-Badge (lokal weiter), SLEEP (Ruhezeit/Screensaver),
              THINKING (KI antwortet), UPDATING (OTA)
```

## Anhang B – Datenmodell (erste Version)

| Tabelle | Wichtige Felder |
|---|---|
| `users` | id, email, created_at, timezone, ai_budget_day, ai_budget_month |
| `sessions` | id, user_id, expires_at |
| `devices` | id, user_id, name, board, fw_version, token_hash, last_seen_at, settings (JSON) |
| `pairing_codes` | code_hash, device_nonce, expires_at, attempts, used_at |
| `tasks` | id, user_id, title, note, due_date, priority, status, sort_order, is_current, completed_at |
| `focus_sessions` | id, user_id, task_id?, kind (focus/break), started_at, ends_at, ended_at, state |
| `reminders` | id, user_id, task_id?, title, fire_at, rrule?, last_fired_at, snoozed_until |
| `notes` | id, user_id, title, body_md, updated_at |
| `habits` / `habit_logs` | id, user_id, name, schedule / habit_id, date |
| `ai_messages` | id, user_id, role, content, tool_calls (JSON), created_at |
| `ai_usage` | id, user_id, model, input_tokens, output_tokens, cost_eur, created_at |
