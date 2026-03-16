import pytest

# Load all fixtures
pytest_plugins = [
    "tests.fixtures",
    "tests.mocks",
]

from django.core.cache import cache

@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
