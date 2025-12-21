"""Pytest configuration for integration tests.

Integration tests in this directory test against the REAL ProNatura API when
explicitly requested with the integration marker. Socket blocking is automatically
disabled for these tests, as AWS API Gateway uses dynamic IP addresses.

Access control is provided by requiring explicit marker selection:
    pytest -m integration tests/
"""

import socket as socket_module

import pytest


@pytest.fixture(autouse=True)
def _enable_real_api_sockets(request):
    """Completely disable socket blocking for integration tests."""
    # Only enable sockets if this test is marked as integration
    if "integration" in request.keywords:
        # Get the original socket class before pytest-socket wrapped it
        import _socket

        # Restore the original socket.socket class to bypass pytest-socket
        # This needs to run for EACH test because pytest-socket rewraps between tests
        socket_module.socket = _socket.socket
