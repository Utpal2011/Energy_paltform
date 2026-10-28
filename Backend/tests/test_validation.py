import pytest


def post(client, payload, **changes):
    return client.post("/calculate", json={**payload, **changes})


@pytest.mark.parametrize("units", ["abc", None, -5, 0, 100001, 12.5, True, [200]])
def test_calculate_rejects_bad_units(client, payload, units):
    response = post(client, payload, units=units)

    assert response.status_code == 400
    assert "units" in response.get_json()["error"]


@pytest.mark.parametrize("system_kw", ["x", "nan", "inf", -1, 0, 1500])
def test_calculate_rejects_bad_system_kw(client, payload, system_kw):
    response = post(client, payload, system_kw=system_kw)

    assert response.status_code == 400
    assert "system_kw" in response.get_json()["error"]


def test_system_kw_capped_by_state_max_capacity(client, payload):
    # Uttar Pradesh allows 500 kW, Gujarat 1000 kW
    assert post(client, payload, system_kw=1000).status_code == 200
    up = {**payload, "state": "Uttar Pradesh", "category": "Residential (LMV-1)"}
    assert post(client, up, system_kw=501).status_code == 400


def test_numeric_strings_are_accepted(client, payload):
    response = post(client, payload, units="200", system_kw="2.5")

    assert response.status_code == 200
    assert response.get_json()["units"] == 200


@pytest.mark.parametrize("field", ["state", "category", "system_type"])
def test_non_string_fields_rejected(client, payload, field):
    response = post(client, payload, **{field: ["Gujarat"]})

    assert response.status_code in (400, 404)


def test_non_object_body_rejected(client):
    response = client.post("/calculate", json=[1, 2, 3])

    assert response.status_code == 400


@pytest.mark.parametrize("states", ["Gujarat", [["Gujarat"]], ["Gujarat"] * 51])
def test_compare_rejects_bad_states(client, states):
    response = client.post("/compare", json={"units": 200, "states": states})

    assert response.status_code == 400
    assert "states" in response.get_json()["error"]


def test_compare_rejects_bad_units(client):
    response = client.post("/compare", json={"units": "lots"})

    assert response.status_code == 400


def test_oversized_body_rejected(client, payload):
    response = client.post(
        "/calculate", json={**payload, "padding": "x" * 20000}
    )

    assert response.status_code == 413
