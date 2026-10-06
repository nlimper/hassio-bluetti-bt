# Elite 200 V2 – leestest (6 okt 2026)

Alleen gelezen (Modbus `03`), vanaf de pc via Bluetooth (-46 dBm), library
`wannessels/bluetti-bt-lib@2090566`, versleuteld. Script: `tools/read_registers.py`.

## Verbinding

- Advertising: fabrikantdata `BLUETTF` (`424c5545545446`). De app behandelt dat als versleuteld,
  net als `BLUETTE`. De handshake van de library werkt.
- Modbus-slaveadres 1.
- 640 registers in 72 blokjes van 10 gelezen. Geweigerd (Modbus-fout): 190–219, 1330–1339,
  2090–2099, 2290–2309, 14000–14009.
- Waarde **404** (`0x0194`) = "niet ondersteund op dit model" (o.a. 2007, 2010, 2066, 2207, 2208,
  2211, 2213, 2215–2217, 2241 en tijdvak 7–10).
- Modelnaam (110–115) is byte-gewisseld ("lEti e02 02V"), zoals `SwapStringField` verwacht.

## Bevestigd (klopt met HA en de app)

| Register | Wat | Gelezen |
|---:|---|---|
| 102 | SOC | 71 % |
| 142 | AC-uit (wat Bluetti toont) | ~250 (u16, 143 = 0) |
| 146 | AC-in | ~250 (u16) |
| 161 (lo) | omvormerstatus | 3 |
| 1312 / 1429 / 1508 (lo) | aantal fasen net / belasting / omvormer | 1 / 1 / 1 |
| 1313–1315 | AC-in fase 1: vermogen / V ÷10 / A ÷10 | ~250 / 235,9 / 1,0 |
| 1430–1432 | AC-uit fase 1: vermogen / V ÷10 / A ÷10 | ~250 / 232,9 / 1,0 |
| 1500 | frequentie ÷10 | 50,0 |
| 1509–1512 | omvormer: status / W / V ÷10 / A ÷10 | 3 / 0 / 232,8 / 0 |
| 2005 | werkmodus | 1 = Customized UPS |
| 2008 | laden van het net | 1 |
| 2009 | PV | 2 |
| 2011 / 2012 | AC / DC | 1 / 0 |
| 2014–2016 | DC ECO aan / uren / min W | 1 / 4 / 5 |
| 2017–2019 | AC ECO aan / uren / min W | 0 / 4 / 10 |
| 2020 | laadmodus | 0 = standaard |
| 2021 | power lifting | 0 |
| 2022 / 2023 | SOC laag / hoog | 10 / 100 |
| 2029 | tijdsturing aan | 1 |
| 2030–2047 | tijdvakken Customized UPS (6 stuks, 3 reg per vak) | vak 1 = laden 13:00–15:30 |
| 2067 | schermtijd | 5 |
| 2073 / 2074 | op afstand opstarten / SOC | 1 / 5 |
| 2212 / 2214 | max laadstroom / max netstroom | 20 / 10 |

Tijdvak (3 registers): `[vlag | 0=uit,1=laden,2=ontladen,3=stand-by]`, `[start uur | start min]`,
`[eind uur | eind min]`.

Nog onduidelijk: register 100 (volgens de app accuspanning ÷10) gaf ruw 3986, register 101
(accustroom) 0. Bij doorvoer zonder laden is stroom 0 logisch; de schaal van 100 klopt nog niet.

## W of VA

Gemeten in doorvoermodus (Shelly aan, omvormer 0 W), 8 metingen naast een Shelly-energiemeter aan de AC-ingang:

| | 142 | 1430 | V×A uit | Shelly (W, ingang) |
|---|---:|---:|---:|---:|
| typisch | ~250 | ~250 | 233–257 | 202–218 |

- 142 en 1430 zijn op dit model **hetzelfde getal**.
- De uitgang (~250) is groter dan wat de Shelly aan de ingang meet (~210 W). Dat kan niet als
  beide watt zijn: de Bluetti-waarden zijn **schijnbaar vermogen (VA)**. Arbeidsfactor ≈ 0,84.
- De aparte VA-registers 1433 en 1316 zijn op dit model 0.
- Een register met het werkelijke vermogen (W) is niet gevonden.

## Library-definitie (EL200V2) uitgelezen

Met `tools/read_device.py` en de nieuwe definitie in `bluetti-bt-lib` (alleen lezen):

- Accuspanning 6003 is **÷100** (39,91 V; 12S LFP, max laadspanning 6010 = 42,6 V).
- Accutemperatuur 6007 − 40 = 35 °C, SOH 99 %.
- Energietellers 150–167 zijn 32-bits met het lage woord eerst (zoals `bit32HexSwap` in de app).
- Register 1300 (netfrequentie) wisselt tussen 500 en 0: niet gebruikt. Frequentie komt uit 1500.

## Schrijftest (6 okt 2026)

Op register 2067 (schermtijd), het enige register dat het testscript mocht schrijven
(`tools/write_test_display.py`, alleen de waarden 4 en 5):

| Stap | Resultaat |
|---|---|
| begin | 5 (nooit) |
| 5 schrijven | teruggelezen 5 |
| 4 schrijven | teruggelezen 4: **versleuteld schrijven werkt** |
| 5 terugzetten | eerste poging time-out, derde poging gelukt: teruggelezen 5 |

Schrijven via de library (`DeviceWriter`, eigen verbinding per schrijfactie) loopt af en toe
tegen een time-out aan bij het opnieuw verbinden direct na een leesactie. Een schrijfactie moet dus
altijd worden teruggelezen en zo nodig herhaald.
