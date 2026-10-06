# Bluetti app v3.1.4 – lokaal protocol (uit APK-analyse)

## Verbindingsmodi in de app
- `ConnMode`: alleen `BLUETOOTH` en `REMOTE`. REMOTE = cloud-MQTT `ssl://iot.bluettipower.com:18760` (TOTP-auth).
- Geen lokale WiFi/LAN-API in de app.

## BLE
- Service `0000ff00-…`, write `0000ff02-…`, notify `0000ff01-…` (CCCD 0x2902)
- MTU 247/517 bij ESP32-modules
- Advertising-data `BLUETTI` (`424c5545545449`) = onversleuteld, `BLUETTE` (`424c5545545445`) = versleuteld

## Handshake (versleutelde apparaten), `ConnectManager.bleEncryptedHandle`
Handshakeframes: `2A 2A <cmd> <len> <payload> <sum16>` (checksum = byte-som over cmd+len+payload).
1. Apparaat → `2A2A 01 ..` met 4 random bytes (byte 4..7).
   `randomMd5 = MD5(reversed(random))` (hex).
   App → `2A2A 0204 <randomMd5[16:24]> <sum>`.
   `bleConnAESKey = randomMd5 XOR <vaste sleutel uit de app>`
2. Apparaat → versleuteld (AES-CBC, key = bleConnAESKey, IV = randomMd5) frame cmd `04`:
   bytes 4..67 = IoT public key (secp256r1, raw X||Y), rest = ECDSA-signatuur (verifieer met K2).
3. App genereert ECDH-keypair (secp256r1). Stuurt `2A2A 0580 <pubkey64> <sig64> <sum>`,
   sig = SHA256withECDSA over (eigen pubkey || randomMd5) met privésleutel L1, omgezet naar raw r||s.
4. Apparaat → cmd `06`, byte 4 == 0 → OK. `bleConnShareKey = ECDH(eigen priv, iot pub)` (32 bytes = AES-256 key).

De vaste sleutels (AES-masker, ondertekensleutel L1, verificatiesleutel K2) staan in de app
(`SignatureCrypt`) en zijn al geïmplementeerd in `bluetti_bt_lib/bluetooth/encryption.py`.

## Versleutelde frames na handshake (`ProtocolParse.buildAESCBCCmd/parseAESCBCData`)
- Zenden: `<len u16 BE (plaintext)> <iv4 random> <AES-CBC(blocks, zero-padded)>`; IV = MD5(iv4); key = bleConnShareKey.
- Ontvangen: idem, eerste 4 bytes len, dan 4 bytes iv-seed, dan ciphertext.
- Plaintext = standaard Modbus RTU: `01 03 addr cnt crc16` (lezen), `01 06` (enkel register), `01 10` (meerdere).

## Belangrijke registers
V1 (oudere AC/EP-modellen, `ProtocolAddr`): `3000..` instelbare data, bv.
3001 WORKING_MODE, 3007 AC_SWITCH, 3008 DC_SWITCH, 3011 GRID_CHARGING_SWITCH,
3023-3030 laad/ontlaad-tijden, 3057/3058 max laad-/ontlaadvermogen, 3061 LCD-tijd,
3063-3070 ECO-instellingen, 3065 CHARGING_MODE/SILENT, 3066 POWER_LIFTING.

V2 (nieuwere modellen, `ProtocolAddrV2`): 100 APP_HOME_DATA, 1100-1700 inverter/PV/grid/load/meter info,
2000 INV_BASE_SETTINGS: 2005 WORKING_MODE, 2011 AC_SWITCH, 2012 DC_SWITCH, 2014-2019 ECO,
2020 CHARGING_MODE, 2021 SUPER_POWER, 2022/2023 SOC laag/hoog, 2075/2083 SOC_SET_LOW/HIGH,
2207 CTRL_GRID, 2208 CTRL_FEED, 2213-2216 grid-/feed-in max stroom/vermogen,
5000 TIME_CTRL (weekschema), 5800 EMS_SETTINGS, 6000 PACK_MAIN_INFO,
19000 COMM_SOC_SETTINGS, 19200 COMM_SCHEDULED_CHG_DSG, 19300 COMM_TIMER_SETTINGS, 26000/26001 TOU.

Gedecompileerde bronnen: scratchpad `src/net/poweroak/...` (androguard/DAD).
