# ADR-0001: MQTT (Upstream-Protokoll) statt eigenem WebSocket

**Status:** angenommen · **Datum:** 2026-09-24 · **Ersetzt:** Abschnitt 5.1 des ursprünglichen Konzepts (WSS + JSON)

## Kontext
Das erste Konzept sah vor, der Firmware einen eigenen WebSocket-Client (`cloud_client`) zu geben. Die Analyse der Upstream-Firmware (`firmware/main/taby_mqtt.c`) zeigt aber: Es gibt bereits einen fertigen **MQTT-Client** mit TLS, Zugangsdaten aus dem Factory-Record, Topics `devices/<id>/cmd|ack|state`, Heartbeat und Auto-Reconnect. Das ist genau die Cloud-Anbindung, die das Original-Produkt („Taby Cloud“) nutzt.

## Entscheidung
Wir nutzen **MQTT und die Upstream-Befehlssprache** unverändert. Als Broker dient **Mosquitto 2** mit Dynamic Security. Die Firmware bekommt nur minimale Ergänzungen: konfigurierbare Broker-URI, `event`-Topic, LWT/`status` (siehe `spec/firmware.md`, FW-1 bis FW-5).

## Folgen
- ➕ Deutlich weniger Firmware-Code. Der riskanteste Teil (TLS-Client in C) ist schon upstream getestet.
- ➕ Wir bleiben nah an upstream, Updates lassen sich leichter mergen.
- ➕ Online/Offline-Erkennung über LWT ist MQTT-Standard.
- ➖ Es gibt einen zusätzlichen Dienst (Mosquitto) und einen offenen Port 8883.
- ➖ Die Befehlssprache ist textbasiert mit `|`-Trennern, deshalb müssen Nutzertexte bereinigt werden (K5).
- ➖ `ack` hat keine Message-ID, deshalb sendet das Backend Befehle pro Gerät seriell.
