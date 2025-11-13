# ProNatura for Home Assistant

Custom integration that downloads the ProNatura garbage collection schedule
and exposes one date sensor per supported fraction.

## Features

- Config flow with searchable street and address lists returned from the ProNatura API.
- Sensor entities for every waste fraction.
- Daily data refresh, diagnostics download, and Repairs reconfiguration support.

## Installation

### HACS (recommended)

1. In HACS open **Integrations → ⋮ → Custom repositories** and add `https://github.com/nilvanis/ha-pronatura` with category **Integration**.
2. Search for **ProNatura** inside HACS and install the integration.
3. Restart Home Assistant to load the new custom component.

### Manual copy

1. Download the latest release or clone this repository.
2. Copy the `custom_components/pronatura` directory into the `custom_components` folder of your Home Assistant configuration.
3. Restart Home Assistant.

## Configuration

1. Navigate to **Settings → Devices & Services → Add Integration** and search for **ProNatura**.
2. Pick your street from the list populated by the API.
3. Select the building number / address point that matches your location.
4. Confirm the summary – the integration will create sensors for every fraction that is served at that address.

## Sensor data

Each waste fraction is exposed as a `date` sensor whose state is the next scheduled
collection date. In case there is no upcoming collection date in the schedule, it will show the last one. If there is no dates at all, sensor will have an `unknown` state.\
Attributes:

- `full_address` – formatted street + building number.
- `fraction_name` – label provided by ProNatura.
- `area`, `building_type`, and optional `address_name` metadata.

The sensors refresh once per day.
