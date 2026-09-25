# Hey Tabby Cloud – Konzept, Features & Guardrails

> Privates Spaßprojekt: ein Nachbau von [Hey Taby](https://www.heytaby.com/) als **reine Cloud- und Web-Version**.
> Auf dem PC wird nichts installiert. Die App läuft im Browser, und das physische Gerät spricht **direkt per WLAN mit der Cloud**, nicht per USB mit einer Desktop-App.

---

## 1. Ausgangslage: So funktioniert das Original

| Bereich | Original (Hey Taby) | Unsere Cloud-Version |
|---|---|---|
| App | Desktop-App (Mac/Win), die man installiert | Web-App/PWA im Browser |
| KI | lokale Gemma-Modelle (2B/4B/12B) auf dem Rechner | Claude API in der Cloud |
| Gerät ↔ App | USB-C/BLE zur Desktop-App, dazu „Taby Cloud“ per MQTT | WLAN → **MQTT über TLS** → eigener Broker in unserer Cloud |
| Hardware | Waveshare ESP32-S3 AMOLED (1,64" rechteckig oder 1,32" rund), Magnethalterung | identisch (**1,64" V1**), Upstream-Firmware mit kleinen Ergänzungen |
| Funktionen | Aufgaben, Notizen, Gewohnheiten, Fokus-Timer, Erinnerungen, Animationen | dieselben, dazu Fernsteuerung des Geräts aus dem Browser |

Offene Firmware: [TRIIIS-LABS/firmware-taby](https://github.com/TRIIIS-LABS/firmware-taby). Der Code und die Gehäuse stehen unter **Apache-2.0**. Für die Taby-Artwork (Gesicht, Animationen) gelten **eigene Bedingungen**: Die Nutzung in privaten Projekten ist erlaubt, solange Taby als Taby erkennbar bleibt. Man darf die Figur aber nicht als eigenes Produkt oder eigenen Charakter umlabeln (siehe Guardrails, Abschnitt 7).

> **Wichtigste Erkenntnis aus der Firmware-Analyse** ([spec/firmware.md](spec/firmware.md)): Die Upstream-Firmware bringt einen fertigen **MQTT-Cloud-Client** mit, dazu WLAN-Einrichtung per USB-Befehl oder Captive Portal und eine Befehlssprache für Animationen, Text-, Auswahl- und Timer-Karten. Wir müssen also **keinen eigenen Cloud-Client schreiben**, sondern nur die Broker-Adresse umbiegen und die Gerätezugangsdaten selbst erzeugen ([ADR-0001](adr/0001-mqtt-statt-websocket.md), [ADR-0002](adr/0002-identitaet-per-factory-record.md)).

---

## 2. Zielbild & Architektur

```
 ┌──────────────┐     HTTPS (REST + SSE)       ┌──────────────────────────────┐
 │  Browser     │ ◄──────────────────────────► │  Cloud (1 VPS, Docker)       │
 │  Web-App/PWA │                              │                              │
 │  (Desktop,   │                              │  Caddy   (TLS, Web, Proxy)   │
 │   Handy)     │                              │  API     (REST, SSE, Director│
 └──────────────┘                              │           Scheduler, KI)     │
        │ nur einmalig (Chrome/Edge):          │  Postgres                    │
        │ WebSerial → Flashen + WLAN           │  Mosquitto (MQTT-Broker)     │
        ▼                                      │  ─► Claude API (extern)      │
 ┌──────────────┐     MQTT über TLS :8883      └──────────────▲───────────────┘
 │ Physical     │ ────────────────────────────────────────────┘
 │ Tabby        │   Das Gerät baut die Verbindung selbst auf:
 │ ESP32-S3     │   keine offenen Ports am Gerät, kein PC nötig
 └──────────────┘
```

**Kernprinzipien**

1. **Cloud ist die Quelle der Wahrheit.** Aufgaben, Timer und Zustand liegen im Backend. Ein „Device Director“ entscheidet, was Tabby zeigt ([spec/backend.md](spec/backend.md) §5).
2. **Das Gerät verbindet sich immer ausgehend** per MQTT über TLS. Dadurch gibt es kein Port-Forwarding und keine lokale Bridge.
3. **Browser-only.** Flashen, Gerätezugang und WLAN-Einrichtung laufen im Browser (esptool-js + Web Serial). Das klappt nur mit Chrome/Edge und nur einmalig. Danach reicht jeder Browser, auch Safari oder das Handy. Die Firmware wird in GitHub Actions gebaut, lokal wird nichts installiert.
4. **Gerät bleibt offline nutzbar.** Animationen und ein laufender Timer funktionieren auch ohne Verbindung. Nach dem Reconnect sendet das Backend den Soll-Zustand neu.
5. **Nah an upstream bleiben.** Firmware-Änderungen sind minimal und abschaltbar (`CONFIG_TABBY_CLOUD`).

---

## 3. Hardware

Details, Einkaufsliste und Montage: **[spec/hardware.md](spec/hardware.md)**.

- **Waveshare ESP32-S3-Touch-AMOLED-1.64, Revision V1** (280×456, 16 MB Flash, 8 MB PSRAM, Touch, IMU, Akku-Anschluss, **kein Mikrofon/Lautsprecher**). ⚠️ V2 wird von der Firmware nicht unterstützt.
- USB-C-Datenkabel, USB-Netzteil, Neodym-Magnet 20 × 10 × 2 mm, Stahlplättchen, Gummifolie
- 3D-gedrucktes Upstream-Gehäuse (Base, Back, Handle)

### 3.1 Firmware-Plan

Details: **[spec/firmware.md](spec/firmware.md)**. Kurzfassung:

| ID | Änderung an der Upstream-Firmware |
|---|---|
| FW-1 | Broker-URI konfigurierbar (Kconfig) → unser `mqtts://mqtt.<domain>:8883` |
| FW-2 | Touch- und Auswahl-Events per MQTT melden (`devices/<id>/event`) |
| FW-3 | Lokalen HTTP-Server (ohne Auth) im Heim-WLAN abschalten |
| FW-4 | BLE im Cloud-Build abschalten (kein Bonding) |
| FW-5 | Last Will → Online/Offline-Status |
| FW-6 | Helligkeit per MQTT |
| FW-7 | eigene Build-Variante im CI |
| FW-8 | OTA: erst in Phase 5 untersuchen ([ADR-0004](adr/0004-kein-ota-im-mvp.md)) |

---

## 4. Cloud & Hosting

Details, Compose, Caddy- und Mosquitto-Konfiguration: **[spec/infra.md](spec/infra.md)**.

### 4.1 Empfehlung (Hobby, günstig, DSGVO-freundlich)

**Ein einzelner VPS in der EU** (z. B. Hetzner, kleinste Instanz) mit **Docker Compose**:

| Container | Aufgabe |
|---|---|
| `caddy` | automatisches HTTPS (Let's Encrypt), liefert die Web-App aus, Reverse Proxy für die API |
| `api` | REST + SSE für die Web-App, MQTT-Client für die Geräte, Scheduler, KI |
| `postgres` | Daten |
| `mosquitto` | MQTT-Broker mit TLS und Dynamic Security (ein Zugang pro Gerät, ACL pro Topic) |
| `backup` | täglicher verschlüsselter `pg_dump` in einen externen Speicher |

Kosten: ca. 5–16 € im Monat, inklusive KI-Budget.

### 4.2 Alternativen

| Option | Vorteil | Nachteil |
|---|---|---|
| **VPS + Compose** *(empfohlen)* | volle Kontrolle, MQTT-Port problemlos, fixe Kosten | Updates und Backups muss man selbst machen |
| Managed MQTT (z. B. HiveMQ Cloud, EMQX Cloud Free) + PaaS für die API | weniger Betrieb | mehr Anbieter, Free-Tier-Limits, Daten evtl. außerhalb der EU |
| Serverless (Cloudflare) | kein Server | MQTT-Broker trotzdem extern nötig |

### 4.3 Tech-Stack

Siehe [ADR-0003](adr/0003-stack.md): TypeScript, **SvelteKit** (Web), **Hono** + Drizzle + Zod (API), **Postgres**, **Mosquitto**, **Claude API**. Die Firmware bleibt C/ESP-IDF 5.4.2 wie upstream.

### 4.4 Repo-Struktur (Monorepo)

```
heytabbycloud/
├─ apps/
│  ├─ web/          # SvelteKit-PWA inkl. Einrichtungs-Assistent und Simulator
│  └─ api/          # Hono-API, MQTT-Client, Director, Scheduler, KI
├─ packages/
│  └─ protocol/     # Zod-Schemas, Befehls-Builder, Text-Bereinigung, Factory-Record
├─ firmware/        # Fork der Taby-Firmware (FW-1 … FW-8)
├─ infra/           # docker-compose.yml, Caddyfile, mosquitto.conf, Backup
└─ docs/            # Konzept, Features, Bauplan, spec/, adr/
```

---

## 5. Gerät ↔ Cloud: Protokoll & Gerätezugang

Details: **[spec/protocol.md](spec/protocol.md)**.

### 5.1 Transport: MQTT (Upstream-Protokoll)

| Topic | Richtung | Inhalt |
|---|---|---|
| `devices/<id>/cmd` | Cloud → Gerät | Textbefehl: Animations-ID, `UI/title_subtitle…`, `UI/choice_2…`, `UI/timer…`, `CLEAR` |
| `devices/<id>/ack` | Gerät → Cloud | Quittung `{ok, state, input, error?}` |
| `devices/<id>/state` | Gerät → Cloud | Zustand alle 15 s und bei Änderung |
| `devices/<id>/event` | Gerät → Cloud | **neu:** Touch-/Auswahl-Ereignisse |
| `devices/<id>/status` | Gerät → Cloud | **neu:** `online`/`offline` (Last Will) |

Ein Gerät darf nur seine eigenen Topics nutzen (ACL). Das Backend sendet nur Befehle aus einer **Allowlist** und bereinigt alle Nutzertexte.

### 5.2 Gerätezugang statt Pairing-Code

1. In der Web-App auf „Neues Tabby“ klicken: Das Backend erzeugt `device_id` und `device_secret` und legt den MQTT-Zugang an.
2. Der Browser baut daraus den **Factory-Record** (16 KB, mit CRC) und flasht ihn zusammen mit der Firmware per USB.
3. Die WLAN-Daten gehen per USB-Befehl `PROVISION` direkt an das Gerät und nie an den Server. Alternativ über das Captive Portal mit dem Handy.
4. Tabby verbindet sich mit dem Broker und ist sofort dem Konto zugeordnet, ohne Code.

Entkoppeln = MQTT-Zugang löschen. Das Gerät fliegt sofort raus.

---

## 6. Features

### 6.1 MVP (Phase 1–3)

**Web-App**
- Login (Magic-Link oder Passkey), ein Nutzer mit einem oder mehreren Geräten
- **Aufgaben**: anlegen, abhaken, priorisieren, „Jetzt dran“ markieren (erscheint auf dem Gerät)
- **Fokus-Timer** (Pomodoro): Start im Browser **oder** am Gerät, synchron auf beiden
- **Erinnerungen**: zeitbasiert, lösen am Gerät eine Animation aus (und optional eine Browser-Notification)
- **Geräte-Panel**: Online-Status, Animationen per Klick abspielen (Vorschau-Galerie), Helligkeit, Ruhezeiten
- **Einrichtungs-Assistent**: Flashen, Gerätezugang und WLAN, alles im Browser

**Gerät**
- zeigt Stimmung, aktuelle Aufgabe und Timer
- Touch-Gesten: Aufgabe erledigen, Timer starten/pausieren
- reagiert mit Animationen auf Ereignisse (Aufgabe erledigt → „happy“)

### 6.2 Phase 4: KI-Assistent

- **Chat in der Web-App**, der über **Tool-Use** echte Aktionen ausführt: `create_task`, `list_tasks`, `complete_task`, `start_timer`, `set_reminder`, `play_animation`
- **Tagesplanung**: „Plane meinen Tag“ erzeugt aus den offenen Aufgaben einen Vorschlag. Der Nutzer bestätigt ihn, erst dann wird er übernommen.
- **Gerät als Ausdruck**: Während die KI „denkt“, spielt eine Denk-Animation. Ist die Antwort fertig, zeigt das Gerät eine kurze Zusammenfassung.
- **Modell**: Standard ist `claude-opus-5` mit niedrigem Effort, per Env umstellbar auf `claude-sonnet-5` oder `claude-haiku-4-5`, falls dir die Kosten wichtiger sind (Details in [spec/ki.md](spec/ki.md)). Ein selbst gehostetes Modell wäre möglich, braucht aber einen GPU-Server und ist deutlich teurer.

### 6.3 Phase 5: Nice-to-have

- **Notizen** (Markdown), die die KI auch durchsuchen kann
- **Gewohnheiten/Habits** mit Streak-Anzeige auf dem Gerät
- **Sprache** per Push-to-Talk im Browser, Transkription über eine Cloud-API
- **Kalender-Import** (ICS-URL, nur lesend), damit das Gerät vor Terminen erinnert
- **OTA-Updates** aus der Web-App (vorher Partitionslayout klären, [ADR-0004](adr/0004-kein-ota-im-mvp.md))
- **Statistiken**: Fokuszeit pro Tag/Woche
- **Mehrere Geräte** (Schreibtisch + Regal), eines davon als „primär“

### 6.4 Bewusst nicht im Umfang (Non-Goals)

- keine native Desktop- oder Mobile-App
- kein Multi-Tenant-SaaS, kein Verkauf, keine Zahlungsabwicklung
- kein dauerhaft lauschendes Mikrofon / kein Wake-Word am Gerät
- keine Kamera

---

## 7. Guardrails

### 7.1 Sicherheit

| # | Regel |
|---|---|
| S1 | **TLS überall.** Das Gerät prüft das Broker-Zertifikat (ESP-IDF-Zertifikats-Bundle). MQTT ohne TLS nur im internen Docker-Netz, nie nach außen. |
| S2 | **Das Gerät öffnet keine Ports.** Keine lokale HTTP-API im Cloud-Modus, nur ausgehende Verbindungen. |
| S3 | **Eigener Zugang pro Gerät** (`device_id` + `device_secret`), widerrufbar in der Web-App. Das Secret wird nur einmal ausgegeben und liegt im Broker nur als Hash. ACL: Ein Gerät darf nur `devices/<eigene-id>/…` nutzen. |
| S4 | **Das Gerät führt nur Befehle aus einer festen Liste aus** (Abschnitt 5.3). Befehle werden gegen das Schema validiert, alles andere wird verworfen. Es gibt keinen „beliebigen Code/Text ausführen“-Befehl. |
| S5 | **Geräte-Secret** nur im Browser-Speicher während des Flashens, nie in `localStorage`, nie geloggt. **WLAN-Passwort** geht nur per USB ans Gerät, nie an den Server. |
| S6 | **Firmware nur aus unserem CI**, mit SHA-256-Prüfung vor dem Flashen. Falls OTA kommt: nur signiert, mit A/B-Partition und Rollback. |
| S7 | **Web-Sicherheit**: Session-Cookies `HttpOnly`/`Secure`/`SameSite`, CSRF-Schutz, strenge CSP, Rate-Limits auf Login und API |
| S8 | **Secrets** (API-Keys, DB-Passwort) nur als Env-Variablen auf dem Server, **nie** im Repo oder in der Firmware. Ein Secret-Scan im CI ist Pflicht. |
| S9 | Server-Härtung: nur die Ports 22 (Key-only), 80 und 443; automatische Sicherheitsupdates; Firewall |

### 7.2 Datenschutz (DSGVO, auch privat sinnvoll)

| # | Regel |
|---|---|
| D1 | Hosting in der **EU** |
| D2 | **Datensparsamkeit**: Es werden nur Aufgaben, Notizen, Timer und Geräte-Metadaten gespeichert. Keine Audio-Aufnahmen speichern, nur die Transkripte, und auch die nur, wenn gewünscht. |
| D3 | **Mikrofon nur per Push-to-Talk im Browser** mit sichtbarem Aufnahme-Indikator |
| D4 | An die KI gehen nur die Daten, die für die Anfrage nötig sind. Anbieter mit klarer Retention-Policy wählen und die Policy dokumentieren. |
| D5 | **Export und Löschen** aller eigenen Daten mit einem Klick |
| D6 | Logs ohne Inhalte (keine Aufgabentexte oder Prompts im Klartext), Aufbewahrung max. 14 Tage |

### 7.3 KI-Guardrails

| # | Regel |
|---|---|
| K1 | **Tool-Allowlist**: Die KI kann nur die definierten Tools aufrufen. Jedes Tool prüft Berechtigung und Schema serverseitig. |
| K2 | **Bestätigung bei Destruktivem**: Löschen, Massenänderungen und das Überschreiben eines Tagesplans erst nach einem Klick des Nutzers |
| K3 | **Prompt-Injection**: Inhalte aus Notizen, Kalendern oder importierten Texten gelten als *Daten*, nicht als Anweisungen. Sie werden im Prompt klar abgegrenzt, und Tool-Aufrufe, die aus solchen Inhalten entstehen, bestätigt der Nutzer. |
| K4 | **Kostendeckel**: Token-Budget pro Tag und Monat, hartes Limit im Backend und Warnung bei 80 % |
| K5 | **Ausgabe fürs Display**: Texte auf dem Gerät werden hart gekürzt (Zeichen-Limit) und bereinigt (keine Steuerzeichen, keine Markup-Reste). |
| K6 | **Kein Autopilot**: Die KI handelt nur auf eine Nutzeranfrage hin. Geplante Aktionen legt nur der Nutzer an. |
| K7 | Timeout und Fallback: Ist die KI nicht erreichbar, funktioniert der Rest der App normal weiter. |

### 7.4 Hardware & Gerät

| # | Regel |
|---|---|
| H1 | **AMOLED-Burn-in vermeiden**: Dimmen oder Screensaver nach Inaktivität, Ruhezeiten (z. B. 22–7 Uhr), keine statischen Elemente dauerhaft auf voller Helligkeit |
| H2 | **Watchdog** in der Firmware. Reconnect mit exponentiellem Backoff und Jitter, damit der Server nicht geflutet wird. |
| H3 | **Offline-Modus**: Timer mit absoluter Endzeit laufen lokal weiter. Das Gerät zeigt dezent „offline“ an und stürzt nicht ab. |
| H4 | **Stromversorgung**: nur ordentliche 5-V-USB-Netzteile. Bei Akkubetrieb nur geschützte Zellen, kein Laden unbeaufsichtigt im Gehäuse ohne Belüftung. |
| H5 | **Rate-Limit für Gerätebefehle** (z. B. max. 5 Befehle pro Sekunde), damit die Web-App oder die KI das Gerät nicht „spammen“ kann |
| H6 | Werksreset: WLAN-Daten löschen (upstream `WIFI_FORGET`) und in der Web-App entkoppeln (widerruft den Zugang). |

### 7.5 Lizenz & Marke

| # | Regel |
|---|---|
| L1 | Firmware-Fork: Apache-2.0-Lizenztext und `NOTICE` behalten, eigene Änderungen kennzeichnen |
| L2 | **Taby-Artwork** nur privat nutzen, Taby als Taby lassen, nicht als eigenen Charakter oder eigenes Produkt ausgeben. Bei Veröffentlichung auf das Original verweisen. |
| L3 | Keine Nutzung von Name oder Logo „Hey Taby“ für ein öffentliches Angebot. Das Projekt heißt intern „Hey Tabby Cloud“ und bleibt ein privater Nachbau. |
| L4 | Soll das Projekt je öffentlich oder kommerziell werden, braucht es **eigene Artwork**, und die Hersteller sollten vorher gefragt werden. |
| L5 | Die **Desktop-App** des Originals ist proprietär. Sie darf zum Testen genutzt werden, wird aber **nicht** dekompiliert, und es werden keine Inhalte daraus extrahiert. Alles, was wir brauchen, steht in der offenen Firmware (Apache-2.0). |

### 7.6 Kosten

| # | Regel |
|---|---|
| C1 | Fixkosten-Ziel: im niedrigen einstelligen Euro-Bereich pro Monat für den VPS, plus nutzungsabhängige KI-Kosten |
| C2 | Hartes KI-Budget (K4), dazu ein Billing-Alert beim Anbieter |
| C3 | Keine Managed-Dienste mit Mindestgebühr, solange sie nicht nötig sind |

### 7.7 Engineering

| # | Regel |
|---|---|
| E1 | Das Protokoll ist versioniert (`v`-Feld). Änderungen sind abwärtskompatibel oder erhöhen die Version. |
| E2 | Ein Schema (`packages/protocol`) ist die einzige Quelle für API, Web und Firmware. |
| E3 | CI: Lint, Typecheck, Tests, Secret-Scan. Firmware-Build als CI-Artefakt. |
| E4 | Eine **Simulator**-Seite in der Web-App (virtuelles Tabby im Browser), damit sich Backend und Web ohne Hardware entwickeln lassen |
| E5 | Architekturentscheidungen als kurze ADRs in `docs/adr/` |

---

## 8. Roadmap

> Details: [FEATURES.md](FEATURES.md) (Feature-Katalog) und [BAUPLAN.md](BAUPLAN.md) (Arbeitsschritte je Phase).

| Phase | Ziel | Ergebnis / „Done“ |
|---|---|---|
| **0 – Hardware-Bring-up** | Board kaufen, Original-Firmware flashen, Gehäuse drucken | Animation läuft auf dem Gerät |
| **1 – Cloud-Skelett** | VPS, Compose, Caddy, API mit Health-Check, DB, Login | `https://<domain>` erreichbar, Login funktioniert |
| **2 – Gerät online** | Mosquitto, Firmware-Fork (FW-1…FW-5), Einrichtungs-Assistent, Director-Grundgerüst | Klick im Browser → Animation am Gerät (< 300 ms) |
| **3 – Produktiv-MVP** | Aufgaben, Fokus-Timer, Erinnerungen, Touch-Gesten, Simulator | Tabby ist im Alltag nutzbar |
| **4 – KI** | Chat mit Tool-Use, Tagesplanung, Kostendeckel | „Leg mir drei Aufgaben für morgen an“ funktioniert |
| **5 – Extras** | Notizen, Habits, Push-to-Talk, OTA, Kalender, Statistiken | nach Lust und Laune |

---

## 9. Offene Entscheidungen

Vorläufig entschieden (siehe [ADR-0003](adr/0003-stack.md), änderbar bis Phase 1):
SvelteKit · VPS mit Docker Compose · Claude API · Board 1,64" V1 · MQTT/Mosquitto.

Noch offen:
1. **Domain** für Web-App und Broker (`tabby.<domain>`, `mqtt.<domain>`)
2. **KI-Modell**: `claude-opus-5` (Standard) oder günstiger (`claude-sonnet-5`/`claude-haiku-4-5`), am besten nach einer Woche Kostenmessung entscheiden
3. **Gehäuse-Druck**: eigener Drucker, Makerspace oder Druckdienst?

---

## Quellen

- [Hey Taby: Website](https://www.heytaby.com/) · [Setup](https://www.heytaby.com/setup) · [Modelle](https://www.heytaby.com/models) · [Physical Taby / DIY](https://www.heytaby.com/diy-kit)
- [TRIIIS-LABS/firmware-taby](https://github.com/TRIIIS-LABS/firmware-taby) (Firmware, Animationen, Gehäuse, Lizenzhinweise)
- [esptool-js](https://github.com/espressif/esptool-js) · [Web Serial API](https://developer.mozilla.org/docs/Web/API/Web_Serial_API) · [Mosquitto Dynamic Security](https://mosquitto.org/documentation/dynamic-security/)
- [Waveshare ESP32-S3-Touch-AMOLED-1.64](https://www.waveshare.com/esp32-s3-touch-amoled-1.64.htm)
