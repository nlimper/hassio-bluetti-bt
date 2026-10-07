# Elite 200 V2 – voorgestelde entiteiten

Gebaseerd op de leestest van 6 okt 2026 (`docs/elite200v2-leestest.md`) en de app (v3.1.4).
Alleen registers die op dit model een echte waarde geven (geen `404`, geen Modbus-fout).
**Schrijven is nog nergens getest.** De schrijfwijze komt uit de app-code.

Status: ✓ = waarde klopt met HA/app/meting, ? = waarde gelezen maar schaal of betekenis nog verifiëren.

## Stand van de implementatie

| Wat | Status |
|---|---|
| Sensoren, energietellers, uitgangen/AC-ECO als binaire sensor | getest op HA |
| Werkmodus (2005), laadmodus (2020), schermtijd (2067), DC-ECO-tijd (2015): keuzelijst | lezen en schrijven getest |
| Laden van het net (2008), DC-ECO (2014), power lifting (2021), tijdsturing (2029): schakelaar | lezen en schrijven getest |
| SOC laag/hoog (2022/2023): getal 5–100, laag < hoog | lezen en schrijven getest (SOC hoog) |
| Max netlaadstroom (2214): getal 1–10 A | lezen en schrijven getest |
| Tijdvakken 1–6: keuzelijst (modus) + tijd (start, eind) + service `bluetti_bt.set_time_slot` | lezen en schrijven getest (vak 1 eind, service); overlap wordt geweigerd |
| DC-ECO-minimumvermogen (2016), slaapmodus, op afstand opstarten (2073/2074), 2226 | bewust niet: de Bluetti moet altijd aan blijven |

Werkmodus op dit model (zoals de officiële integratie): 1 = Customized UPS, 2 = PV Priority UPS,
4 = Standard UPS, 5 = Time Control UPS.

Elke schrijfactie wordt teruggelezen en maximaal 3 keer herhaald (`write.py`); lukt het niet,
dan geeft HA een foutmelding.

Schrijftest via HA (6 okt 2026): schermtijd NEVER → MIN5 → NEVER en SOC hoog 100 → 99 → 100,
alle vier in één poging bevestigd (9–22 s per schrijfactie). Daarna ook alle schakelaars,
keuzelijsten, max netlaadstroom en tijdvak 1 (via tijd-entiteit en service) heen en terug.

## Sensoren (alleen lezen)

AC- en DC-uitgang (2011/2012) en AC-ECO (2017–2019) alleen als sensor, nooit als schakelaar of instelling.

| Register | Entiteit | Eenheid / omrekening | Gelezen | Status |
|---:|---|---|---|:-:|
| 102 | Accu SOC | % | 71 | ✓ |
| 6006 (lo) | Accu SOH (gezondheid) | % | 99 | ✓ |
| 6007 | Accutemperatuur | °C, waarde − 40 | 36 °C | ? |
| 6003 | Accuspanning | V, ÷100 (app zegt ÷10) | 39,86 V | ? |
| 6004 | Accustroom | A, ÷10, zonder teken (ook positief bij laden) | 26,4 bij laden, 2,5 bij ontladen | ✓ |
| 103 | Laadstatus | 0 geen, 1 laden, 2 ontladen (richting van de accustroom) | | ✓ |
| 6010 | Max laadspanning accu | V, ÷10 | 42,6 V | ? |
| 103 | Laadstatus | enum | 0 | ? |
| 104 / 105 | Tijd tot vol / tot leeg | min; 5994 = n.v.t. | 5994 | ? |
| 140 | DC-uit | W | 0 | ✓ |
| 142 | AC-uit | **VA** (zie leestest) | 262 | ✓ |
| 144 | DC-in / PV | W | 0 | ✓ |
| 146 | AC-in | **VA** | 262 | ✓ |
| 1431 / 1432 | AC-uit spanning / stroom | V ÷10 / A ÷10 | 232,9 / 1,0 | ✓ |
| 1314 / 1315 | AC-in spanning / stroom | V ÷10 / A ÷10, met teken | 235,9 / 1,0 | ✓ |
| 1500 | Frequentie | Hz ÷10 | 50,0 | ✓ |
| 1511 | Omvormer-uitgangsspanning | V ÷10 | 232,8 | ✓ |
| 1510 | Omvormervermogen | W | 0 (doorvoer) | ? |
| 161 (lo) / 1509 (lo) | Omvormerstatus | enum | 3 / 3 | ? |
| 174 bit 3 | Slaapstand | binary | 0 | ? |
| 1153 | Temperatuur PV/DCDC | °C, waarde − 40 | 37 °C | ? |
| 1152 | Max omvormertemperatuur | onduidelijk (350) | | ? |

### Energietellers (voor het HA Energy-dashboard)

Waarschijnlijk 32-bits met het lage woord eerst (het tweede register is nu 0). Eenheid kWh, ÷10.

| Register | Entiteit | Gelezen | Status |
|---:|---|---|:-:|
| 152 (= 1422) | Totaal AC-uit | 809,5 kWh | ? |
| 156 (= 1303) | Totaal geladen van het net | 815,9 kWh | ? |
| 154 (= 1202) | Totaal PV | 57,7 kWh | ? |
| 167 (= 6021) | Totaal ontladen uit de accu | 902,0 kWh | ? |
| 1501 | Totaal omvormer | 284,3 kWh | ? |

Dezelfde waarde staat in twee blokken; dat bevestigt de betekenis.

## Bediening (lezen en schrijven)

Schrijven met Modbus `06` (één register), tenzij anders vermeld.

| Register | Entiteit | Type | Waarden | Gelezen | Nut |
|---:|---|---|---|---|---|
| 2005 | Werkmodus | select | 1 = Customized UPS, 2 = PV-priority, 3 = Standard UPS, 4/5 = tijdsturing, 11 = self-consumption (welke dit model kent: verifiëren) | 1 | hoog |
| 2008 | Laden van het net | switch | 0/1 | 1 | hoog |
| 2022 | SOC-ondergrens | number | % | 10 | **hoog**: nu alleen in de app in te stellen |
| 2023 | SOC-bovengrens | number | % | 100 | hoog |
| 2029 | Tijdsturing aan/uit | switch | 0/1 | 1 | hoog |
| 2030–2047 | Tijdvakken Customized UPS (6 stuks) | lezen: sensor / later schrijven | per vak: modus (0 uit, 1 laden, 2 ontladen, 3 stand-by), start, eind | vak 1 = laden 13:00–15:30 | **hoog**: nu alleen in de app, max 1x per maand |
| 2214 | Max laadstroom van het net | number | A | 10 | hoog: laadvermogen begrenzen |
| 2212 | Max laadstroom | number | A | 20 | middel (betekenis verifiëren) |
| 2020 | Laadmodus | select | 0 standaard, 1 stil, 2 turbo, 4 aangepast | 0 | middel |
| 2014 | DC-ECO | switch | 0/1 | 1 | middel |
| 2015 | DC-ECO-uitschakeltijd | select | 1–4 uur | 4 | laag |
| 2016 | DC-ECO-minimumvermogen | number | W | 5 | laag |
| 2021 | Power lifting | switch | 0/1 | 0 | laag |
| 2067 | Schermtijd | select | enum | 5 | laag |
| 2073 / 2074 | Op afstand opstarten / SOC daarvoor | switch / number | bits / % | 1 / 5 | laag (betekenis verifiëren) |
| 2226 | Uitgangen herstellen na herstart | switch | 0/1 | 1 | laag (verifiëren) |

### Volgorde voorstel

1. Alle sensoren en de energietellers (alleen lezen, geen risico).
2. Tijdvakken uitlezen als sensoren.
3. Eenvoudige schakelaars: laden van het net, tijdsturing.
4. Getallen: SOC-grenzen, max netstroom.
5. Werkmodus en laadmodus.
6. Tijdvakken schrijven (meerdere registers tegelijk; als laatste, met een terugleesrol).

## Bewust weglaten

| Register | Waarom |
|---:|---|
| 2011 / 2012 | AC- en DC-uitgang: **mogen nooit geschakeld worden**, niet via HA en niet door Claude. Alleen uitlezen als sensor. |
| 2017–2019 | AC-ECO (aan, uitschakeltijd, minimumvermogen): kan de AC-uitgang zelf uitzetten. **Alleen lezen** (sensor), nooit schrijven. |
| 2013 | Apparaat uitzetten: daarna is het waarschijnlijk niet meer via Bluetooth aan te zetten. |
| 2200–2203 | Wachtwoord geavanceerde instellingen (staat in klare tekst). |
| 2206 | Fabrieksreset. |
| 2209 / 2210 / 2218 | Uitgangsspanning, frequentie, regio. |
| 2258–2265 | Netbeveiligingsgrenzen (spanning/frequentie). |
| 2001–2004 | Systeemklok en tijdzone (eventueel later: klok gelijkzetten). |
| 2007, 2010, 2066, 2207, 2208, 2211, 2213, 2215–2217, 2241 | `404`: niet ondersteund op dit model. |
| 1316 / 1433 | VA-registers, op dit model altijd 0. |
