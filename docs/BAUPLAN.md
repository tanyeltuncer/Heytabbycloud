# Hey Tabby Cloud – Bauplan

Schritt-für-Schritt-Plan zur Umsetzung von [KONZEPT.md](KONZEPT.md) und [FEATURES.md](FEATURES.md).
Die technischen Details stehen in [spec/](spec/), Entscheidungen in [adr/](adr/).

- Jede Phase endet mit einem **greifbaren Ergebnis** (✅ Done).
- Jede Aufgabe hat eine ID (`P2.3.1`), damit man sie als GitHub-Issue anlegen kann.
- Aufwand in Hobby-Abenden (≈ 2–3 h), grob geschätzt.

> **Prinzip „nichts installieren“ gilt auch fürs Entwickeln:** Die Firmware baut **GitHub Actions** (Docker-Image `espressif/idf:v5.4.2`),
> geflasht wird **im Browser**. Code entsteht in der Cloud (Claude Code, GitHub Codespaces). Eine lokale Toolchain ist optional.

---

## Überblick

| Phase | Ergebnis | Features | Aufwand |
|---|---|---|---|
| 0 | Tabby lebt (Original-Firmware, Gehäuse) | – | 2 Abende + Lieferzeit |
| 1 | Server läuft, Login funktioniert, Deploy automatisch | F-01 | 3–4 Abende |
| 2 | Klick im Browser → Tabby reagiert, Einrichtung komplett im Browser | F-02, F-03, F-04, F-10 | 6–8 Abende |
| 3 | Tabby im Alltag nutzbar | F-05 – F-09, F-20, F-21 | 6–8 Abende |
| 4 | KI-Assistent | F-11 – F-13 | 3–5 Abende |
| 5 | Extras nach Lust und Laune | F-14 – F-19 | offen |

**Kritischer Pfad:** P0 (Hardware) → P2.2 (Firmware-Fork mit FW-1) → P2.4 (Factory-Record am echten Gerät verifiziert). Wenn das klappt, ist der Rest „normale“ Web-Entwicklung.
**Parallel möglich:** Phase 1 und der Simulator (P2.6) lassen sich schon während der Lieferzeit der Hardware bauen.

---

## Phase 0 – Hardware-Bring-up

**Ziel:** Das Board zeigt mit der Original-Firmware eine Animation und sitzt im Gehäuse. → [spec/hardware.md](spec/hardware.md)

| ID | Aufgabe | Details |
|---|---|---|
| P0.1 | **Einkaufen** | Einkaufsliste in `hardware.md` §2. ⚠️ Board-Revision **V1**. Am besten zwei Boards. |
| P0.2 | **Gehäuse drucken lassen** | Upstream `hardware/amoled-1.64/V1/desktop-case/`, PETG. Parallel zur Lieferzeit. |
| P0.3 | **Board prüfen** | Aufschrift/Revision fotografieren und in `docs/hardware-log.md` festhalten |
| P0.4 | **Original-Firmware flashen** | Offizielles Release-Bundle 1.1.x von GitHub laden, im Browser mit dem [esptool-js-Webflasher](https://espressif.github.io/esptool-js/) flashen (Offsets aus dem Bundle-Manifest) |
| P0.4b | *Alternative:* **offizielle Desktop-App** | Die [Hey-Taby-App](https://www.heytaby.com/downloads) (Mac, Windows, Linux experimentell) einmalig nutzen, um Tabby zu flashen und das Original-Verhalten als Referenz zu sehen. Bricht bewusst das Prinzip „nichts installieren“, ist optional und danach deinstallierbar. |
| P0.5 | **Funktionstest** | Serielles Web-Terminal (z. B. [Spacehuhn Serial Terminal](https://serial.huhn.me/), 115200 Baud): `PING` → `TABY:PONG`, `INFO`, `confirmation`, `UI/choice_2?test:HALLO?\|JA\|NEIN` → tippen → `CHOICE_SIGNAL` |
| P0.6 | **Upstream-Code lesen** | `taby_mqtt.c`, `taby_identity.c`, `taby_reusable_ui.c` (Karten-Syntax), `taby_http_server.c`, Notizen in `docs/hardware-log.md` |
| P0.7 | **Montage** | `hardware.md` §3, Magnet, Gummi, Stahlplättchen |

**✅ Done:** Tabby hängt am Monitor, spielt Animationen, eine Auswahlkarte reagiert auf Touch.

---

## Phase 1 – Cloud-Skelett

**Ziel:** `https://tabby.<domain>` ist erreichbar, Login funktioniert, ein Push auf `main` deployt automatisch. → [spec/infra.md](spec/infra.md), [spec/backend.md](spec/backend.md)

### P1.1 Accounts & Server (1 Abend)
- [ ] P1.1.1 Domain registrieren, DNS: `tabby.<domain>` und `mqtt.<domain>` → IP des VPS
- [ ] P1.1.2 VPS mieten (EU, Ubuntu 24.04), SSH-Key hinterlegen
- [ ] P1.1.3 Härten: Passwort-Login und Root-Login aus, `ufw` (22, 80, 443, 8883), `unattended-upgrades`
- [ ] P1.1.4 Docker + Compose-Plugin auf dem **Server** installieren
- [ ] P1.1.5 SMTP-Anbieter (Free-Tier) einrichten, SPF/DKIM für die Domain setzen

### P1.2 Monorepo (1 Abend)
- [ ] P1.2.1 pnpm-Workspace: `apps/web`, `apps/api`, `packages/protocol`, `infra/`
- [ ] P1.2.2 TypeScript strict, ESLint, Prettier, Vitest, gemeinsame `tsconfig.base.json`
- [ ] P1.2.3 `.env.example` (siehe `infra.md` §5), `.gitignore` inkl. `.env*`
- [ ] P1.2.4 `CLAUDE.md` im Repo-Root mit Konventionen, damit KI-Sessions den Kontext haben

### P1.3 Backend-Grundgerüst (1 Abend)
- [ ] P1.3.1 Hono-App, `GET /api/health`, pino-Logging ohne Bodies
- [ ] P1.3.2 Drizzle + Migrationen: `users`, `sessions`, `magic_links`
- [ ] P1.3.3 **F-01**: Magic-Link (Allowlist `ALLOWED_EMAILS`, 15 min, einmalig, Rate-Limit), Session-Cookie, CSRF-Header
- [ ] P1.3.4 Tests: Login-Flow, abgelaufener Link, fremde E-Mail, Rate-Limit

### P1.4 Web-Grundgerüst (0,5 Abende)
- [ ] P1.4.1 SvelteKit + `adapter-static` + Tailwind, Layout mit Navigation (Desktop/Handy)
- [ ] P1.4.2 `/login`, geschützte Routen, leere Seiten für alle Bereiche

### P1.5 Betrieb & CI/CD (1 Abend)
- [ ] P1.5.1 `infra/docker-compose.yml` mit `caddy`, `api`, `postgres` (Mosquitto kommt in P2.1)
- [ ] P1.5.2 Caddyfile inkl. Security-Header und CSP
- [ ] P1.5.3 `ci.yml`: install → lint → typecheck → test → build → gitleaks
- [ ] P1.5.4 `deploy.yml`: Images → GHCR → SSH-Deploy → Healthcheck
- [ ] P1.5.5 Backup-Container: `pg_dump` → `age` → `rclone`, **Restore einmal testen**
- [ ] P1.5.6 Externer Uptime-Check auf `/api/health`

**✅ Done:** Login unter `https://tabby.<domain>` funktioniert, Deploy per Push, Backup plus Restore getestet.

---

## Phase 2 – Tabby geht online

**Ziel:** Ein fabrikneues Board wird **nur mit Chrome** eingerichtet und ist danach aus dem Browser (auch vom Handy) steuerbar.
→ [spec/firmware.md](spec/firmware.md), [spec/protocol.md](spec/protocol.md), [spec/webapp.md](spec/webapp.md) §2.4

### P2.1 Broker (1 Abend)
- [ ] P2.1.1 Mosquitto-Container, `mosquitto.conf` (Listener 8883 TLS, 9001 WS intern, 1883 intern), Zertifikat von Caddy (Dateirechte!)
- [ ] P2.1.2 Dynamic Security initialisieren, Rollen `device` und `api` mit ACLs (`infra/dynsec-bootstrap.sh`, idempotent)
- [ ] P2.1.3 Cron: wöchentlich `SIGHUP` für die Zertifikatserneuerung
- [ ] P2.1.4 Test vom Server aus: `mosquitto_pub`/`mosquitto_sub` mit einem Test-Gerätezugang, fremde Topics werden abgelehnt

### P2.2 Firmware-Fork (2 Abende)
- [ ] P2.2.1 Upstream als `firmware/` übernehmen (git subtree, damit Updates mergebar bleiben), LICENSE/NOTICE behalten
- [ ] P2.2.2 **FW-1** Kconfig für Broker-URI und Topic-Prefix, `sdkconfig.cloud` mit unserer Domain
- [ ] P2.2.3 **FW-5** Last Will + `status` online/offline (retained)
- [ ] P2.2.4 **FW-2** `event`-Topic für Auswahlkarten (Hook in `publish_choice_signal`)
- [ ] P2.2.5 **FW-3** lokaler HTTP-Server nur im SoftAP-Setup, **FW-4** BLE aus
- [ ] P2.2.6 **FW-7** `firmware.yml` in GitHub Actions: Build + Paket als Artefakt, Release bei Tag `fw-v*`
- [ ] P2.2.7 Upstream-Tests (`tests/`) laufen weiter grün

### P2.3 Protokoll-Paket (1 Abend)
- [ ] P2.3.1 Zod-Schemas für `ack`, `state`, `event`, `status`
- [ ] P2.3.2 **Befehls-Builder** (`cmd.animation(id)`, `cmd.titleCard(t, s)`, `cmd.choice(ctx, q, a, b)`, `cmd.timer(...)`, `cmd.clear()`) mit **Text-Bereinigung** (K5): `|`, Zeilenumbrüche und Steuerzeichen raus, Längen kürzen, Umlaut-Strategie nach Font-Test
- [ ] P2.3.3 **Allowlist-Prüfung** für alles, was an `cmd` geht (`protocol.md` §6)
- [ ] P2.3.4 `buildFactoryRecord(deviceId, secret)` inkl. CRC32 + Unit-Tests (Vergleich mit Python-Referenz)

### P2.4 Backend: Geräte (1–2 Abende)
- [ ] P2.4.1 Tabelle `devices`, `POST /devices` (Zugang anlegen: Dynsec `createClient` + Rolle `device`), `DELETE` (Client löschen + `kickClient`)
- [ ] P2.4.2 MQTT-Modul: subscribe `devices/+/#`, `status`/`state` → DB + SSE, Befehls-Queue pro Gerät (seriell, 5 s Ack-Timeout), Rate-Limit (H5)
- [ ] P2.4.3 `POST /devices/:id/command` (nur `animation`/`text`/`clear`), `GET /devices/:id/animations`
- [ ] P2.4.4 `GET /api/events` (SSE) mit `device.status`, `device.state`
- [ ] P2.4.5 Firmware-Bundle-Proxy `/api/firmware/latest`, `/api/firmware/bundles/:file` (SHA-256 aus dem Release)
- [ ] P2.4.6 **Meilenstein-Test mit echtem Gerät:** Factory-Record per esptool-js-Webflasher manuell schreiben → Boot-Log `identity source=factory_data` → Gerät erscheint online

### P2.5 Web: Assistent & Geräte (2 Abende)
- [ ] P2.5.1 `/tabby/neu` Schritte 1–7 laut `webapp.md` §2.4 (esptool-js, `PROVISION` per Web Serial)
- [ ] P2.5.2 Update-Modus (ohne `factory_data` zu überschreiben)
- [ ] P2.5.3 `/tabby`: Geräteliste mit Live-Status, Textkarte senden, `CLEAR`
- [ ] P2.5.4 Animationsgalerie: Vorschauen einmalig aus den Upstream-GIFs als WebP erzeugen (CI-Skript), Kategorien, Suche
- [ ] P2.5.5 `/tabby/:id`: Umbenennen, Entkoppeln (mit Bestätigung)

### P2.6 Simulator (1 Abend, kann vor P0 fertig sein)
- [ ] P2.6.1 `/simulator`: Canvas 280 × 456, MQTT over WebSocket (`mqtt.js` im Browser), eigener Simulator-Zugang
- [ ] P2.6.2 Animationen (WebP), Text-, Auswahl- und Timer-Karten nachbauen, Klick → `event`
- [ ] P2.6.3 Integrationstests nutzen den Simulator als Gerät (Node-Variante ohne Canvas)

### P2.7 Abnahme
- [ ] Neues Board: Assistent von Anfang bis Ende in < 10 min
- [ ] Klick → Animation < 300 ms
- [ ] Router aus/an → Tabby wieder online ohne Eingriff, Status in der Web-App korrekt (≤ 45 s)
- [ ] Server-Neustart → Tabby verbindet sich allein neu
- [ ] Entkoppeln → sofort offline, erneuter Connect wird abgelehnt
- [ ] Im Heim-WLAN: `http://<tabby-ip>/cmd` ist nicht erreichbar, BLE nicht sichtbar

**✅ Done:** Tabby ist ein Cloud-Gerät. Einrichten, steuern und entkoppeln geht komplett aus dem Browser.

---

## Phase 3 – Produktiv-MVP

**Ziel:** Du nutzt Tabby jeden Tag für Aufgaben, Fokus und Erinnerungen.

### P3.1 Backend (2–3 Abende)
- [ ] P3.1.1 Tabellen `tasks`, `focus_sessions`, `reminders` + REST laut `backend.md` §3
- [ ] P3.1.2 **Device Director** (`backend.md` §5): Soll-Zustand berechnen, Diff senden, nach Reconnect alles neu senden. Unit-Tests für alle Prioritäten.
- [ ] P3.1.3 Event-Handling für Auswahlkarten (Kontexte `task`, `reminder`, `focus_end`, `break_end`)
- [ ] P3.1.4 Scheduler: `reminders.due`, `focus.ends`, `quiet.hours` (idempotent)
- [ ] P3.1.5 **FW-6** Helligkeit per MQTT, Ruhezeiten = `sleeping_loop` + dunkel
- [ ] P3.1.6 `/export`, `DELETE /me` (F-20)
- [ ] P3.1.7 Web-Push (VAPID) für Timer-Ende und Erinnerungen

### P3.2 Web (3 Abende)
- [ ] P3.2.1 **Heute**-Dashboard mit Schnelleingabe (`morgen`, `!hoch`, `@17:00`)
- [ ] P3.2.2 **Aufgaben** mit Tabs, Drag & Drop, „Jetzt dran“, Undo
- [ ] P3.2.3 **Fokus** mit Presets, Restzeit im Tab-Titel
- [ ] P3.2.4 **Erinnerungen** inkl. Wiederholung (täglich, werktags, wöchentlich)
- [ ] P3.2.5 **Einstellungen**: Zeitzone, Ruhezeiten, Helligkeit, Screensaver, Export, Konto löschen
- [ ] P3.2.6 PWA: Manifest, Icons, Service Worker

### P3.3 Tests & Abnahme (1 Abend)
- [ ] Playwright-E2E mit Simulator: Aufgabe anlegen → auf dem Gerät erledigen → im Browser erledigt
- [ ] **Alltagstest „ein Arbeitstag“:** 5 Aufgaben, 4 Pomodoros, 2 Erinnerungen, einmal WLAN weg
- [ ] Eine Woche Eigennutzung, Bugs als Issues sammeln

**✅ Done:** Eine Woche Alltag mit Tabby ohne Frust.

---

## Phase 4 – KI-Assistent

**Ziel:** Du sagst Tabby in normaler Sprache, was es tun soll. → [spec/ki.md](spec/ki.md)

- [ ] P4.1 API-Key anlegen (nur Server-Env), Billing-Limit beim Anbieter, Tabellen `ai_messages`, `ai_actions`, `ai_usage`
- [ ] P4.2 Tools als `betaZodTool` auf Basis der Service-Schicht, Tool Runner mit Streaming, `strict: true`, Zod-Validierung jedes Inputs
- [ ] P4.3 Bestätigungsflow (`ai_actions` pending → Karte im Browser **und** `UI/choice_2?ai:…` am Gerät)
- [ ] P4.4 Budget-Check vor jedem Aufruf, Verbrauch nach jedem Aufruf buchen, Anzeige in den Einstellungen
- [ ] P4.5 Prompt-Caching prüfen (`cache_read_input_tokens` > 0 ab dem zweiten Request)
- [ ] P4.6 Chat-UI mit Aktionskarten und Undo, Tabby zeigt `searching_loop` während der Antwort
- [ ] P4.7 „Plane meinen Tag“ mit Vorschau → Übernehmen → `day_planned`
- [ ] P4.8 Test-Suite mit 20 Prompts inkl. Prompt-Injection-Fall (`ki.md` §5)

**✅ Done:** „Leg mir für morgen drei Aufgaben an und starte jetzt 25 Minuten Fokus“ funktioniert, und eine „böse Notiz“ richtet nichts an.

---

## Phase 5 – Extras (Reihenfolge frei)

| Feature | Kernaufgaben |
|---|---|
| F-15 Gewohnheiten | Tabellen, UI, Streak-Karte, `trophy`/`perfect_day_01` bei Meilensteinen, `drink_water`/`stretching` als Erinnerungen |
| F-14 Notizen | Markdown-Editor, Suche, KI-Tool `search_notes` (Ergebnis in `<daten>`) |
| F-17 Kalender | ICS-Abruf im Scheduler, Termin-Erinnerungen, Einbindung in F-12 |
| F-16 Sprache | Push-to-Talk im Browser, Transkription, Übergabe an den Chat |
| F-19 Statistiken | Fokuszeit pro Tag/Woche, erledigte Aufgaben |
| F-18 OTA | App-Größe messen → neues Partitionslayout (ADR-0004) → signierte Updates, Rollback-Test |
| IMU-Spielerei | QMI8658 auslesen: Tabby umdrehen = Timer pausieren (Firmware-Erweiterung) |

---

## Laufende Pflichten (ab Phase 1)

- **Backups**: täglich automatisch, monatlich Restore-Probe
- **Updates**: Server automatisch, Abhängigkeiten per Dependabot, Upstream-Firmware vierteljährlich mergen
- **Kosten**: VPS fix, KI-Budget im Blick
- **Entscheidungen**: neue ADRs in `docs/adr/`

## Risiken & Gegenmaßnahmen

| Risiko | Wahrscheinlichkeit | Gegenmaßnahme |
|---|---|---|
| Es wird ein V2-Board statt V1 geliefert. | mittel | Beim Kauf nachfragen, V2 nicht flashen |
| Der Factory-Record wird nicht akzeptiert (CRC, Layout). | mittel | Früh testen (P2.4.6), Boot-Log lesen, Python-Referenz |
| Die Firmware hat keine einfache Stelle für Touch-Events. | niedrig | Auswahlkarten statt freier Gesten (F-08), FW-2b optional |
| Mosquitto kann das Caddy-Zertifikat nicht lesen. | mittel | Zertifikat per Cron kopieren und `chown` (infra.md §4) |
| Umlaute fehlen im Firmware-Font. | mittel | Früh testen, sonst `ä→ae` in der Text-Bereinigung |
| Die Upstream-Firmware ändert sich stark. | niedrig | git subtree, eigene Änderungen klein und hinter `CONFIG_TABBY_CLOUD` |
| Web Serial fehlt im Browser. | – | Einrichtung einmalig in Chrome/Edge, WLAN alternativ per Captive Portal |
| KI-Kosten laufen davon. | niedrig | Hartes Budget (K4), Billing-Limit beim Anbieter |
| AMOLED brennt ein. | niedrig | Ruhezeiten, `sleeping_loop`, keine stundenlang statischen Karten (H1) |
| Artwork-Lizenz verletzt | – | nur privat, Taby bleibt Taby (L2–L4) |
