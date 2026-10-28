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
