# Spec: Firmware

Basis ist die offene Firmware [TRIIIS-LABS/firmware-taby](https://github.com/TRIIIS-LABS/firmware-taby) (Apache-2.0).
Dieses Dokument hält fest, **was upstream schon kann** (analysiert am Stand 1.1.x, September 2026) und **was wir ändern**.

---

## 1. Was upstream schon mitbringt

| Baustein | Datei(en) | Relevanz für uns |
|---|---|---|
| **ESP-IDF v5.4.2**, CMake, Build über `tools/build.py <board>` | `firmware/CMakeLists.txt`, `tools/` | ✅ Upstream-CI baut schon im Docker-Image `espressif/idf:v5.4.2`. Wir brauchen **keine lokale Toolchain**. |
| **MQTT-Cloud-Client** (TLS, Zertifikats-Bundle, Keepalive 30 s, Auto-Reconnect) | `main/taby_mqtt.c` | ✅ **Das ist schon die Cloud-Anbindung.** Nur der Broker ist fest auf `mqtts://mqtt.heytaby.com:8883` eingestellt. |
| Topics `devices/<device_id>/cmd`, `…/ack`, `…/state`; State-Heartbeat alle 15 s | `main/taby_mqtt.c` | ✅ direkt nutzbar |
| **Geräte-Identität** aus Partition `factory_data` (`device_id`, `device_secret`, CRC32) | `main/taby_identity.c` | ✅ Das sind die MQTT-Zugangsdaten. **Diesen Record erzeugen wir selbst** (Abschnitt 3). |
| **WLAN-Einrichtung**: USB-Befehl `PROVISION {"ssid","password"}` **oder** Captive Portal (SoftAP, `192.168.4.1`) | `taby_usb_serial.c`, `taby_http_server.c`, `taby_wifi.c` | ✅ Beides geht ohne Installation: WebSerial im Browser oder mit dem Handy ins Taby-WLAN |
| Mehrere WLAN-Profile mit Priorität | `taby_wifi.c` | ✅ |
| **Befehlssprache**: Animations-IDs, `UI/...`-Karten, `CLEAR` | `taby_transport_protocol.c`, `taby_reusable_ui.c` | ✅ Über USB, BLE, HTTP und MQTT identisch |
| Touch-Auswahl bei `UI/choice_*` → `choice signal` | `taby_reusable_ui.c` (`publish_choice_signal`) | ⚠️ Wird **nicht** per MQTT gemeldet (siehe FW-2). |
| Lokaler HTTP-Server (`/cmd`, `/state`, `/touch`, Setup-Seiten) | `taby_http_server.c` | ⚠️ **ohne Authentifizierung**, muss im Cloud-Betrieb eingeschränkt werden (FW-3) |
| BLE-GATT-Steuerung | `taby_ble_transport.c` | ⚠️ ohne Bonding, jeder in Funkreichweite könnte steuern (FW-4) |
| Helligkeit, Display-Ausrichtung per Befehl | `taby_usb_serial.c` | ✅ Per USB ja; ob auch per MQTT, wird geprüft (FW-6). |
| Partitionen: **ein** App-Slot (4 MB) + Assets (~11,75 MB) | `partitions.csv` | ⚠️ **Kein OTA mit Rollback möglich** (FW-8) |

### Board-Revision
`boards.json` unterstützt ausdrücklich **Waveshare ESP32-S3-Touch-AMOLED-1.64 V1**. Upstream warnt:
*„Waveshare 1.64 V2 needs its own reviewed pin mapping and hardware tests.“* → **Nur V1 kaufen** (siehe `hardware.md`).

---

## 2. Unsere Änderungen (Fork `firmware/`)

Grundsatz: **so wenig wie möglich ändern.** Die Upstream-Dateien bleiben unangetastet, wo es geht, damit spätere Upstream-Updates sich gut mergen lassen.
Alle Änderungen landen hinter `#if CONFIG_TABBY_CLOUD` oder in neuen, kleinen Dateien.

| ID | Änderung | Umfang | Phase |
|---|---|---|---|
| **FW-1** | **Broker-URI und Topic-Prefix konfigurierbar** über eine neue `Kconfig.projbuild` (`CONFIG_TABBY_MQTT_URI`, `CONFIG_TABBY_MQTT_TOPIC_PREFIX`). Default bleibt upstream. Unser CI setzt `mqtts://mqtt.<domain>:8883`. | ~20 Zeilen | 2 |
| **FW-2** | **Events per MQTT**: `publish_choice_signal()` ruft einen Hook auf, der `devices/<id>/event` mit `{"type":"choice","signal":N,"selection":"..."}` sendet. Außerdem die Touch-Gesten im Idle-Zustand (Tap, Double, Long). | ~60 Zeilen | 2–3 |
| **FW-3** | **Lokaler HTTP-Server im Cloud-Modus**: nur für das Captive-Portal-Setup aktiv (SoftAP). Im Station-Modus sind `/cmd`, `/touch`, `/state` aus (Guardrail S2). | ~15 Zeilen | 2 |
| **FW-4** | **BLE im Cloud-Build aus** (`CONFIG_TABBY_DISABLE_BLE`), weil es kein Bonding gibt | ~10 Zeilen | 2 |
| **FW-5** | **Last Will & Testament**: Der MQTT-Client setzt LWT auf `devices/<id>/status` = `offline` (retained). Beim Connect wird `online` gesendet (retained). Damit weiß der Server sofort, ob das Gerät erreichbar ist. | ~15 Zeilen | 2 |
| **FW-6** | Prüfen, ob `BRIGHTNESS <0-100>` über MQTT ankommt. Falls nicht, im MQTT-Pfad freischalten (nur Helligkeit, **kein** `PROVISION`, `WIFI_*` oder `DIAG` über MQTT). | ~20 Zeilen | 3 |
| **FW-7** | Build-Variante `amoled-1.64-cloud` in `boards.json`/CI mit unseren Kconfig-Werten | CI | 2 |
| **FW-8** | **OTA** (optional, Phase 5): App-Größe messen. Unter ~1,9 MB passen zwei Slots zu je 2 MB (`ota_0`, `ota_1`), die Assets bleiben gleich groß. Sonst Assets verkleinern oder OTA weglassen und per USB im Browser updaten. | Untersuchung | 5 |

**Nicht ändern:** Animationen, Artwork, Display- und Board-Code (Lizenz L2, und weil sie funktionieren).

---

## 3. Factory-Record (Gerätezugang)

Die Firmware liest beim Boot die Partition `factory_data` (Offset `0x1c000`, Größe `0x4000`):

```c
typedef struct __attribute__((packed)) {
    uint32_t magic;               // 0x59424154  ("TABY", little endian)
    uint16_t version;             // 1
    uint16_t reserved0;           // 0
    char device_id[32];           // z. B. "tabby_3f9a1c7e2b40", nullterminiert
    char device_secret[65];       // 64 Hex-Zeichen + \0
    char hardware_revision[16];   // "V1"
    char manufacturing_batch[32]; // "diy"
    uint8_t reserved[64];         // 0
    uint32_t crc32;               // esp_rom_crc32_le(0, record, offsetof(crc32))
} taby_factory_record_t;          // Rest der Partition: 0xFF
```

**Erzeugung:** Das Backend legt beim „Neues Tabby hinzufügen“ `device_id` und `device_secret` an. Der Browser baut daraus
das 16-KB-Image (JS-Funktion `buildFactoryRecord()` in `packages/protocol`, inkl. CRC32 **kompatibel zu `esp_rom_crc32_le`**)
und flasht es mit esptool-js zusammen mit der Firmware. Das Secret erscheint nur in diesem einen Request und wird nirgends geloggt.

> Test: Unit-Test, der einen Record baut und mit einer Referenz-Implementierung in Python (`zlib.crc32`-Variante prüfen!) vergleicht.
> `esp_rom_crc32_le(0, …)` sollte dem Standard-CRC32 (`zlib.crc32`) entsprechen. **Trotzdem einmal an einem echten Gerät verifizieren**: Das Boot-Log muss `identity source=factory_data` zeigen, sonst fällt die Firmware auf `mac_fallback` zurück, und MQTT bleibt aus.

---

## 4. Build & Release (ohne lokale Installation)

GitHub-Actions-Workflow `firmware.yml`:
1. Container `espressif/idf:v5.4.2`
2. `python tools/check.py` und die Unit-Tests (wie upstream)
3. `python tools/build.py amoled-1.64` mit `SDKCONFIG_DEFAULTS="sdkconfig.defaults;sdkconfig.cloud"`
4. `python tools/package_release.py amoled-1.64` → `taby-amoled-1.64.zip` + SHA-256
5. Bei Tag `fw-v*`: Release anlegen. Die Web-App lädt die Bundles über den Server (Proxy/Cache, damit kein CORS-Problem entsteht).

**Flash-Layout** (aus dem Bundle, wird im Browser geschrieben):

| Offset | Inhalt |
|---|---|
| `0x0` | Bootloader |
| `0x8000` | Partitionstabelle |
| `0x19000` | otadata (leer/0xFF) |
| `0x1c000` | **factory_data** (von uns erzeugt) |
| `0x40000` | App |
| `0x440000` | Assets (SPIFFS, ~12 MB, dauert beim Flashen am längsten) |

Genaue Offsets **immer aus dem Bundle-Manifest lesen**, nicht hart kodieren.

---

## 5. Test-Checkliste Firmware

- [ ] Boot-Log: `identity source=factory_data`, `mqtt enabled broker=mqtts://mqtt.<domain>:8883`
- [ ] `mosquitto_sub -t 'devices/+/#'` (auf dem Server) zeigt `state` alle 15 s.
- [ ] `cmd` = `confirmation` → Animation + `ack {"ok":true}`
- [ ] `cmd` = `UI/choice_2?test:PAUSE?|JA|SPÄTER` → Tippen → `event {"type":"choice"}` (FW-2)
- [ ] Router aus → `status` = `offline` nach ≤ 45 s (LWT, Keepalive 30 s × 1,5). Router an → `online`.
- [ ] Im Heim-WLAN ist `http://<geräte-ip>/cmd` **nicht** erreichbar (FW-3).
- [ ] Das BLE-Gerät ist beim Scannen nicht sichtbar (FW-4).
