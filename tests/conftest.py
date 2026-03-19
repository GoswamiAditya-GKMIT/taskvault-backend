import pytest
from django.conf import settings
from django.core.cache import cache

# Load all fixtures
pytest_plugins = [
    "tests.fixtures",
    "tests.mocks",
]

@pytest.fixture(autouse=True, scope="session")
def override_cache_settings():
    """
    Globally override the cache setting to use LocMemCache for all tests.
    This removes the dependency on a real Redis instance.
    """
    settings.CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "unique-snowflake",
        }
    }

@pytest.fixture(autouse=True)
def clear_cache():
    """
    Clear the cache before each test to ensure isolation.
    """
    cache.clear()
