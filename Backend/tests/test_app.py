from app import calculate_bill


def test_bill_walks_slabs_for_gujarat_200_units():
    bill = calculate_bill(200, "Gujarat", "Residential (RGP)")

    # 50 x 3.20 + 50 x 3.65 + 100 x 4.25
    assert bill["energy_charge"] == 767.5
    assert bill["fppas_charge"] == 460.0
    assert bill["fixed_charge"] == 25
    assert bill["electricity_duty"] == 62.62
    assert bill["total_bill"] == 1315.12
    assert [slab["units"] for slab in bill["slab_breakdown"]] == [50, 50, 100]


def test_calculate_endpoint_returns_bill_and_solar(client, payload):
    response = client.post("/calculate", json=payload)

    assert response.status_code == 200
    data = response.get_json()
    assert data["bill"]["total_bill"] == 1315.12
    assert data["solar"]["gross_cost"] == 165000
    assert data["solar"]["subsidy"] == 78000
    assert data["environment"]["co2_kg"] == 164.0
    assert data["environment"]["trees_equivalent"] == 7.6


def test_compare_sorts_by_total_bill(client):
    response = client.post("/compare", json={"units": 200})

    assert response.status_code == 200
    bills = [item["total_bill"] for item in response.get_json()["comparison"]]
    assert bills == sorted(bills)
    assert len(bills) == 5


def test_frontend_served_from_root(client):
    response = client.get("/")

    assert response.status_code == 200
    assert b"VoltIQ" in response.data


def test_environment_factors_come_from_config(client, payload, monkeypatch):
    import config

    monkeypatch.setattr(config, "CO2_KG_PER_KWH", 1.0)
    monkeypatch.setattr(config, "CO2_KG_PER_TREE", 20.0)

    data = client.post("/calculate", json=payload).get_json()

    assert data["environment"]["co2_kg"] == 200.0
    assert data["environment"]["trees_equivalent"] == 10.0
