# ADR-0003: Tech-Stack

**Status:** angenommen (änderbar, solange Phase 1 nicht begonnen hat) · **Datum:** 2026-09-24

## Entscheidung
| Bereich | Wahl | Alternative |
|---|---|---|
| Sprache | TypeScript überall (außer Firmware: C/ESP-IDF) | – |
| Frontend | SvelteKit (SPA, `adapter-static`) | Next.js |
| Backend | Node 22 + Hono + Drizzle + Zod | Fastify, Prisma |
| DB | Postgres 17 | SQLite (einfacher, aber weniger Reserven) |
| Broker | Mosquitto 2 + Dynamic Security | EMQX (mehr Features, schwerer) |
| Hosting | ein VPS in der EU, Docker Compose, Caddy | Fly.io, Cloudflare |
| KI | Claude API (`@anthropic-ai/sdk`) | selbst gehostetes Modell |

## Begründung
Eine Sprache für Web, API und Protokoll-Schemas. Kleine, schnelle Bibliotheken. Fixkosten im einstelligen Euro-Bereich. WebSockets/MQTT ohne Plattform-Limits.
