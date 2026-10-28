import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import app  # noqa: E402


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as test_client:
        yield test_client


@pytest.fixture
def payload():
    return {
        "units": 200,
        "state": "Gujarat",
        "category": "Residential (RGP)",
        "system_kw": 3,
        "system_type": "on_grid",
    }
