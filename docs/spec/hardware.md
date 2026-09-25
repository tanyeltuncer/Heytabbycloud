# Spec: Hardware

## 1. Board: Waveshare ESP32-S3-Touch-AMOLED-1.64 (**V1**)

| Eigenschaft | Wert | Quelle |
|---|---|---|
| SoC | ESP32-S3R8, Dual-Core LX7, 240 MHz | Waveshare |
| Speicher | 512 KB SRAM, **8 MB PSRAM**, **16 MB Flash** | Waveshare, `boards.json` |
| Funk | WLAN 2,4 GHz (b/g/n), Bluetooth 5 LE | Waveshare |
| Display | 1,64" AMOLED, 280 × 456, QSPI, Treiber **CO5300** | Waveshare |
| Touch | kapazitiv, **FT3168** | Waveshare |
| Sensoren | **QMI8658** 6-Achsen-IMU (Beschleunigung + Gyro) | Waveshare |
| Akku | **MX1.25-2P-Anschluss** für 3,7-V-LiPo, Lade-IC auf dem Board | Waveshare |
| Sonstiges | microSD-Slot, USB-C (Strom, Flashen, Debug) | Waveshare |
| Audio | **kein Mikrofon und kein Lautsprecher aufgeführt** | Waveshare (Produktseite) |

**Konsequenzen**
- Sprache (F-16) läuft **nur über das Browser-Mikrofon**, wie im Konzept vorgesehen.
- Die IMU ist ungenutzt, aber interessant für später: „Tabby umdrehen = Timer pausieren“ oder „schütteln = neue Aufgabe“.
- Mit Akku könnte Tabby kabellos sein. Im MVP läuft es aber am USB-Netzteil (siehe 4).

### ⚠️ Revision V1 vs. V2
Die Firmware unterstützt **nur V1**. V2 hat eine andere Pinbelegung und ist upstream ungetestet.
- Beim Kauf auf „V1“ achten oder beim Händler nachfragen.
- **Erkennen lässt sich die Revision nur an der Platinen-Beschriftung bzw. der Verdrahtung**, nicht per USB. Das zeigt der [bebilderte Revisions-Guide von Waveshare](https://docs.waveshare.com/ESP32-S3-Touch-AMOLED-1.64).
- Falls V2 geliefert wird: **nicht flashen**. Zurückschicken oder erst nach einem Upstream-Support-Update verwenden.

## 2. Einkaufsliste

| # | Teil | Menge | ca. Preis | Hinweis |
|---|---|---|---|---|
| 1 | ESP32-S3-Touch-AMOLED-1.64 **V1** | 1 (besser 2) | 25–35 € | Ein zweites Board erlaubt Experimente, während das erste im Alltag läuft. |
| 2 | USB-C-Datenkabel, 1 m | 1 | 5 € | Test: Im Browser muss beim Verbinden ein serieller Port erscheinen. |
| 3 | USB-Netzteil 5 V / 1–2 A | 1 | 8 € | Markengerät, kein No-Name (H4) |
| 4 | Neodym-Blockmagnet 20 × 10 × 2 mm | 2 | 3 € | Maß laut Upstream-Gehäuse |
| 5 | Stahlplättchen, selbstklebend | 2 | 3 € | Monitor-Rückseite oder Regal |
| 6 | Rutschfeste Gummifolie | 1 | 3 € | Unterseite |
| 7 | Sekundenkleber oder 2K-Kleber | 1 | – | Magnet fixieren |
| 8 | Gehäuse-Druck (PLA/PETG) | 1 Satz | 0–15 € | Siehe 3 |
| 9 | *optional* LiPo 3,7 V mit MX1.25-Stecker und Schutzschaltung | 1 | 8 € | **Erst nach Phase 5.** Polarität prüfen! |

## 3. Gehäuse

Upstream liefert für die 1.64 V1 ein Desktop-Gehäuse aus drei Teilen: **Base, Back, Handle**.
**[Print-Pack herunterladen](https://github.com/TRIIIS-LABS/firmware-taby/releases/download/prints-1.64-1.0.0/taby-1.64-print-pack-1.0.0.zip)** (STL, 3MF, G-Code).

| Datei | Profil laut Upstream |
|---|---|
| G-Code | Bambu Lab P1S, 0,4-mm-Düse, PLA, 15 % Infill, variable Schichthöhe, Tree-Supports |
| 3MF | Bambu Lab A1 mini, 0,4-mm-Düse, PLA, 25 % Infill, 0,2 mm, manuelle Tree-Supports, inkl. Modifier |
| STL | für andere Drucker selbst slicen. **Achtung:** STL enthält keine Modifier und keine Support-Einstellungen. |

Upstream druckt in PLA. PETG ist hitzebeständiger, falls Tabby direkt auf einem warmen Monitor sitzt. Maße dann gegebenenfalls nachprüfen. Die Passform für V2 ist upstream nicht bestätigt.

**Montage**
1. Magnet in die Aussparung von Base/Back kleben, Polung zum Stahlplättchen beachten
2. Gummifolie auf die Unterseite
3. Board einsetzen, USB-C-Buchse zur Öffnung ausrichten
4. Back aufsetzen, Handle montieren
5. Stahlplättchen am Monitor anbringen, Tabby andocken

## 4. Strom & Sicherheit (H4)

- Dauerbetrieb am USB-Netzteil. Das AMOLED zieht wenig Strom, WLAN kurzzeitig bis ~300 mA.
- Kein Betrieb im geschlossenen Gehäuse **mit** geladenem LiPo auf heißen Oberflächen (Monitor-Oberseite).
- Einen LiPo nur mit Schutzschaltung verwenden und nicht unbeaufsichtigt laden.
- AMOLED-Einbrennen: Ruhezeiten und Screensaver (F-09) sind Pflicht, keine statischen Karten über Stunden.

## 5. Hardware-Abnahme (Phase 0)

- [ ] Die Platinen-Beschriftung bestätigt V1 (Waveshare-Guide, Foto in `docs/hardware-log.md`).
- [ ] Download-Modus bekannt, falls das Flashen hängt: **BOOT halten, RESET drücken und loslassen, dann BOOT loslassen**.
- [ ] USB-Port erscheint im Browser (WebSerial-Dialog).
- [ ] Upstream-Release 1.1.x im Browser geflasht (siehe `webapp.md`, Setup-Wizard, oder upstream `INSTALL.md`)
- [ ] `INFO` → `hardware_target: amoled-1.64`
- [ ] Animationen `confirmation`, `boxing`, `flower_grow` laufen.
- [ ] Touch reagiert (Choice-Karte testen).
- [ ] Gehäuse gedruckt, Magnet hält auch beim Antippen.
