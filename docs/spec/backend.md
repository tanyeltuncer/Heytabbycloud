# Spec: Backend

## 1. Dienste

```
apps/api  (ein Node.js-Prozess, drei Module)
├─ http        Hono: REST-API + SSE für die Web-App, Auth, statische Firmware-Bundles
├─ mqtt        MQTT-Client "tabby-api": empfängt state/ack/event/status, sendet cmd (Queue pro Gerät)
└─ scheduler   Takt 15 s: Erinnerungen, Timer-Enden, Ruhezeiten, Kalender-Abruf
```

Ein einziger Prozess reicht für einen Nutzer mit wenigen Geräten. Die Module sind so getrennt, dass `scheduler` später ein eigener Container werden kann.

**Stack:** Node 22 LTS, TypeScript strict, Hono, Drizzle ORM + `postgres`, `mqtt` (MQTT.js), Zod, `@anthropic-ai/sdk`, Vitest.

## 2. Realtime zur Web-App: Server-Sent Events

`GET /api/events` (SSE, Session-Cookie). Der Server pusht:

| Event | Payload |
|---|---|
| `device.status` | `{ deviceId, online, lastSeenAt }` |
| `device.state` | `{ deviceId, state }` |
| `task.changed` | `{ task }` / `{ id, deleted: true }` |
| `focus.changed` | `{ session }` |
| `reminder.fired` | `{ reminder }` |
| `ai.delta` | nur im Chat-Stream (separater Endpoint) |

SSE statt WebSocket: Die Web-App schickt Änderungen per normalem REST, der Rückkanal ist unidirektional. Das ist einfacher, und Caddy braucht keine Sonderkonfiguration.

## 3. REST-API (v1)

Alle Routen unter `/api`, JSON, Session-Cookie, CSRF-Header `X-Tabby-CSRF` bei schreibenden Requests.

### Auth
| Methode | Pfad | Beschreibung |
|---|---|---|
| POST | `/auth/magic-link` | `{ email }` → Mail senden (nur Allowlist, Rate-Limit) |
| GET | `/auth/verify?token=` | Session setzen, Redirect `/` |
| POST | `/auth/logout` | Session löschen |
| GET | `/me` | Nutzer + Einstellungen |
| PATCH | `/me` | Zeitzone, KI-Budget, Ruhezeiten-Default |

### Geräte
| Methode | Pfad | Beschreibung |
|---|---|---|
| GET | `/devices` | Liste inkl. online/state |
| POST | `/devices` | Neues Gerät → `{ deviceId, deviceSecret }` (**einziges Mal**, dass das Secret herausgegeben wird). Legt den MQTT-Client in Dynsec an. |
| PATCH | `/devices/:id` | Name, `isPrimary`, Einstellungen (Helligkeit, Ruhezeiten, Screensaver) |
| DELETE | `/devices/:id` | Entkoppeln: Dynsec-Client löschen + Verbindung trennen (`kickClient`) |
| POST | `/devices/:id/rotate-secret` | Neues Secret (danach neu flashen, nur Factory-Partition) |
| POST | `/devices/:id/command` | `{ kind: "animation", id }` / `{ kind: "text", title, subtitle }` / `{ kind: "clear" }`. **Kein Freitext-Befehl.** |
| GET | `/devices/:id/animations` | Animationsliste aus dem Manifest des installierten Firmware-Bundles |

### Aufgaben
| Methode | Pfad | Beschreibung |
|---|---|---|
| GET | `/tasks?view=today\|upcoming\|done` | |
| POST | `/tasks` | `{ title, note?, dueDate?, priority? }` |
| PATCH | `/tasks/:id` | Felder, `status`, `sortOrder` |
| POST | `/tasks/:id/current` | als „Jetzt dran“ setzen → Gerät |
| POST | `/tasks/:id/complete` | erledigt → Animation `task_completed` |
| DELETE | `/tasks/:id` | Soft-Delete, 5 s Undo über `POST /tasks/:id/restore` |

### Fokus
| Methode | Pfad | Beschreibung |
|---|---|---|
| GET | `/focus/current` | laufende Session oder `null` |
| POST | `/focus/start` | `{ minutes, breakMinutes?, taskId? }` |
| POST | `/focus/pause` · `/focus/resume` · `/focus/stop` | |

### Erinnerungen
| Methode | Pfad | Beschreibung |
|---|---|---|
| GET/POST | `/reminders` | `{ title, fireAt, rrule?, taskId? }` (rrule: nur `FREQ=DAILY\|WEEKLY`, `BYDAY`) |
| PATCH/DELETE | `/reminders/:id` | |
| POST | `/reminders/:id/snooze` | `{ minutes: 10 }` |

### KI
| Methode | Pfad | Beschreibung |
|---|---|---|
| POST | `/ai/chat` | `{ message }` → SSE-Stream mit Text + Aktionskarten |
| POST | `/ai/actions/:id/confirm` · `/reject` | bestätigungspflichtige Tool-Aufrufe (K2) |
| POST | `/ai/plan-day` | Vorschlag (ohne zu speichern) |
| POST | `/ai/plan-day/apply` | Vorschlag übernehmen |
| GET | `/ai/usage` | Verbrauch Tag/Monat |

### Sonstiges
| Methode | Pfad | Beschreibung |
|---|---|---|
| GET | `/firmware/latest` | `{ version, bundleUrl, sha256, parts[] }` |
| GET | `/firmware/bundles/:file` | gecachte Release-Dateien (gleiche Origin → kein CORS) |
| GET | `/export` | alle Daten als JSON (F-20) |
| DELETE | `/me` | Konto löschen (F-20) |
| GET | `/health` | `{ ok, version, db, mqtt }` |

## 4. Datenmodell (Drizzle, Postgres)

```sql
users           (id uuid pk, email citext unique, timezone text default 'Europe/Berlin',
                 quiet_start time default '22:00', quiet_end time default '07:00',
                 ai_budget_day_cents int default 50, ai_budget_month_cents int default 500,
                 created_at timestamptz)
sessions        (id text pk /* sha256 des Tokens */, user_id fk, expires_at, created_at)
magic_links     (token_hash text pk, email, expires_at, used_at)
devices         (id text pk /* = device_id */, user_id fk, name, is_primary bool,
                 fw_version text, settings jsonb, last_seen_at, online bool, state text,
                 created_at)
tasks           (id uuid pk, user_id fk, title varchar(200), note text, due_date date,
                 priority smallint, status text check (status in ('open','done')),
                 sort_order int, is_current bool, completed_at, deleted_at, created_at, updated_at)
focus_sessions  (id uuid pk, user_id fk, task_id fk null, kind text /* focus|break */,
                 planned_seconds int, started_at, ends_at, paused_at, remaining_at_pause int,
                 ended_at, state text /* running|paused|done|stopped */)
reminders       (id uuid pk, user_id fk, task_id fk null, title varchar(120),
                 fire_at timestamptz, rrule text null, last_fired_at, snoozed_until, active bool)
ai_messages     (id uuid pk, user_id fk, role text, content jsonb, created_at)
ai_actions      (id uuid pk, user_id fk, tool text, input jsonb, status text
                 /* pending|confirmed|rejected|executed|failed */, result jsonb, created_at)
ai_usage        (id bigserial, user_id fk, model text, input_tokens int, output_tokens int,
                 cost_cents numeric(10,4), created_at)
audit_log       (id bigserial, user_id, action text, target text, created_at)  -- ohne Inhalte (D6)
```

Indizes: `tasks(user_id, status, due_date)`, `reminders(active, fire_at)`, `focus_sessions(user_id, state)`.

## 5. Gerätesteuerung: der „Device Director“

Eine kleine Zustandsmaschine pro Gerät im Backend entscheidet, **was Tabby gerade zeigen soll**. Priorität von hoch nach niedrig:

1. `sleep` (Ruhezeit aktiv)
2. `reminder` (Erinnerung offen)
3. `thinking` (KI-Antwort läuft)
4. `focus` / `break` (Timer läuft)
5. `task` (es gibt eine „Jetzt dran“-Aufgabe)
6. `idle`

Bei jeder Datenänderung ruft der Service `director.reconcile(userId)` auf. Der berechnet den Soll-Zustand, vergleicht ihn mit dem zuletzt gesendeten und schickt nur Differenzen als Befehle (siehe `protocol.md` §4).
Nach `status=online` wird der Soll-Zustand komplett neu gesendet.

**Events vom Gerät**

| Event | Kontext (zuletzt gesendete Karte) | Aktion |
|---|---|---|
| `choice` Option 1 | `task` | Aufgabe erledigt → `task_completed`, nächste Aufgabe als „Jetzt dran“ |
| `choice` Option 2 | `task` | Fokus 25 min für diese Aufgabe |
| `choice` Option 1 / 2 | `reminder` | erledigt / 10 min schlummern |
| `choice` Option 1 / 2 | `focus_end` | Pause starten / nächster Fokusblock |
| `choice` Option 1 / 2 | `break_end` | Fokus starten / Pause +5 min |
| `choice` Option 1 / 2 | `ai` | KI-Aktion bestätigen / ablehnen (K2) |
| `touch` (optional, FW-2b) | `idle` | Tap = nächste Aufgabe, lang = Fokus |

Ob `selection` als Index oder als Text kommt, wird in Phase 2 am Gerät geprüft und dann in `packages/protocol` festgelegt.
Der Kontext kommt aus dem zuletzt gesendeten Befehl (Backend-Zustand), weil `choice`-Events keine Prompt-ID tragen (Upstream-Hinweis).

## 6. Scheduler-Jobs

| Job | Takt | Aufgabe |
|---|---|---|
| `reminders.due` | 15 s | `active AND fire_at <= now()` → auslösen, bei `rrule` das nächste `fire_at` berechnen |
| `focus.ends` | 15 s | `running AND ends_at <= now()` → Ende, ggf. Pause starten |
| `quiet.hours` | 1 min | Ruhezeit beginnt/endet → `reconcile` |
| `sessions.cleanup` | 1 h | abgelaufene Sessions und Magic-Links löschen |
| `backup` | täglich | läuft außerhalb (Cron im `backup`-Container), nicht hier |

Die Jobs sind idempotent (`UPDATE … WHERE last_fired_at IS DISTINCT FROM fire_at RETURNING`), damit bei einem Neustart nichts doppelt feuert.

## 7. Tests

- Unit: Director (Prioritäten, Diff), rrule-Berechnung, Text-Bereinigung, Factory-Record, CRC
- Integration (Vitest + Testcontainers Postgres + Mosquitto): API-Routen, MQTT-Rundlauf mit dem **Simulator** als Gerät
- Jede Route: Test „fremder Nutzer bekommt 404“ (Guardrail S3)
