# hassio-bluetti-bt (fork voor de Bluetti Elite 200 V2)

Doel: de Elite 200 V2 lokaal via Bluetooth in Home Assistant, zonder Bluetti-cloud, inclusief
instellingen die de bestaande integraties missen.

## Herkomst

- Gekloond van `wannessels/hassio-bluetti-bt` (remote `wannessels`): versleuteld schrijven werkt daar.
  `upstream` = `Patrick762/hassio-bluetti-bt`. Een eigen GitHub-fork maakt en pusht Nic zelf.
- Library: `wannessels/bluetti-bt-lib@2090566` (vastgezet in `manifest.json`).
- Elite 200 V2-definitie bestaat al (alleen lezen) in `brunosccosta/bluetti-bt-lib`, branch `el200v2`.

## Afspraken

- **AC- en DC-uitgang (registers 2011/2012) worden nooit geschakeld**: niet door Claude, en de
  integratie biedt er geen schakelaar voor (alleen een sensor). Ook niet om te testen. Geldt ook
  voor 2013 (apparaat uit) en AC-ECO (2017–2019, kan de AC-uitgang zelf uitzetten): alleen lezen.
  DC-ECO (2014–2016) mag wel geschreven worden.
- **Niets naar de Bluetti schrijven** zonder uitdrukkelijke toestemming van Nic per stap.
  Testscripts in `tools/` gebruiken `ReadOnlyGuard` (`tools/read_registers.py`), die alles behalve
  Modbus `03` weigert.
- Testen kan vanaf de pc via Bluetooth. Een andere integratie die met de Bluetti verbindt moet dan
  uit staan, en de Bluetti-app mag niet via Bluetooth verbonden zijn (één verbinding tegelijk).
- Lokale gegevens (MAC-adres, HA-omgeving) staan in `CLAUDE.local.md` (gitignored).
- **De repo is openbaar**: geen MAC-adressen, serienummers, tokens, sleutels, wifi-namen,
  e-mailadressen of details van de eigen HA-installatie committen.
- `tools/dumps/` bevat serienummers en blijft buiten git.
- Bestanden met LF-regeleinden schrijven (beide repo's gebruiken LF).

## Installeren op HA

Via HACS (custom repository `nlimper/hassio-bluetti-bt`). Een wijziging komt op HA na: committen,
Nic pusht (eerst `bluetti-bt-lib` als de pin in `manifest.json` verandert), HACS-update van de
repository, HA herstarten. Niet meer met de hand naar `custom_components` kopiëren.

## Werkomgeving

```bash
.venv/Scripts/python tools/read_registers.py --mac <MAC>
```
`.venv` is lokaal (gitignored), met de vastgezette library geïnstalleerd.

## Documentatie

- `docs/protocol.md`: BLE, handshake, versleuteling.
- `docs/registers-v2.md`: registeroverzicht uit de app (v3.1.4).
- `docs/elite200v2-leestest.md`: wat de Elite 200 V2 echt teruggeeft.
- `docs/elite200v2-entiteiten.md`: voorgestelde HA-entiteiten, volgorde van toevoegen, wat bewust wegblijft.
