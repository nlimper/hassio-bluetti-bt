# Bluetti V2-protocol – registeroverzicht

Uit de Bluetti-app v3.1.4 (gedecompileerd), voor de **Elite 200 V2** en andere V2-apparaten.
Nog **niet getest** op het apparaat: niet elk model vult elk register.

## Hoe je dit leest

- Modbus over BLE, slave-adres `01`. Lezen met functie `03`, schrijven met `06` (één register).
- Elk register is 16 bits, big-endian.
- **lo-byte / hi-byte**: de waarde zit in de lage of hoge byte van het register.
  Bij schrijven van een hi-byte-veld schuift de app de waarde 8 bits op (`waarde << 8`).
- **2 reg / u32**: 32-bits waarde over twee registers.
- **/10**: delen door 10 (bv. 532 → 53,2 V).
- **bits**: bitveld (elke bit is een aan/uit).
- **In bt-lib ✓**: zit al in `bluetti-bt-lib` (EL100V2/AC180) en werkt daar dus bewezen.

De app leest blokken in één keer (bv. vanaf 100, 2000, 2200).
Adres = blokbegin + (byte-index ÷ 2), gecontroleerd tegen de constanten in de app
(werkmodus 2005, AC 2011, DC 2012, laadmodus 2020).

## De interessantste instellingen

| Register | Wat | Waarden / schrijven | In bt-lib |
|---:|---|---|:-:|
| 2005 | Werkmodus | 1 = Customized UPS, 2 = PV-priority UPS, 3 = Standard UPS, 4 = Time-control UPS (V2: 4 = Standard UPS offline, 5 = Time-control UPS), 11 = Self-consumption/export | |
| 2007 | LED | 0/1 | |
| 2008 | Laden van het net | 0/1 | |
| 2009 | PV-invoer | 0/1 | |
| 2010 | Omvormer | 0/1 | |
| 2011 / 2012 | AC- / DC-uitgang | 0/1 | ✓ |
| 2014–2016 | DC ECO: aan, uitschakeltijd (1–4 uur), minimum vermogen | | ✓ |
| 2017–2019 | AC ECO: aan, uitschakeltijd (1–4 uur), minimum vermogen | | ✓ |
| 2020 | Laadmodus | 0 = standaard, 1 = stil, 2 = turbo, 4 = aangepast | ✓ |
| 2021 | Power lifting | 0/1 | ✓ |
| 2022 / 2023 | Systeem-SOC laag / hoog (ontlaadgrens / laadgrens) | % | ✓ (alleen lezen) |
| 2029 + 2030–2059 | Tijdsturing aan + tijdvakken (laden/ontladen) | | |
| 2066 | Alarmgeluid | 0/1 | |
| 2067 | Schermtijd | | ✓ |
| 2075 | SOC vasthouden (laag): hi-byte = %, lo-byte = aan | | |
| 2078 | LED-kleur (lo, 2 bits) / helderheid (hi, `waarde << 8`) | | |
| 2079 | Slaap-drempelvermogen | | |
| 2083 | SOC-bovengrens: hi-byte = %, schrijven als `soc << 8` | | |
| 2087 / 2088 | Cyclus-capaciteit ingesteld / max | | |
| 2093–2095 | AC-/DC-poorten afzonderlijk aan/uit, DC-poortmodus | bits | |
| 2207 | Netkoppeling | 0/1 | |
| 2208 | Terugleveren | 0/1 | |
| 2211 / 2212 | Max laadspanning / laadstroom | | |
| 2213 / 2214 | Max netvermogen / netstroom (laden van het net) | W / A | |
| 2215 / 2216 | Max terugleververmogen / -stroom | W / A | |
| 2241 | EMS-modus | | |

**Let op met 2206 (FactoryReset) en 2200 (geavanceerd wachtwoord): niet schrijven.**

Registers 19000–19300 (SOC-drempels, uitgestelde schakeling, reserve, timers) en
26000/26001 (TOU-tarieven) zijn gedeelde blokken voor andere modellen; die zijn hieronder
niet uitgewerkt omdat de app ze met lussen leest.

## Vermogen per fase: watt (W) en schijnbaar vermogen (VA)

De app leest per fase het werkelijke vermogen én het schijnbare vermogen apart uit.
De parser gebruikt een lus per fase (stapgrootte 6 registers); daarom stond dit niet in de automatische tabel.

| Register | Wat | Type |
|---:|---|---|
| 1429 (lo-byte) | aantal fasen belasting | |
| **1430** | **AC-uitgang (belasting) fase 1: werkelijk vermogen** | W, u16 |
| 1431 | AC-uitgang fase 1: spanning | /10 V |
| 1432 | AC-uitgang fase 1: stroom | /10 A |
| **1433** | **AC-uitgang fase 1: schijnbaar vermogen** | VA, u16 |
| 1436–1439 | idem fase 2 (bij meerfase-apparaten) | |
| 1456+2k / 1462+2k | 32-bits versie van W / VA voor fase k (alleen thuisbatterijen, protocol ≥ 2022) | u32 |
| 1312 (lo-byte) | aantal fasen net | |
| **1313** | **AC-ingang (net) fase 1: werkelijk vermogen** | W, signed |
| 1314 | AC-ingang fase 1: spanning | /10 V |
| 1315 | AC-ingang fase 1: stroom | /10 A, signed |
| **1316** | **AC-ingang fase 1: schijnbaar vermogen** | VA, signed |
| 1508 (lo-byte) | aantal fasen omvormer | |
| 1509 (lo-byte) | omvormer fase 1: werkstatus | |
| 1510 | omvormer fase 1: vermogen | W |
| 1511 | omvormer fase 1: spanning | /10 V |
| 1512 | omvormer fase 1: stroom | /10 A |

Het totaal op 142 (AC-uitgang) is het getal dat Bluetti overal toont. Of dat W of VA is, staat niet
in de code; vergelijk het live met 1430 en 1433.

## Vergelijking met het registerbestand van de officiële integratie

Bestand `downloads/proto/<model><serienummer>.bin` (929 bytes, onversleutelde protobuf).
Het is **generiek** (modelnaam `*`) en bevat alleen de ~20 functies die de officiële integratie toont,
voor zowel gen1- (3000-reeks) als gen2-apparaten. Alle gen2-adressen kloppen met dit overzicht.

| Register | Naam in .bin | Opmerking |
|---:|---|---|
| 102 / 103 / 104 | SOC / sChargingStatus / ChgFullTime | |
| 116 (4 reg) | deviceSn | |
| 140 / 142 / 144 / 146 | DC- / AC-belasting / PV / net (vermogen) | 2 reg |
| 161 | InvWorkState | |
| 174 | iotState | bitveld, bit 3 = slaapstand |
| 182 | drivingChargingPower | autoladen (= TotalCarPower) |
| 2005 | SetCtrlWorkMode | |
| 2011 / 2012 | SetCtrlAc / SetCtrlDc | |
| 2013 | SetCtrlPowerOn | apparaat aan/uit |
| 2014 / 2017 | SetDCECO / SetACECO | |
| 2073 | remoteSet | op afstand opstarten (lo-byte bits) |
| 2074 | remoteSetSoc | SOC voor op afstand opstarten |

Nieuw t.o.v. de app-analyse: 174 (slaapstand-bit) en 2013 (aan/uit).

## Volledig overzicht per blok

### 100 – Live data (home)  
_bron: `ProtocolParserV2.parseHomeData`_

| Register | Veld (app-naam) | Type | Opmerking | In bt-lib |
|---:|---|---|---|:-:|
| 100 | PackTotalVoltage | u16 | /10 |  |
| 101 | PackTotalCurrent | u16 | /10 |  |
| 102 | PackTotalSoc | u16 |  | ✓ |
| 103 | PackChargingStatus | u16 |  |  |
| 104 | PackChgFullTime | u16 |  | ✓ |
| 105 | PackDsgEmptyTime | u16 |  |  |
| 107 | PackCnts | lo-byte |  |  |
| 108 | PackOnline | u16 | bits |  |
| 109 | CanBusFault | u16 | bits |  |
| 110 | DeviceModel | 6 reg | ascii | ✓ |
| 116 | DeviceSN | 4 reg |  | ✓ |
| 120 | InvNumber | lo-byte |  |  |
| 121 | InvOnline | u16 | bits |  |
| 122 | InvPowerType | lo-byte |  |  |
| 123 | EnergyLines | u16 |  |  |
| 123 | EnergyLinesBit | u16 | bits |  |
| 124 | CtrlStatus | u16 |  |  |
| 125 | GridParallelSoC | lo-byte |  |  |
| 140 | TotalDCPower | 2 reg | u32 | ✓ |
| 142 | TotalACPower | 2 reg | u32 | ✓ |
| 144 | TotalPVPower | 2 reg | u32 | ✓ |
| 146 | TotalGridPower | 2 reg | u32 | ✓ |
| 148 | TotalInvPower | 2 reg | u32 |  |
| 150 | TotalDCEnergy | 2 reg | /10 u32 |  |
| 152 | TotalACEnergy | 2 reg | /10 u32 |  |
| 154 | TotalPVChargingEnergy | 2 reg | /10 u32 |  |
| 156 | TotalGridChargingEnergy | 2 reg | /10 u32 |  |
| 158 | TotalFeedbackEnergy | 2 reg | /10 u32 |  |
| 160 | ChargingMode | lo-byte |  |  |
| 161 | InvWorkingStatus | lo-byte |  |  |
| 162 | PvToAcEnergy | 2 reg | /10 u32 |  |
| 164 | SelfSufficiencyRate | lo-byte |  |  |
| 165 | PvToAcPower | 2 reg | u32 |  |
| 167 | PackDsgEnergyTotal | 2 reg | /10 u32 |  |
| 169 | RateVoltage | u16 |  |  |
| 170 | RateFrequency | u16 |  |  |
| 175 | SceneFlag | lo-byte |  |  |
| 178 | SleepStandbyTime | 2 reg | u32 |  |
| 180 | PackChgEnergyTotal | 2 reg | u32 |  |
| 182 | TotalCarPower | u16 |  |  |
| 183 | TotalEVPower | 2 reg | u32 |  |
| 214 | AcInputStatus | u16 |  |  |
| 215 | EnergyLines2 | u16 | bits |  |

### 1100 – Omvormer: basisinfo  
_bron: `ProtocolParserV2.parseInvBaseInfo`_

| Register | Veld (app-naam) | Type | Opmerking | In bt-lib |
|---:|---|---|---|:-:|
| 1100 | InvId | lo-byte |  |  |
| 1101 | InvType | 6 reg | ascii |  |
| 1107 | InvSN | 4 reg |  |  |
| 1111 | InvPowerType | lo-byte |  |  |
| 1112 | SoftwareNumber | lo-byte |  |  |
| 1142 | WorkingTimeNumber | lo-byte |  |  |
| 1143 | DevVoltageType | lo-byte |  |  |
| 1148 | WorkingTimeNumber | lo-byte |  |  |
| 1149 | DevVoltageType | lo-byte |  |  |
| 1151 | AmbientTemp | u16 |  |  |
| 1152 | InvMaxTemp | u16 |  |  |
| 1153 | PvDcdcMaxTemp | u16 |  |  |
| 1154 | FmVerDiff | u16 | bits |  |
| 1155 | InvChgLimitL1Power | u16 |  |  |
| 1156 | InvChgLimitL2Power | u16 |  |  |
| 1157 | InvChgLimitL3Power | u16 |  |  |
| 1158 | InvDisgLimitL3Power | u16 |  |  |
| 1159 | InvDisgLimitL3Power | u16 |  |  |
| 1160 | InvDisgLimitL3Power | u16 |  |  |
| 1161 | InputRateCurrentL1 | u16 |  |  |
| 1162 | InputRateCurrentL2 | u16 |  |  |
| 1163 | InputRateCurrentL3 | u16 |  |  |
| 1164 | OutputRateCurrentL1 | u16 |  |  |
| 1165 | OutputRateCurrentL2 | u16 |  |  |
| 1166 | OutputRateCurrentL3 | u16 |  |  |
| 1167 | GridInputRateCurrentL1 | u16 |  |  |
| 1168 | GridInputRateCurrentL2 | u16 |  |  |
| 1169 | GridInputRateCurrentL3 | u16 |  |  |

### 1200 – Omvormer: PV  
_bron: `ProtocolParserV2.parseInvPVInfo`_

| Register | Veld (app-naam) | Type | Opmerking | In bt-lib |
|---:|---|---|---|:-:|
| 1200 | TotalChgPower | 2 reg | u32 |  |
| 1202 | TotalChgEnergy | 2 reg | /10 u32 |  |

### 1300 – Omvormer: net (grid)  
_bron: `ProtocolParserV2.parseInvGridInfo`_

| Register | Veld (app-naam) | Type | Opmerking | In bt-lib |
|---:|---|---|---|:-:|
| 1300 | Frequency | u16 | /10 |  |
| 1301 | TotalChgPower | 2 reg | u32 |  |
| 1303 | TotalChgEnergy | 2 reg | /10 u32 |  |
| 1305 | TotalFeedbackEnergy | 2 reg | /10 |  |

### 1400 – Omvormer: belasting  
_bron: `ProtocolParserV2.parseInvLoadInfo`_

| Register | Veld (app-naam) | Type | Opmerking | In bt-lib |
|---:|---|---|---|:-:|
| 1400 | DcLoadTotalPower | 2 reg | u32 |  |
| 1402 | DcLoadTotalEnergy | 2 reg | /10 u32 |  |
| 1404 | Dc5VPower | u16 |  |  |
| 1405 | Dc5VCurrent | u16 | /10 |  |
| 1406 | Dc12VPower | u16 |  |  |
| 1407 | Dc12VCurrent | u16 | /10 |  |
| 1408 | Dc24VPower | u16 |  |  |
| 1409 | Dc24VCurrent | u16 | /10 |  |
| 1412 | DcVoltTotal | u16 | /10 |  |
| 1413 | DcCurrentTotal | u16 | /10 |  |
| 1420 | AcLoadTotalPower | 2 reg | u32 |  |
| 1422 | AcLoadTotalEnergy | 2 reg | /10 u32 |  |

### 1500 – Omvormer: uitgang  
_bron: `ProtocolParserV2.parseInvInvInfo`_

| Register | Veld (app-naam) | Type | Opmerking | In bt-lib |
|---:|---|---|---|:-:|
| 1500 | Frequency | u16 | /10 |  |
| 1501 | TotalEnergy | 2 reg | /10 u32 |  |
| 1508 | SysPhaseNumber | lo-byte |  |  |
| 1535 | CustomPatternMatchingStrategy | lo-byte |  |  |

### 2000 – Basisinstellingen (lezen/schrijven)  
_bron: `ProtocolParserV2.parseInvBaseSettings`_

| Register | Veld (app-naam) | Type | Opmerking | In bt-lib |
|---:|---|---|---|:-:|
| 2000 | InvAddress | lo-byte |  |  |
| 2005 | WorkingMode | lo-byte |  |  |
| 2007 | CtrlLed | lo-byte |  |  |
| 2008 | CtrlGridChg | lo-byte |  |  |
| 2009 | CtrlPV | lo-byte |  |  |
| 2010 | CtrlInverter | lo-byte |  |  |
| 2011 | CtrlAC | lo-byte |  | ✓ |
| 2012 | CtrlDC | lo-byte |  | ✓ |
| 2014 | DcECOCtrl | lo-byte |  | ✓ |
| 2015 | DcECOOffTime | lo-byte |  | ✓ |
| 2016 | DcECOPower | lo-byte |  | ✓ |
| 2017 | AcECOCtrl | lo-byte |  | ✓ |
| 2018 | AcECOOffTime | lo-byte |  | ✓ |
| 2019 | AcECOPower | lo-byte |  | ✓ |
| 2020 | ChargingMode | lo-byte |  | ✓ |
| 2021 | PowerLiftingMode | lo-byte |  | ✓ |
| 2022 | SysLowPower | lo-byte |  | ✓ |
| 2023 | SysHighPower | lo-byte |  | ✓ |
| 2024 | MachineType | lo-byte |  |  |
| 2025 | MachineAddress | lo-byte |  |  |
| 2026 | HistoryEnergyType | lo-byte |  |  |
| 2027 | CurrentEnergyType | lo-byte |  |  |
| 2029 | CtrlWorkingTime | lo-byte |  |  |
| 2030 | CtrlTimeList | 30 reg |  |  |
| 2060 | Pv1type | lo-byte |  |  |
| 2061 | Pv2type | lo-byte |  |  |
| 2062 | Pv3type | lo-byte |  |  |
| 2063 | Pv4type | lo-byte |  |  |
| 2064 | Pv5type | lo-byte |  |  |
| 2065 | Pv6type | lo-byte |  |  |
| 2066 | CtrlAlarmSound | lo-byte |  |  |
| 2067 | LcdScreenTime | u16 |  | ✓ |
| 2068 | LoadPowerSet | u16 |  |  |
| 2071 | RateAcPower | u16 |  |  |
| 2072 | CustomFuncEnum | hi-byte |  |  |
| 2073 | AutoSleepDays | hi-byte |  |  |
| 2074 | RemoteStartupSoc | lo-byte |  |  |
| 2075 | SocHoldingLow | hi-byte |  |  |
| 2075 | SocHoldingLowEnable | lo-byte | bits |  |
| 2076 | ChildLockLevel | lo-byte |  |  |
| 2077 | SleepMinRemaining | u16 |  |  |
| 2078 | LedColor | lo-byte | &3 |  |
| 2078 | LedBrightness | hi-byte |  |  |
| 2079 | SleepPowerThreshold | lo-byte |  |  |
| 2080 | PackNumShow | hi-byte |  |  |
| 2080 | PackNumSet | lo-byte |  |  |
| 2081 | InvNumActual | hi-byte |  |  |
| 2081 | InvNumSet | lo-byte |  |  |
| 2083 | SocHoldingHigh | hi-byte |  |  |
| 2083 | SocHoldingHighEnable | lo-byte | &3 |  |
| 2084 | PvAdvEnable | u16 | bits |  |
| 2085 | CigaretteLighterVolt | u16 | &3 |  |
| 2086 | Ja122025Enable | u16 | &3 |  |
| 2087 | CycleCapacitySet | u16 |  |  |
| 2088 | CycleCapacityMax | u16 |  |  |
| 2093 | AcEnableRaw16 | u16 |  |  |
| 2093 | AcEnableList | u16 | bits |  |
| 2094 | DcEnableList | u16 | bits |  |
| 2095 | DcPortModeList | u16 | bits |  |

### 2200 – Geavanceerde instellingen  
_bron: `ProtocolParserV2.parseInvAdvSettings`_

| Register | Veld (app-naam) | Type | Opmerking | In bt-lib |
|---:|---|---|---|:-:|
| 2200 | AdvLoginPassword | 4 reg | ascii |  |
| 2206 | FactoryReset | lo-byte |  |  |
| 2207 | CtrlGrid | lo-byte |  |  |
| 2208 | CtrlFeedback | lo-byte |  |  |
| 2209 | InvVoltage | lo-byte |  |  |
| 2210 | InvFreq | lo-byte |  |  |
| 2211 | ChgMaxVoltage | u16 |  |  |
| 2212 | ChgMaxCurrent | u16 |  |  |
| 2213 | GridMaxPower | u16 |  |  |
| 2214 | GridMaxCurrent | u16 |  |  |
| 2215 | FeedbackMaxPower | u16 |  |  |
| 2216 | FeedbackMaxCurrent | u16 |  |  |
| 2217 | GridOffAcRatePower | u16 |  |  |
| 2218 | UserArea | u16 |  |  |
| 2225 | CtrlGridEnhanced | lo-byte |  |  |
| 2226 | SysSwitchRecovery | lo-byte |  |  |
| 2227 | MeterCtrl | lo-byte |  |  |
| 2228 | MeterType | lo-byte |  |  |
| 2229 | CtrlMultiInv | lo-byte |  |  |
| 2230 | InvAddr | lo-byte |  |  |
| 2231 | CtTestResult | hi-byte |  |  |
| 2231 | CtTest | lo-byte |  |  |
| 2232 | AcInputGenManualEnable | hi-byte |  |  |
| 2241 | EmsCtrlMode | lo-byte |  |  |
| 2243 | ChargingPileVoltage | lo-byte |  |  |
| 2244 | CtRatioOfAcPv | hi-byte |  |  |
| 2244 | CtRatioOfGridPort | lo-byte |  |  |
| 2245 | AcCTTestResult | hi-byte |  |  |
| 2245 | AcCTTestEnable | lo-byte |  |  |
| 2246 | GenSettings | u16 | bits |  |
| 2246 | AcInputGenCtrlMode | hi-byte |  |  |
| 2246 | AcInputGenDisableTimeEnable | hi-byte |  |  |
| 2247 | GenSocStart | lo-byte |  |  |
| 2248 | GenSocStop | lo-byte |  |  |
| 2258 | GridUVValue | u16 |  |  |
| 2259 | GridUVTime | u16 |  |  |
| 2260 | GridOVValue | u16 |  |  |
| 2261 | GridOVTime | u16 |  |  |
| 2262 | GridUFValue | u16 |  |  |
| 2263 | GridUFTime | u16 |  |  |
| 2264 | GridOFValue | u16 |  |  |
| 2265 | GridOFTime | u16 |  |  |
| 2266 | CounterCurrentPowerLimit | u16 |  |  |
| 2267 | GridMeterType | hi-byte |  |  |
| 2267 | GridMeterCtrl | lo-byte |  |  |
| 2269 | PvAdvEnable | hi-byte |  |  |
| 2269 | PvCtrl | lo-byte |  |  |
| 2270 | PhaseVoltage | hi-byte |  |  |
| 2270 | PhaseMode | lo-byte |  |  |
| 2271 | DcVoltSet | hi-byte |  |  |
| 2271 | DcVoltSetEnable | lo-byte | bits |  |
| 2272 | GridMaxCurrentInput2 | u16 |  |  |
| 2273 | FuncEnableSet | u16 | bits |  |
| 2274 | SceneUse | lo-byte |  |  |
| 2274 | SceneSub | hi-byte |  |  |
| 2275 | AltOutputOffDelay | u16 |  |  |
| 2276 | RvEnableList | u16 | bits |  |
| 2276 | RvGenType | hi-byte |  |  |
| 2277 | BatteryCapacity | 2 reg | u32 |  |
| 2279 | BatteryType | hi-byte |  |  |
| 2279 | BatteryModelType | lo-byte |  |  |
| 2280 | HeadPumpEnable | 5 reg |  |  |
| 2304 | MultiPeakEnable | lo-byte |  |  |
| 2304 | MultiPeakScanTime | hi-byte |  |  |
| 2306 | AcInputMode | lo-byte |  |  |
| 2306 | AcInputCheckEnable | hi-byte |  |  |
| 2306 | AcInputPortEnable | hi-byte |  |  |

### 3500 – Totale energie  
_bron: `ProtocolParserV2.parseTotalEnergyInfo`_

| Register | Veld (app-naam) | Type | Opmerking | In bt-lib |
|---:|---|---|---|:-:|
| 3500 | EnergyType | lo-byte |  |  |
| 3501 | TotalEnergy | 2 reg | /10 u32 |  |

### 3600 – Energie dit jaar  
_bron: `ProtocolParserV2.parseCurrYearEnergy`_

| Register | Veld (app-naam) | Type | Opmerking | In bt-lib |
|---:|---|---|---|:-:|
| 3600 | EnergyType | lo-byte |  |  |
| 3601 | Year | u16 |  |  |
| 3601 | TotalEnergy | 2 reg | /10 u32 |  |

### 5000 – Tijdsturing  
_bron: `ProtocolParserV2.parseTimeCtrlInfo`_

| Register | Veld (app-naam) | Type | Opmerking | In bt-lib |
|---:|---|---|---|:-:|
| 5000 | WeekModeBinary | u16 | bits |  |

### 5800 – EMS  
_bron: `ProtocolParserV2.parseEmsSettings`_

| Register | Veld (app-naam) | Type | Opmerking | In bt-lib |
|---:|---|---|---|:-:|
| 5801 | AcCouplingSwitch | u16 | &3 |  |
| 5802 | AcCouplingMin | u16 |  |  |

### 6000 – Accupack: hoofdinfo  
_bron: `ProtocolParserV2.parsePackMainInfo`_

| Register | Veld (app-naam) | Type | Opmerking | In bt-lib |
|---:|---|---|---|:-:|
| 6000 | PackVoltType | u16 |  |  |
| 6001 | PackCnts | lo-byte |  |  |
| 6002 | PackOnline | u16 | bits |  |
| 6003 | TotalVoltage | u16 | /10 |  |
| 6004 | TotalCurrent | u16 | /10 |  |
| 6005 | TotalSOC | lo-byte |  |  |
| 6006 | TotalSOH | lo-byte |  |  |
| 6007 | AverageTemp | u16 |  |  |
| 6008 | RunningStatus | lo-byte |  |  |
| 6009 | ChargingStatus | lo-byte |  |  |
| 6010 | MaxChgVoltage | u16 | /10 |  |
| 6011 | MaxChgCurrent | u16 | /10 |  |
| 6012 | MaxDsgCurrent | u16 | /10 |  |
| 6017 | PackChgFullTime | u16 |  |  |
| 6018 | PackDsgEmptyTime | u16 |  |  |
| 6016 | PackMos | u16 | bits |  |
| 6031 | PackFaultBit | u16 | bits |  |
| 6033 | BcuBalancePower | u16 |  |  |

### 6100 – Accupack: per pack  
_bron: `ProtocolParserV2.parsePackItemInfo`_

| Register | Veld (app-naam) | Type | Opmerking | In bt-lib |
|---:|---|---|---|:-:|
| 6100 | PackID | lo-byte |  |  |
| 6101 | PackType | 6 reg | ascii |  |
| 6107 | PackSN | 4 reg |  |  |
| 6111 | Voltage | u16 | /100 |  |
| 6112 | Current | u16 | /10 |  |
| 6113 | PackSoc | lo-byte |  |  |
| 6114 | PackSoh | lo-byte |  |  |
| 6115 | AverageTemp | u16 |  |  |
| 6124 | RunningStatus | lo-byte |  |  |
| 6125 | ChargingStatus | lo-byte |  |  |
| 6129 | PackCapOnline | lo-byte |  |  |
| 6152 | TotalCellCnt | lo-byte |  |  |
| 6153 | NtcCellCnt | lo-byte |  |  |
| 6154 | BmuCnt | lo-byte |  |  |
| 6155 | BmuFaultBit | u16 | bits |  |
| 6171 | BmuType | lo-byte |  |  |
| 6173 | SoftwareNumber | lo-byte |  |  |

### 7000 – Accupack: instellingen  
_bron: `ProtocolParserV2.parsePackSettingsInfo`_

| Register | Veld (app-naam) | Type | Opmerking | In bt-lib |
|---:|---|---|---|:-:|
| 7000 | PackId | lo-byte |  |  |
| 7001 | OffGridHeatingAdaptationEnable | lo-byte |  |  |
| 7002 | PackHeat | lo-byte |  |  |
| 7003 | PackUnlock | lo-byte |  |  |
| 7004 | PackParallelNumber | u16 |  |  |
| 7010 | BmsCommProtType | hi-byte |  |  |
| 7010 | BmsCommInterfaceType | lo-byte |  |  |