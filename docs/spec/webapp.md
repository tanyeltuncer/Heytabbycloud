# Spec: Web-App

**Stack:** SvelteKit (Svelte 5), TypeScript, Vite, `adapter-static` (SPA, von Caddy ausgeliefert), Tailwind CSS, `esptool-js` (Flashen), Web Serial API.
PWA über `@vite-pwa/sveltekit`. Sprache: Deutsch. Dark Mode passend zum AMOLED-Look.

## 1. Seitenstruktur

```
/login                    Magic-Link anfordern
/                         Heute (Dashboard)
/aufgaben                 Alle Aufgaben (Tabs: Heute · Demnächst · Erledigt)
/fokus                    Großer Timer
/erinnerungen             Liste + Formular
/chat                     KI-Chat (Phase 4)
/tabby                    Geräte: Liste, Status, Fernsteuerung, Animationsgalerie
/tabby/neu                Einrichtungs-Assistent (F-02)
/tabby/:id                Geräte-Einstellungen
/simulator                Virtuelles Tabby (F-10)
/einstellungen            Konto, Zeitzone, Ruhezeiten, KI-Budget, Export, Löschen
```

Navigation: Auf dem Desktop eine linke Seitenleiste, auf dem Handy eine Tab-Leiste unten (Heute · Aufgaben · Fokus · Chat · Tabby).

## 2. Screens

### 2.1 Heute (`/`)
```
┌─────────────────────────────────────────────┐
│ Guten Morgen 👋             Tabby ● online  │
├──────────────────────┬──────────────────────┤
│ JETZT DRAN           │ FOKUS                │
│ Steuererklärung      │  ┌──────────┐        │
│ [✓ Erledigt] [▶ 25m] │  │  18:42   │ ⏸ ⏹   │
│                      │  └──────────┘        │
├──────────────────────┴──────────────────────┤
│ HEUTE (4)                        + Aufgabe  │
│ ○ Steuererklärung         ★ jetzt           │
│ ○ Mails beantworten                         │
│ ○ Einkaufen                    🔔 17:00     │
│ ✓ Standup                                   │
├─────────────────────────────────────────────┤
│ Nächste Erinnerung: Einkaufen · 17:00       │
└─────────────────────────────────────────────┘
```
Schnelleingabe oben: Enter legt eine Aufgabe für heute an. Einfache Syntax: `morgen`, `!hoch`, `@17:00` erzeugt eine Erinnerung.

### 2.2 Fokus (`/fokus`)
Großer Kreis-Countdown, Presets (25/5, 50/10, frei), Aufgaben-Auswahl, Buttons Start · Pause · Stopp. Der Browser-Tab-Titel zeigt die Restzeit.

### 2.3 Tabby (`/tabby`)
- Gerätekarte: Name, ● online/offline, zuletzt gesehen, Firmware, aktueller Zustand
- **Fernsteuerung:** Textkarte senden (Titel, Untertitel, Zeichenzähler), `CLEAR`
- **Animationsgalerie:** Raster mit Vorschaubildern und Suche, Kategorien (Stimmung, Arbeit, Pause, Erfolg, Sport, Sonstiges). Klick spielt die Animation ab.
- Helligkeitsregler, Ruhezeiten, Screensaver

### 2.4 Einrichtungs-Assistent (`/tabby/neu`)
Voraussetzung: Chrome oder Edge am Desktop, da Web Serial nötig ist. Sonst erscheint ein Hinweis mit Erklärung.

| Schritt | UI | Technik |
|---|---|---|
| 1 Vorbereitung | Checkliste: V1-Board, Datenkabel, Board per USB anstecken | – |
| 2 Verbinden | Button „Tabby verbinden“ | `navigator.serial.requestPort()`, esptool-js `ESPLoader`, Chip-Erkennung `ESP32-S3`, Flash 16 MB prüfen |
| 3 Registrieren | Name eingeben | `POST /devices` → `deviceId`, `deviceSecret` (nur im Speicher, nie in `localStorage`) |
| 4 Flashen | Fortschrittsbalken pro Teil (Bootloader, Tabelle, Identität, App, Assets), Dauer ca. 2–4 min | Bundle über `/api/firmware/bundles/…` laden, SHA-256 prüfen, `buildFactoryRecord()`, `writeFlash` mit allen Teilen, danach Hard-Reset |
| 5 WLAN | SSID und Passwort | Serieller Port neu öffnen (115200, DTR/RTS aus), `PROVISION {"ssid":…,"password":…}`, auf `TABY:OK PROVISION` warten. **Passwort verlässt den Browser nicht.** |
| 6 Online? | Spinner „Tabby verbindet sich …“, dann eine Test-Animation | SSE `device.status online` abwarten (Timeout 60 s), dann `POST /devices/:id/command {animation: "confirmation"}` |
| 7 Fertig | „Tabby ist bereit 🎉“, Link zu Heute | Port schließen |

Fehlerfälle: falscher Chip oder falsche Flash-Größe → Abbruch vor dem Flashen. WLAN-Fehler → Firmware meldet `wifi_error` (über `SETUP_INFO`), anzeigen und neu eingeben lassen.
**Alternative ohne Kabel für den WLAN-Schritt:** Mit dem Handy ins Setup-WLAN von Tabby gehen, `192.168.4.1` öffnen (Upstream-Captive-Portal).

**Firmware-Update per USB** (solange es kein OTA gibt): gleicher Assistent, Schritt 3 entfällt. Die Identität wird aus dem Gerät gelesen (Partition `factory_data` wird nicht überschrieben).

### 2.5 Chat (`/chat`) – Phase 4
- Nachrichtenliste mit gestreamten Antworten
- **Aktionskarten** unter der Antwort: „✔ Aufgabe ‚A‘ angelegt [Rückgängig]“ oder „⚠ Aufgabe löschen? [Bestätigen] [Ablehnen]“
- Button „Plane meinen Tag“ → Vorschau-Timeline → „Übernehmen“
- Kostenanzeige: „Heute 0,12 € von 0,50 €“

### 2.6 Simulator (`/simulator`)
- Canvas 280 × 456 mit Rahmen im Tabby-Look
- Meldet sich als eigenes Gerät an. Der Browser kann nicht direkt MQTT über TLS sprechen, deshalb nutzt der Simulator **MQTT over WebSockets** (Mosquitto-Listener `wss://mqtt.<domain>/mqtt`) mit eigenem Simulator-Gerät (`POST /devices?simulator=true`).
- Spielt Animationen als WebP ab, rendert Text- und Timer-Karten nach, simuliert Touch (Klick = Tap, Doppelklick, lang drücken)

## 3. Zustand & Daten

- **Svelte Stores** pro Bereich (`tasks`, `focus`, `devices`, `reminders`), gefüllt per REST, aktualisiert per SSE (`/api/events`)
- **Optimistische Updates** (sofort anzeigen, bei Fehler zurückrollen)
- Keine sensiblen Daten in `localStorage`. Erlaubt ist nur UI-Kram wie der zuletzt gewählte Tab.

## 4. PWA & Benachrichtigungen

- Manifest (Name „Tabby“, Icons, `display: standalone`), Service Worker mit Cache nur für die App-Shell. Daten immer live.
- Web-Push (VAPID) für Timer-Ende und Erinnerungen. Die Erlaubnis wird erst angefragt, wenn der Nutzer den ersten Timer startet, nicht beim Laden der Seite.

## 5. Barrierefreiheit & Qualität

- Tastaturbedienung für alles, sichtbarer Fokus, Kontrast AA
- `prefers-reduced-motion` respektieren (Galerie-Vorschauen stehen statt zu animieren)
- Playwright-E2E: Login (Test-Token), Aufgabe anlegen/erledigen, Timer starten → der Simulator zeigt den Timer.
