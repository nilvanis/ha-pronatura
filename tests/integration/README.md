# Integration Tests

Integration tests in this directory test against the **REAL ProNatura API**.

## Running Integration Tests

Integration tests are **disabled by default** and only run when explicitly requested using pytest markers.

### Run Integration Tests Only

```bash
pytest -m integration tests/
```

Or to run integration tests from this directory:

```bash
pytest -m integration tests/integration/
```

### Run All Tests (Including Integration)

To override the default and run all tests including integration:

```bash
pytest -m "" tests/
# or
pytest --override-ini="addopts=" tests/
```

### Run Unit Tests Only (Default)

By default, integration tests are skipped:

```bash
pytest tests/
```

## Socket Configuration

AWS API Gateway (which hosts the ProNatura API as of 2025) uses dynamic IP addresses that change frequently. `pytest-socket` host whitelisting cannot reliably handle this.

**Solution**: Socket blocking is automatically disabled for tests marked with `@pytest.mark.integration` via the `_enable_real_api_sockets` fixture in `tests/integration/conftest.py`. This is safe because:

1. Integration tests only run when explicitly requested with `-m integration`
2. Tests are designed to only connect to `BASE_API_URL` (https://zs5cv4ng75.execute-api.eu-central-1.amazonaws.com/prod)
3. The tests validate real API responses to ensure the client works correctly
4. Unit tests (default) still have full socket blocking enabled

## What Gets Tested

These integration tests verify:
- ✅ Streets list fetching
- ✅ Address points lookup
- ✅ Trash schedule retrieval
- ✅ Error handling (404, invalid street names)
- ✅ Response schema validation
- ✅ Full integration flow
