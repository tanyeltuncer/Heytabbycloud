# Hey Tabby Cloud – Konzept, Features & Guardrails

> Privates Spaßprojekt: ein Nachbau von [Hey Taby](https://www.heytaby.com/) als **reine Cloud- und Web-Version**.
> Auf dem PC wird nichts installiert. Die App läuft im Browser, und das physische Gerät spricht **direkt per WLAN mit der Cloud**, nicht per USB mit einer Desktop-App.

---

## 1. Ausgangslage: So funktioniert das Original

| Bereich | Original (Hey Taby) | Unsere Cloud-Version |
|---|---|---|
| App | Desktop-App (Mac/Win), die man installiert | Web-App/PWA im Browser |
| KI | lokale Gemma-Modelle (2B/4B/12B) auf dem Rechner | KI-API in der Cloud (z. B. Claude) oder ein selbst gehostetes Modell |
| Gerät ↔ App | USB-C (auch BLE/WLAN-Befehle) zur Desktop-App | WLAN → WebSocket (TLS) → Cloud-Backend |
| Hardware | Waveshare ESP32-S3 AMOLED (1,64" rechteckig oder 1,32" rund), Magnethalterung | identisch, Firmware wird um einen Cloud-Client erweitert |
| Funktionen | Aufgaben, Notizen, Gewohnheiten, Fokus-Timer, Erinnerungen, Animationen | dieselben, dazu Fernsteuerung des Geräts aus dem Browser |

Offene Firmware: [TRIIIS-LABS/firmware-taby](https://github.com/TRIIIS-LABS/firmware-taby). Der Code und die Gehäuse stehen unter **Apache-2.0**. Für die Taby-Artwork (Gesicht, Animationen) gelten **eigene Bedingungen**: Die Nutzung in privaten Projekten ist erlaubt, solange Taby als Taby erkennbar bleibt. Man darf die Figur aber nicht als eigenes Produkt oder eigenen Charakter umlabeln (siehe Guardrails, Abschnitt 7).

---

## 2. Zielbild & Architektur

```
 ┌──────────────┐         HTTPS / WSS          ┌─────────────────────────────┐
 │  Browser     │ ◄──────────────────────────► │  Cloud (1 VPS, Docker)      │
 │  Web-App/PWA │                              │                             │
 │  (Desktop,   │                              │  Caddy (TLS, Reverse Proxy) │
 │   Handy)     │                              │  API + Realtime-Gateway     │
 └──────────────┘                              │  Worker (Timer/Reminder)    │
        │ nur einmalig:                        │  Postgres                   │
        │ WebSerial (Flashen + WLAN-Setup)     │  ─► LLM-API (extern)        │
        ▼                                      └──────────────▲──────────────┘
 ┌──────────────┐          WSS (ausgehend)                    │
 │ Physical     │ ────────────────────────────────────────────┘
 │ Tabby        │   Gerät baut die Verbindung selbst auf,
 │ ESP32-S3     │   keine offenen Ports, kein PC nötig
 └──────────────┘
```

**Kernprinzipien**

1. **Cloud ist die Quelle der Wahrheit.** Aufgaben, Timer und Zustand liegen im Backend. Browser und Gerät sind nur „Views“ und „Controller“.
2. **Das Gerät verbindet sich immer ausgehend** per WSS. Dadurch gibt es kein Port-Forwarding und keine lokale Bridge.
3. **Browser-only.** Auch Flashen und WLAN-Einrichtung laufen im Browser (WebSerial via [ESP Web Tools](https://esphome.github.io/esp-web-tools/) + [Improv WiFi](https://www.improv-wifi.com/)). Das klappt nur mit Chrome/Edge und nur einmalig. Danach reicht jeder Browser, auch Safari oder das Handy.
4. **Gerät bleibt offline nutzbar.** Ein laufender Fokus-Timer und die Animationen funktionieren auch ohne Verbindung. Nach dem Reconnect wird der Zustand synchronisiert.

---

## 3. Hardware

### 3.1 Stückliste (Taby 1.64, Empfehlung)

| Teil | Hinweis |
|---|---|
| Waveshare **ESP32-S3-Touch-AMOLED-1.64** (280×456) | Hauptplatine mit Touch, WLAN und BLE. Die Firmware hat hier die meisten Animationen (84). |
| USB-C-**Datenkabel** | Wird nur zum ersten Flashen gebraucht, danach reicht ein USB-Netzteil. |
| Neodym-Blockmagnet 20 × 10 × 2 mm + Stahlplättchen | Magnethalterung wie beim Original |
| Rutschfeste Gummiauflage | Unterseite |
| 3D-Druck-Gehäuse (Base, Back, Handle) | Dateien aus dem Firmware-Repo, PLA oder PETG |
| *optional* USB-Netzteil 5 V / 1 A | Damit läuft das Gerät dauerhaft ohne PC. |

Alternative: **ESP32-S3-Touch-AMOLED-1.32** (rund, 466×466). Dafür gibt es aber weniger Animationen, und die Gehäusedateien fehlen noch.

### 3.2 Hardware-Fragen vor dem Kauf

- [ ] Hat das Board ein **Mikrofon oder einen Lautsprecher**? Das steht im Waveshare-Datenblatt. Falls nicht, läuft Sprache über das Browser-Mikrofon (sowieso die bevorzugte Variante, siehe Guardrails).
- [ ] Gibt es einen **Akku-Anschluss**? Wenn ja: nur Zellen mit Schutzschaltung verwenden.
- [ ] Gibt es eine **IMU** (Lage-/Bewegungssensor)? Damit wäre „Antippen/Umdrehen = Timer pausieren“ möglich.

### 3.3 Firmware-Plan

- Das offizielle Repo **forken** (Apache-2.0, Lizenz und NOTICE bleiben erhalten).
- Ein neues Modul `cloud_client` ergänzen:
  - WLAN-Provisioning per **Improv** (seriell) und optional per BLE
  - **WSS-Client** mit TLS und gepinnter CA, Heartbeat und exponentiellem Backoff beim Reconnect
  - einen **Pairing-Flow** (siehe Abschnitt 5.2)
  - Mapping der Cloud-Nachrichten auf die bestehenden „device commands“ der Firmware
- Die bestehende USB-Befehlsschnittstelle bleibt erhalten. Sie ist nützlich zum Debuggen und für WebSerial.
- **OTA-Updates** laufen über zwei App-Partitionen (A/B) mit Rollback, wenn der Boot fehlschlägt.

---

## 4. Cloud & Hosting

### 4.1 Empfehlung (Hobby, günstig, DSGVO-freundlich)

**Ein einzelner VPS in der EU** (z. B. Hetzner, kleinste Instanz) mit **Docker Compose**:

| Container | Aufgabe |
|---|---|
| `caddy` | automatisches HTTPS (Let's Encrypt), Reverse Proxy |
| `api` | REST-/RPC-API für die Web-App und WebSocket-Gateway für Geräte und Browser |
| `worker` | Timer, Erinnerungen, geplante Jobs (DB-basierte Queue) |
| `postgres` | Daten |
| `web` | statisch gebaute Web-App (alternativ direkt über Caddy ausgeliefert) |

Backups: täglicher `pg_dump`, verschlüsselt, in einen externen Object Storage.

### 4.2 Alternativen

| Option | Vorteil | Nachteil |
|---|---|---|
| **VPS + Compose** *(empfohlen)* | volle Kontrolle, WebSockets problemlos, fixe Kosten | Updates und Backups muss man selbst machen |
| Fly.io / Railway | einfaches Deploy | WebSocket-Limits und Kosten beachten |
| Cloudflare Workers + Durable Objects + D1 | Serverless, Realtime pro Gerät elegant | Vendor-Lock-in, andere Programmierlogik |
| Supabase (Auth + Postgres + Realtime) + kleiner Gateway-Dienst | Auth und DB fertig | Das Gerät braucht trotzdem einen eigenen Gateway |

### 4.3 Tech-Stack (Vorschlag, TypeScript durchgängig)

- **Backend:** Node.js + [Hono](https://hono.dev/) oder Fastify, `ws` für WebSockets, Drizzle ORM, Zod für Schemas
- **Frontend:** SvelteKit oder Next.js als **PWA** (installierbar ohne App Store, also auch „keine Installation“ im klassischen Sinn)
- **Shared:** Paket `protocol` mit Zod-Schemas für alle Gerätenachrichten. Daraus werden auch C-Header oder JSON-Schema für die Firmware generiert.
- **Firmware:** PlatformIO oder ESP-IDF (je nachdem, was das Upstream-Repo nutzt)

### 4.4 Repo-Struktur (Monorepo)

```
heytabbycloud/
├─ apps/
│  ├─ web/          # Web-App (PWA)
│  └─ api/          # API, WS-Gateway, Worker
├─ packages/
│  └─ protocol/     # Nachrichten-Schemas (Zod) + generierte Firmware-Header
├─ firmware/        # Fork der Taby-Firmware + cloud_client
├─ infra/           # docker-compose.yml, Caddyfile, Backup-Skripte
└─ docs/            # dieses Konzept, Protokoll-Spec, ADRs
```

---

## 5. Gerät ↔ Cloud: Protokoll & Pairing

### 5.1 Transport

- **WSS** auf `wss://<domain>/device`, JSON-Nachrichten (klein, Firmware-freundlich)
- Jede Nachricht: `{ "v": 1, "type": "...", "id": "<msg-id>", "data": { ... } }`
- **Ack** für wichtige Befehle: Das Gerät antwortet mit `{ "type": "ack", "ref": "<msg-id>" }`.
- Heartbeat alle 30 s. Nach 90 s ohne Heartbeat gilt das Gerät als „offline“.
- *Alternative:* MQTT über TLS mit einem Broker (Mosquitto/EMQX). Das lohnt sich erst bei vielen Geräten.

### 5.2 Pairing (ohne PC-Software)

1. Das Gerät ist frisch geflasht und bekommt per Improv (im Browser) die WLAN-Daten.
2. Das Gerät verbindet sich mit der Cloud, fragt einen Code an und zeigt einen **6-stelligen Pairing-Code** (plus QR) auf dem Display.
3. Der Nutzer ist in der Web-App eingeloggt und gibt den Code ein. Dadurch wird das Gerät dem Konto zugeordnet.
4. Die Cloud stellt ein **gerätespezifisches Token** aus. Das Gerät speichert es in NVS (verschlüsselt, falls Flash-Encryption aktiv ist).
5. Der Code ist **5 Minuten gültig**, nur einmal nutzbar und hat ein Rate-Limit gegen Brute-Force.

### 5.3 Nachrichtentypen (v1)

**Cloud → Gerät**

| type | data | Wirkung |
|---|---|---|
| `animation.play` | `{ name, loop? }` | spielt eine Animation ab (unbekannte Namen werden ignoriert, wie upstream) |
| `face.state` | `{ mood: idle\|happy\|focus\|sleepy\|alert }` | Grundstimmung |
| `text.show` | `{ text, ttl_s }` | kurzer Text, z. B. die nächste Aufgabe (max. ~60 Zeichen) |
| `timer.start` / `timer.pause` / `timer.stop` | `{ ends_at, label }` | Fokus-Timer, Endzeit absolut (bleibt auch offline korrekt) |
| `reminder.fire` | `{ title }` | Erinnerung mit Animation |
| `task.current` | `{ id, title, done }` | aktuelle Aufgabe anzeigen |
| `settings.set` | `{ brightness, quiet_hours, ... }` | Einstellungen |
| `ota.available` | `{ version, url, sha256, sig }` | Firmware-Update |

**Gerät → Cloud**

| type | data | Bedeutung |
|---|---|---|
| `hello` | `{ fw, board, caps[], animations[] }` | Anmeldung und Fähigkeiten, damit die Web-App nur Passendes anbietet |
| `heartbeat` | `{ rssi, uptime, heap }` | Gesundheitsdaten |
| `touch` | `{ gesture: tap\|double\|long\|swipe }` | Eingabe, z. B. Tap = Aufgabe erledigt, Long = Timer starten |
| `timer.state` | `{ state, remaining_s }` | Sync nach dem Reconnect |
| `ack` / `error` | `{ ref, code? }` | Quittung |

---

## 6. Features

### 6.1 MVP (Phase 1–3)

**Web-App**
- Login (Magic-Link oder Passkey), ein Nutzer mit einem oder mehreren Geräten
- **Aufgaben**: anlegen, abhaken, priorisieren, „Jetzt dran“ markieren (erscheint auf dem Gerät)
- **Fokus-Timer** (Pomodoro): Start im Browser **oder** am Gerät, synchron auf beiden
- **Erinnerungen**: zeitbasiert, lösen am Gerät eine Animation aus (und optional eine Browser-Notification)
- **Geräte-Panel**: Online-Status, Animationen per Klick abspielen (Vorschau-Galerie), Helligkeit, Ruhezeiten
- **Einrichtungs-Assistent**: Flashen, WLAN, Pairing, alles im Browser

**Gerät**
- zeigt Stimmung, aktuelle Aufgabe und Timer
- Touch-Gesten: Aufgabe erledigen, Timer starten/pausieren
- reagiert mit Animationen auf Ereignisse (Aufgabe erledigt → „happy“)

### 6.2 Phase 4: KI-Assistent

- **Chat in der Web-App**, der über **Tool-Use** echte Aktionen ausführt: `create_task`, `list_tasks`, `complete_task`, `start_timer`, `set_reminder`, `play_animation`
- **Tagesplanung**: „Plane meinen Tag“ erzeugt aus den offenen Aufgaben einen Vorschlag. Der Nutzer bestätigt ihn, erst dann wird er übernommen.
- **Gerät als Ausdruck**: Während die KI „denkt“, spielt eine Denk-Animation. Ist die Antwort fertig, zeigt das Gerät eine kurze Zusammenfassung.
- **Modellwahl**: ein kleines, schnelles Modell für Alltägliches (z. B. Claude Haiku 4.5), ein größeres für Planung (z. B. Claude Sonnet 5). Alternativ ein selbst gehostetes Open-Weight-Modell (Gemma via Ollama), was aber einen GPU-Server braucht und deutlich teurer ist.

### 6.3 Phase 5: Nice-to-have

- **Notizen** (Markdown), die die KI auch durchsuchen kann
- **Gewohnheiten/Habits** mit Streak-Anzeige auf dem Gerät
- **Sprache** per Push-to-Talk im Browser, Transkription über eine Cloud-API
- **Kalender-Import** (ICS-URL, nur lesend), damit das Gerät vor Terminen erinnert
- **OTA-Updates** aus der Web-App
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
| S1 | **TLS überall.** Das Gerät prüft das Server-Zertifikat (CA gepinnt). Kein unverschlüsseltes WS, auch nicht „nur zum Testen“ im Deployment. |
| S2 | **Das Gerät öffnet keine Ports.** Keine lokale HTTP-API im Cloud-Modus, nur ausgehende Verbindungen. |
| S3 | **Token pro Gerät**, widerrufbar in der Web-App. Tokens liegen in der DB nur als Hash. Ein Gerät darf nur seinen eigenen Kanal nutzen. |
| S4 | **Das Gerät führt nur Befehle aus einer festen Liste aus** (Abschnitt 5.3). Befehle werden gegen das Schema validiert, alles andere wird verworfen. Es gibt keinen „beliebigen Code/Text ausführen“-Befehl. |
| S5 | **Pairing-Codes**: 5 min TTL, nur einmal gültig, Rate-Limit pro IP und Konto |
| S6 | **OTA nur signiert** (SHA-256 + Signatur), mit A/B-Partition und automatischem Rollback |
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
| H6 | Werksreset per Touch-Geste beim Booten. Er löscht WLAN-Daten und Token. |

### 7.5 Lizenz & Marke

| # | Regel |
|---|---|
| L1 | Firmware-Fork: Apache-2.0-Lizenztext und `NOTICE` behalten, eigene Änderungen kennzeichnen |
| L2 | **Taby-Artwork** nur privat nutzen, Taby als Taby lassen, nicht als eigenen Charakter oder eigenes Produkt ausgeben. Bei Veröffentlichung auf das Original verweisen. |
| L3 | Keine Nutzung von Name oder Logo „Hey Taby“ für ein öffentliches Angebot. Das Projekt heißt intern „Hey Tabby Cloud“ und bleibt ein privater Nachbau. |
| L4 | Soll das Projekt je öffentlich oder kommerziell werden, braucht es **eigene Artwork**, und die Hersteller sollten vorher gefragt werden. |

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

| Phase | Ziel | Ergebnis / „Done“ |
|---|---|---|
| **0 – Hardware-Bring-up** | Board kaufen, Original-Firmware flashen, Gehäuse drucken | Animation läuft auf dem Gerät |
| **1 – Cloud-Skelett** | VPS, Compose, Caddy, API mit Health-Check, DB, Login | `https://<domain>` erreichbar, Login funktioniert |
| **2 – Gerät online** | `cloud_client` in der Firmware, Improv-WLAN, Pairing, `hello`/`heartbeat`, `animation.play` | Klick im Browser → Animation am Gerät (< 300 ms) |
| **3 – Produktiv-MVP** | Aufgaben, Fokus-Timer, Erinnerungen, Touch-Gesten, Simulator | Tabby ist im Alltag nutzbar |
| **4 – KI** | Chat mit Tool-Use, Tagesplanung, Kostendeckel | „Leg mir drei Aufgaben für morgen an“ funktioniert |
| **5 – Extras** | Notizen, Habits, Push-to-Talk, OTA, Kalender, Statistiken | nach Lust und Laune |

---

## 9. Offene Entscheidungen

1. **Frontend-Framework**: SvelteKit (leichtgewichtig) oder Next.js (größeres Ökosystem)?
2. **Hosting**: VPS (empfohlen) oder Serverless (Cloudflare)?
3. **KI-Anbieter**: Cloud-API (günstig, einfach) oder selbst gehostetes Modell (privater, aber teuer)?
4. **Board**: 1,64" rechteckig (empfohlen, mehr Animationen) oder 1,32" rund?
5. **Domain** für die Web-App?

---

## Quellen

- [Hey Taby: Website](https://www.heytaby.com/) · [Setup](https://www.heytaby.com/setup) · [Modelle](https://www.heytaby.com/models) · [Physical Taby / DIY](https://www.heytaby.com/diy-kit)
- [TRIIIS-LABS/firmware-taby](https://github.com/TRIIIS-LABS/firmware-taby) (Firmware, Animationen, Gehäuse, Lizenzhinweise)
- [ESP Web Tools](https://esphome.github.io/esp-web-tools/) · [Improv WiFi](https://www.improv-wifi.com/)
