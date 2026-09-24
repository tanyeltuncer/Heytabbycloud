# Spec: Infrastruktur & Betrieb

## 1. Server

| Punkt | Wahl |
|---|---|
| Anbieter | Hetzner Cloud (oder vergleichbar), Standort Nürnberg/Falkenstein/Helsinki |
| Größe | kleinste x86- oder ARM-Instanz (2 vCPU, 4 GB RAM) |
| OS | Ubuntu 24.04 LTS |
| Domains | `tabby.<domain>` (Web + API), `mqtt.<domain>` (Broker) |
| Firewall | 22 (nur SSH-Key), 80, 443, **8883** (MQTT over TLS) |

## 2. Container (`infra/docker-compose.yml`)

```yaml
services:
  caddy:
    image: caddy:2
    ports: ["80:80", "443:443"]
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy_data:/data            # enthält auch das Zertifikat für mqtt.<domain>
      - ./web-dist:/srv/web:ro
    restart: unless-stopped

  api:
    image: ghcr.io/tanyeltuncer/heytabbycloud-api:${TAG:-latest}
    env_file: .env
    depends_on: [postgres, mosquitto]
    restart: unless-stopped

  postgres:
    image: postgres:17
    environment:
      POSTGRES_DB: tabby
      POSTGRES_USER: tabby
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes: [pg_data:/var/lib/postgresql/data]
    restart: unless-stopped

  mosquitto:
    image: eclipse-mosquitto:2
    ports: ["8883:8883"]
    volumes:
      - ./mosquitto.conf:/mosquitto/config/mosquitto.conf:ro
      - mosquitto_data:/mosquitto/data   # dynamic-security.json
      - caddy_data:/certs:ro             # Zertifikat von Caddy mitbenutzen
    restart: unless-stopped

  backup:
    image: ghcr.io/tanyeltuncer/heytabbycloud-backup:${TAG:-latest}   # pg_dump + age + rclone, Cron 03:30
    env_file: .env.backup
    depends_on: [postgres]
    restart: unless-stopped

volumes: { caddy_data: {}, pg_data: {}, mosquitto_data: {} }
```

## 3. Caddyfile

```
tabby.{$DOMAIN} {
    encode zstd gzip
    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains"
        X-Content-Type-Options nosniff
        Referrer-Policy strict-origin-when-cross-origin
        Content-Security-Policy "default-src 'self'; img-src 'self' data: blob:; connect-src 'self' wss://mqtt.{$DOMAIN}; style-src 'self' 'unsafe-inline'; frame-ancestors 'none'"
        Permissions-Policy "microphone=(self), camera=(), geolocation=()"
    }
    handle /api/* { reverse_proxy api:3000 }
    handle { root * /srv/web; try_files {path} /index.html; file_server }
}

mqtt.{$DOMAIN} {
    # Nur für das Zertifikat und MQTT-over-WebSocket (Simulator)
    reverse_proxy /mqtt mosquitto:9001
}
```

## 4. Mosquitto (`infra/mosquitto.conf`)

```
per_listener_settings false
persistence true
persistence_location /mosquitto/data/

# Geräte: MQTT über TLS
listener 8883
certfile /certs/caddy/certificates/acme-v02.api.letsencrypt.org-directory/mqtt.<domain>/mqtt.<domain>.crt
keyfile  /certs/caddy/certificates/acme-v02.api.letsencrypt.org-directory/mqtt.<domain>/mqtt.<domain>.key

# Simulator: WebSocket, nur intern (TLS terminiert Caddy)
listener 9001
protocol websockets

# Backend: nur im Docker-Netz, ohne TLS
listener 1883 0.0.0.0

allow_anonymous false
plugin /usr/lib/mosquitto_dynamic_security.so
plugin_opt_config_file /mosquitto/data/dynamic-security.json
```

- **Zertifikatserneuerung:** Caddy erneuert das Zertifikat. Mosquitto lädt es per `SIGHUP` neu, ein wöchentlicher Cron-Job erledigt das (`docker compose kill -s HUP mosquitto`).
- Die Firmware prüft das Zertifikat mit dem ESP-IDF-Zertifikats-Bundle. Let's Encrypt (ISRG Root X1) ist darin enthalten.
- Initialisierung: `mosquitto_ctrl dynsec init …` erstellt den Admin. Danach legt die API die Rollen `device` und `api` an (idempotentes Setup-Skript `infra/dynsec-bootstrap.sh`).
- Port 1883 wird **nicht** nach außen veröffentlicht (kein `ports:`-Eintrag).
- Achtung Dateirechte: Mosquitto läuft als UID 1883 und muss das Zertifikat aus `caddy_data` lesen können. Alternativ kopiert ein kleiner Cron-Job Zertifikat und Key in ein eigenes Volume (`chown 1883`).

## 5. Umgebungsvariablen (`.env.example`)

```
DOMAIN=example.org
PUBLIC_URL=https://tabby.example.org
DATABASE_URL=postgres://tabby:***@postgres:5432/tabby
POSTGRES_PASSWORD=***
MQTT_URL=mqtt://mosquitto:1883
MQTT_API_USER=tabby-api
MQTT_API_PASSWORD=***
MQTT_ADMIN_USER=dynsec-admin
MQTT_ADMIN_PASSWORD=***
SESSION_SECRET=***                # 32+ Byte zufällig
ALLOWED_EMAILS=du@example.org
SMTP_URL=smtps://user:***@smtp.example.org:465
MAIL_FROM="Tabby <tabby@example.org>"
ANTHROPIC_API_KEY=***             # erst ab Phase 4
TABBY_AI_MODEL=claude-opus-5
AI_BUDGET_DAY_CENTS=50
AI_BUDGET_MONTH_CENTS=500
VAPID_PUBLIC_KEY=…
VAPID_PRIVATE_KEY=***
FIRMWARE_RELEASE_REPO=tanyeltuncer/heytabbycloud
```

Secrets **nie** ins Repo (S8). `.env` liegt nur auf dem Server, Rechte `600`.

## 6. CI/CD (GitHub Actions)

| Workflow | Trigger | Schritte |
|---|---|---|
| `ci.yml` | Push, PR | pnpm install → lint → typecheck → test (Vitest mit Testcontainers) → build web → gitleaks |
| `firmware.yml` | Änderungen in `firmware/**`, Tag `fw-v*` | Container `espressif/idf:v5.4.2` → check → build `amoled-1.64` mit `sdkconfig.cloud` → package → Artefakt bzw. Release |
| `deploy.yml` | Push auf `main` (nach grünem CI) | Docker-Images bauen → GHCR → per SSH `docker compose pull && docker compose up -d` → Healthcheck `/api/health` |

Deploy-Secrets in GitHub: `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_SSH_KEY` (eigener Key nur für das Deployment).

## 7. Backups & Wiederherstellung

- Täglich 03:30: `pg_dump -Fc` → mit `age` verschlüsselt → per `rclone` in eine Storage Box oder S3. Aufbewahrung: 7 Tage, 4 Wochen, 6 Monate.
- Zusätzlich gesichert: `mosquitto_data/dynamic-security.json` (enthält die Geräte-Zugänge als Hash)
- **Restore-Probe monatlich:** Dump in einen Wegwerf-Container einspielen, `SELECT count(*) FROM tasks`.

## 8. Monitoring (minimal)

- Uptime-Check von außen auf `/api/health` (z. B. ein kostenloser Uptime-Dienst), Alarm per Mail
- `docker compose logs` mit Rotation (json-file, `max-size: 10m`, `max-file: 3`), keine Inhalte loggen (D6)
- Die API loggt strukturiert (pino): Request-ID, Route, Status, Dauer, **keine** Bodies

## 9. Kosten (Richtwerte)

| Posten | ca. / Monat |
|---|---|
| VPS | 4–6 € |
| Domain | ~1 € |
| Backup-Speicher | 0–4 € |
| E-Mail (Free-Tier) | 0 € |
| KI (Phase 4, mit Budget) | max. 5 € (Standardlimit) |
| **Summe** | **ca. 5–16 €** |
