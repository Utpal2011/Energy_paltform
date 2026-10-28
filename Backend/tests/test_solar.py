import pytest

from app import tariffs


def solar_for(client, payload, **changes):
    return client.post("/calculate", json={**payload, **changes}).get_json()["solar"]


# 3 kW in Gujarat generates more than the 200 units consumed, so there is surplus.


@pytest.mark.parametrize("system_type", ["on_grid", "hybrid"])
def test_grid_connected_systems_earn_export_income(client, payload, system_type):
    solar = solar_for(client, payload, system_type=system_type)

    assert solar["export_allowed"] is True
    assert solar["export_income"] > 0


def test_off_grid_earns_no_export_income(client, payload):
    solar = solar_for(client, payload, system_type="off_grid")

    assert solar["export_allowed"] is False
    assert solar["export_income"] == 0


def test_no_export_income_without_net_metering(client, payload, monkeypatch):
    monkeypatch.setitem(tariffs["Gujarat"]["solar"], "net_metering", False)

    solar = solar_for(client, payload)

    assert solar["export_allowed"] is False
    assert solar["export_income"] == 0


@pytest.mark.parametrize(
    "system_type, gross, net, is_estimate",
    [
        ("on_grid", 165000, 87000, False),
        ("hybrid", 247500, 169500, True),  # 1.5x panels; battery unsubsidised
        ("off_grid", 297000, 297000, True),  # 1.8x panels; no subsidy
    ],
)
def test_gross_cost_scales_by_system_type(client, payload, system_type, gross, net, is_estimate):
    solar = solar_for(client, payload, system_type=system_type)

    assert solar["gross_cost"] == gross
    assert solar["net_cost"] == net
    assert solar["cost_is_estimate"] is is_estimate
    assert ("estimate" in solar["cost_note"].lower()) is is_estimate


def test_generation_includes_system_losses(client, payload):
    solar = solar_for(client, payload)

    # 3 kW x 5.5 h x 30 days x 0.80 performance ratio
    assert solar["monthly_generation_units"] == 396.0
    assert solar["performance_ratio"] == 0.80
    assert solar["annual_degradation"] == 0.005


def test_degradation_reduces_lifetime_savings(client, payload):
    solar = solar_for(client, payload)

    no_degradation = solar["annual_savings"] * 25 - solar["net_cost"]
    assert solar["lifetime_savings"] < no_degradation


def test_without_degradation_matches_simple_model(client, payload, monkeypatch):
    import config

    monkeypatch.setattr(config, "ANNUAL_DEGRADATION", 0)
    solar = solar_for(client, payload)

    expected_lifetime = solar["annual_savings"] * 25 - solar["net_cost"]
    assert solar["lifetime_savings"] == pytest.approx(expected_lifetime, abs=1)
    assert solar["payback_years"] == round(solar["net_cost"] / solar["annual_savings"], 1)


def test_payback_never_reached_reports_no_payback(client, payload, monkeypatch):
    monkeypatch.setitem(tariffs["Gujarat"]["solar"], "cost_per_kw", 10_000_000)

    assert solar_for(client, payload)["payback_years"] == 99


def test_compare_includes_losses(client):
    response = client.post("/compare", json={"units": 200, "states": ["Gujarat"]})
    gujarat = response.get_json()["comparison"][0]

    # PR and degradation lengthen payback beyond the old 3.7 years
    assert gujarat["solar_payback_years"] > 3.7


def test_payback_reached_flag_true_for_normal_system(client, payload):
    assert solar_for(client, payload)["payback_reached"] is True


def test_payback_reached_flag_false_when_never_paid_back(client, payload, monkeypatch):
    monkeypatch.setitem(tariffs["Gujarat"]["solar"], "cost_per_kw", 10_000_000)

    solar = solar_for(client, payload)

    assert solar["payback_reached"] is False


def test_compare_reports_payback_reached(client, monkeypatch):
    monkeypatch.setitem(tariffs["Gujarat"]["solar"], "cost_per_kw", 10_000_000)

    response = client.post("/compare", json={"units": 200, "states": ["Gujarat", "Delhi"]})
    rows = {row["state"]: row for row in response.get_json()["comparison"]}

    assert rows["Gujarat"]["solar_payback_reached"] is False
    assert rows["Delhi"]["solar_payback_reached"] is True


def test_frontend_formats_unreached_payback():
    from pathlib import Path

    script = (Path(__file__).resolve().parents[2] / "Frontend" / "script.js").read_text(encoding="utf-8")

    assert "Not within panel life" in script
    assert "${solar.payback_years} yrs" not in script
    assert "${item.solar_payback_years} years" not in script
