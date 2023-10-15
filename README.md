# Cometblue Custom Component

[![GitHub Release][releases-shield]][releases]
[![License][license-shield]](LICENSE)

A custom component based on [zero-udo/eurotronic-cometblue](https://github.com/zero-udo/eurotronic-cometblue) to support Eurotronic's CometBlue thermostats (and similar).

We support the same devices as our upstream library:
- Eurotronic Comet Blue
- Sygonix HT100 BT
- Xavax Hama
- Lidl Silvercrest RT2000BT

This component aims to support as many of the TRV functions as possible, adding more step by step.

**This integration will set up the following platforms.**

Platform | Description
-- | --
`climate` | Climate entity with **target temperature**, **target temperature range** and **preset mode** support
`number` | Number entities to adjust additional TRV settings
`sensor` | Sensor entities for TRV state
`service` | Services to interact with schedules and dates

## Installation

1. Using the tool of choice open the directory (folder) for your HA configuration (where you find `configuration.yaml`).
1. If you do not have a `custom_components` directory (folder) there, you need to create it.
1. In the `custom_components` directory (folder) create a new folder called `integration_blueprint`.
1. Download _all_ the files from the `custom_components/integration_blueprint/` directory (folder) in this repository.
1. Place the files you downloaded in the new directory (folder) you created.
1. Restart Home Assistant
1. In the HA UI go to "Configuration" -> "Integrations" click "+" and search for "Integration blueprint"

## Configuration is done in the UI

<!---->

***

[license-shield]: https://img.shields.io/github/license/rikroe/cometblue-custom-component.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/rikroe/cometblue-custom-component.svg?style=for-the-badge
[releases]: https://github.com/rikroe/cometblue-custom-component/releases