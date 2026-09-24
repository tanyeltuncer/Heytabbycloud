# ADR-0002: Geräte-Identität per selbst erzeugtem Factory-Record

**Status:** angenommen · **Datum:** 2026-09-24 · **Ersetzt:** Pairing per 6-stelligem Code (Konzept 5.2)

## Kontext
Die Upstream-Firmware aktiviert MQTT nur, wenn in der Partition `factory_data` ein gültiger Record (Magic `0x59424154`, CRC32) mit `device_id` und `device_secret` liegt. Beim Original schreibt der Hersteller diesen Record in der Fabrik. Die Werkzeuge dafür sind nicht öffentlich. Einen Pairing-Code-Flow gibt es in der Firmware nicht.

## Entscheidung
Die Web-App erzeugt den Record **beim Einrichten selbst**: Das Backend legt `device_id` und `device_secret` an und registriert sie in Mosquitto. Der Browser baut das 16-KB-Image und flasht es mit esptool-js zusammen mit der Firmware. Das Gerät gehört damit automatisch zum eingeloggten Konto, ein Pairing-Code ist unnötig.

## Folgen
- ➕ Keine Firmware-Änderung für Pairing nötig
- ➕ Sicherer als ein Pairing-Code: Das Secret existiert nur im Browser-Speicher während des Flashens und im Gerät.
- ➖ Die Einrichtung braucht einmalig Chrome/Edge + USB (war ohnehin für das Flashen nötig).
- ➖ Secret-Rotation heißt: nur die `factory_data`-Partition neu flashen (Assistent kann das).
- ⚠️ Die CRC-Kompatibilität muss am echten Gerät verifiziert werden (Boot-Log `identity source=factory_data`).
