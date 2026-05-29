import os

# Disable rate limiting for the test suite. This must be set before the app
# (and the rate_limiter module, which reads the flag at import time) is imported,
# so it lives here in conftest.py — pytest loads this before any test module.
os.environ.setdefault("DISABLE_RATE_LIMIT", "true")

import pytest

from app.middleware.rate_limiter import auth_rate_limiter, api_rate_limiter


@pytest.fixture(autouse=True)
def reset_rate_limiters():
    """Clear in-memory rate-limiter state between tests for isolation.

    Belt-and-suspenders alongside DISABLE_RATE_LIMIT: keeps tests independent
    even if a test re-enables the limiter to exercise it directly.
    """
    auth_rate_limiter.reset()
    api_rate_limiter.reset()
    yield
