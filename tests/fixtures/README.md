# Test Fixtures

This directory contains JSON fixtures for mocking ProNatura API responses.

## Files

- `streets.json` - Response from GET /streets
- `address_points.json` - Response from GET /address-points/{street_id}
- `trash_schedule.json` - Response from GET /trash-schedule/{address_id}
- `trash_schedule_empty.json` - Schedule with no collection dates
- `trash_schedule_malformed.json` - Invalid data for error handling tests

## Usage

Fixtures are loaded in `conftest.py` and injected into tests via `mock_api_responses` fixture.

## Updating Fixtures

To capture new real responses:
1. Run integration tests: `pytest -m integration tests/integration/`
2. Capture response and save to JSON
3. Redact sensitive data (addresses, IDs)
