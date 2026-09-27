# Peblar REST

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A public [HACS](https://hacs.xyz/) custom integration for controlling and monitoring
Peblar EV chargers through Peblar's local REST API.

The integration uses the distinct `peblar_rest` domain, so it can coexist with Home
Assistant's built-in `peblar` integration and the `peblar_modbus` custom integration.
All charger communication stays on your local network.

## Features

- Automatic zeroconf discovery and manual setup
- Secure password input, reauthentication, and host/password reconfiguration
- Configurable local polling (10 seconds by default; minimum 5 seconds)
- Charging state, current-limit source, power, energy, phase, signal, and diagnostic
  sensors
- Charge current, charging, phase selection, socket lock, identify, restart, and
  socket-unlock controls
- Smart-charging, buzzer, and LED controls
- Firmware and customization update entities
- Firmware 1.10 `CustomSolar` mode, grid target, power threshold, and always-charge
  controls
- Downloadable diagnostics with credentials and device/network identifiers redacted

The integration uses the maintained
[`peblar==2.1.0`](https://github.com/frenck/python-peblar/releases/tag/v2.1.0)
client for authentication, API-token refresh, protocol models, retries, rate-limit
backoff, minimum-firmware checks, and firmware 1.10 endpoint compatibility. The
client is vendored in `custom_components/peblar_rest/_peblar` so it never replaces
the older `peblar` package that Home Assistant bundles for its built-in integration.

## Requirements

- A Peblar charger with firmware 1.6 or newer; firmware 1.10 or newer is required
  for Custom Solar controls
- Home Assistant with network access to the charger
- The password for the charger's local web interface

During setup the integration enables the local REST API in **read/write** mode and
obtains its API token through the authenticated local web interface. The password is
stored only in Home Assistant's config entry, is entered using a password field, is
never logged, and is redacted from diagnostics.

## Installation

### HACS

1. Open HACS, select **Integrations**, then open the menu and choose
   **Custom repositories**.
2. Add `https://github.com/JannicSJensen/peblar-rest` as an **Integration**.
3. Install **Peblar REST** and restart Home Assistant.

### Manual

Copy `custom_components/peblar_rest` into your Home Assistant
`custom_components` directory and restart Home Assistant.

## Configuration

Go to **Settings → Devices & services → Add integration**, search for
**Peblar REST**, and enter the charger's hostname or IP address and local web-interface
password. Discovered chargers also appear automatically.

Use **Reconfigure** on the integration entry after an IP address or password change.
Home Assistant starts a reauthentication flow when the charger rejects stored
credentials. The options dialog changes the poll interval.

## Controls and safety

Setting the charge switch off writes a 0 mA local REST limit. Turning it back on
restores the last limit (6 A initially). Peblar specifies that pausing must not happen
more than three times per rolling ten-minute window to protect the charger and vehicle
relays; automations must respect that constraint.

The integration exposes controls only when the charger reports the required hardware
or firmware capability. Package updates are installed in Peblar's required order:
customization before firmware. An update can temporarily make entities unavailable
while the charger reboots.

## Troubleshooting

- Confirm the charger is reachable from the Home Assistant host over local HTTP.
- Confirm firmware is at least 1.6 and the web-interface password is correct.
- Avoid polling the same charger aggressively from several clients. Peblar allows
  five requests per second across all clients, with a burst of ten.
- Download diagnostics from the integration entry before opening an issue. Passwords,
  host addresses, serial numbers, MAC addresses, and customer identifiers are redacted.
- Enable debug logging when needed:

  ```yaml
  logger:
    logs:
      custom_components.peblar_rest: debug
      peblar: debug
  ```

Hardware-backed operations cannot be fully tested without a charger. When reporting an
issue, include the firmware version, charger model, relevant Home Assistant logs, and
redacted diagnostics.

## Development

Run the repository checks with:

```bash
python3 -m compileall -q custom_components tests
python3 -m json.tool custom_components/peblar_rest/manifest.json >/dev/null
python3 -m ruff check .
python3 -m ruff format --check .
python3 -m pytest
```

Protocol behavior follows Peblar's
[official local REST API](https://developer.peblar.com/) and the maintained
[python-peblar](https://github.com/frenck/python-peblar) client. This project is an
independent custom integration and is not affiliated with Peblar.

## License

[MIT](LICENSE)
