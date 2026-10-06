# hassio-bluetti-bt
[![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg)](https://github.com/hacs/integration)
[![Validate with hassfest](https://github.com/Patrick762/hassio-bluetti-bt/actions/workflows/hassfest_validation.yml/badge.svg)](https://github.com/Patrick762/hassio-bluetti-bt/actions/workflows/hassfest_validation.yml)
[![HACS Action](https://github.com/Patrick762/hassio-bluetti-bt/actions/workflows/HACS.yml/badge.svg)](https://github.com/Patrick762/hassio-bluetti-bt/actions/workflows/HACS.yml)

Bluetti Integration for Home Assistant

The current [Roadmap for this project and the library can be found here](https://github.com/users/Patrick762/projects/4)

## About this fork

This fork of [Patrick762/hassio-bluetti-bt](https://github.com/Patrick762/hassio-bluetti-bt)
builds on the encrypted-write work of [wannessels](https://github.com/wannessels/hassio-bluetti-bt)
and uses the [nlimper/bluetti-bt-lib](https://github.com/nlimper/bluetti-bt-lib) library. It adds:

- **Elite 200 V2** support, checked against a live unit: AC input/output as apparent
  power (VA, which is what the unit reports), battery voltage, health and temperature,
  lifetime energy counters for the Energy dashboard, and the settings below.
- Writes that are read back and retried; a write that does not hold raises an error.
- **Number** entities (SOC low/high, max grid charge current) and **time** entities.
- The six **time slots** of Customized UPS: a select for the mode (off, charge,
  discharge, standby) and a start and end time per slot, plus the service
  `bluetti_bt.set_time_slot` to set mode, start and end in one write. Overlapping
  active slots are refused.
- Discovery on the BLUETTI manufacturer data, so new models are found without a name
  matcher.
- Dutch translation.

Breaking change compared to upstream: select options are lowercase and translated
(`turbo` instead of `TURBO`). Automations that select an option need the new value.

On the Elite 200 V2 the AC and DC outputs, power off and AC ECO are deliberately
read-only.

To install this fork, add `https://github.com/nlimper/hassio-bluetti-bt` to HACS as a
custom repository (category: Integration).

Research notes (protocol, register map, test results) are in [docs/](docs/).

## Disclaimer
This integration is provided without any warranty or support by Bluetti. I do not take responsibility for any problems it may cause in all cases. Use it at your own risk.

## Installation
To install this integration, you first need [HACS](https://hacs.xyz/) installed.
After the installation, you can use this button to install the integration:

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Patrick762&repository=hassio-bluetti-bt&category=integration)

### Supported devices:

See [bluetti-bt-lib](https://github.com/Patrick762/bluetti-bt-lib?tab=readme-ov-file#supported-powerstations-and-data)

### Available controls:
See [bluetti-bt-lib](https://github.com/Patrick762/bluetti-bt-lib?tab=readme-ov-file#supported-powerstations-and-data)

### Adding devices or fields

Please use the issue template at [bluetti-bt-lib](https://github.com/Patrick762/bluetti-bt-lib?tab=readme-ov-file#supported-powerstations-and-data)
