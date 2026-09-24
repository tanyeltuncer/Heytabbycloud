# Architecture Decision Records

Kurze Protokolle wichtiger Entscheidungen: Kontext → Entscheidung → Folgen. Neue ADRs bekommen die nächste Nummer, alte werden nicht gelöscht, sondern mit „ersetzt durch …“ markiert.

| Nr. | Titel | Status |
|---|---|---|
| [0001](0001-mqtt-statt-websocket.md) | MQTT (Upstream-Protokoll) statt eigenem WebSocket | angenommen |
| [0002](0002-identitaet-per-factory-record.md) | Geräte-Identität per selbst erzeugtem Factory-Record statt Pairing-Code | angenommen |
| [0003](0003-stack.md) | Tech-Stack: TypeScript, SvelteKit, Hono, Postgres, Mosquitto auf einem VPS | angenommen (änderbar) |
| [0004](0004-kein-ota-im-mvp.md) | Kein OTA im MVP, Updates per USB im Browser | angenommen |
