import pytest

from app import calculate_subsidy, tariffs

GUJARAT_SOLAR = tariffs["Gujarat"]["solar"]
RESIDENTIAL = "Residential (RGP)"


@pytest.mark.parametrize(
    "system_kw, expected",
    [(0.5, 0), (1, 30000), (1.9, 30000), (2, 60000), (2.5, 60000), (3, 78000), (10, 78000)],
)
def test_subsidy_bands_for_residential_on_grid(system_kw, expected):
    assert calculate_subsidy(system_kw, RESIDENTIAL, "on_grid", GUJARAT_SOLAR) == expected


def test_hybrid_gets_same_subsidy_as_on_grid():
    assert calculate_subsidy(3, RESIDENTIAL, "hybrid", GUJARAT_SOLAR) == 78000


def test_off_grid_gets_no_subsidy():
    assert calculate_subsidy(3, RESIDENTIAL, "off_grid", GUJARAT_SOLAR) == 0


@pytest.mark.parametrize("category", ["Commercial (Non-RGP)", "Agricultural (AGP)"])
def test_non_residential_gets_no_subsidy(category):
    assert calculate_subsidy(3, category, "on_grid", GUJARAT_SOLAR) == 0


def test_bpl_residential_category_is_eligible():
    solar = tariffs["Maharashtra"]["solar"]
    assert calculate_subsidy(3, "Residential (BPL)", "on_grid", solar) == 78000


def test_subsidy_max_kw_caps_the_band():
    solar = {**GUJARAT_SOLAR, "subsidy_max_kw": 2}
    assert calculate_subsidy(3, RESIDENTIAL, "on_grid", solar) == 60000


def test_subsidy_never_exceeds_panel_only_cost():
    solar = {**GUJARAT_SOLAR, "cost_per_kw": 20000}
    # panel cost 1 kW x 20000 is below the 30000 band
    assert calculate_subsidy(1, RESIDENTIAL, "hybrid", solar) == 20000


def test_eligible_types_come_from_config(monkeypatch):
    import config

    monkeypatch.setattr(config, "SUBSIDY_ELIGIBLE_TYPES", {"on_grid"})
    assert calculate_subsidy(3, RESIDENTIAL, "hybrid", GUJARAT_SOLAR) == 0


def test_calculate_reports_commercial_subsidy_reason(client, payload):
    payload["category"] = "Commercial (Non-RGP)"
    solar = client.post("/calculate", json=payload).get_json()["solar"]

    assert solar["subsidy"] == 0
    assert "residential" in solar["message"].lower()
