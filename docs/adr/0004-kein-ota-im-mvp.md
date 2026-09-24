# ADR-0004: Kein OTA im MVP

**Status:** angenommen · **Datum:** 2026-09-24

## Kontext
Die Upstream-Partitionstabelle hat nur **einen** App-Slot (`ota_0`, 4 MB), dazu ~11,75 MB Assets auf 16 MB Flash. Ein sicheres OTA mit Rollback braucht zwei App-Slots. Upstream sagt selbst: „rollback-safe Wi-Fi OTA is not claimed“.

## Entscheidung
Im MVP gibt es **Firmware-Updates nur per USB im Browser** (Einrichtungs-Assistent im Update-Modus, `factory_data` bleibt erhalten). OTA (F-18) wird in Phase 5 untersucht: App-Größe messen und bei < 1,9 MB zwei 2-MB-Slots anlegen.

## Folgen
- ➕ Keine riskante Partitionsänderung am Anfang
- ➖ Für Updates muss Tabby kurz an den PC (ohne Installation, im Browser).
- Guardrail S6 (signiertes OTA) gilt erst, sobald OTA existiert.
