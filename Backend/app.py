from flask import Flask, jsonify, request
from flask_cors import CORS
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR.parent / "Frontend"

# Serve the Frontend folder from the site root, so the whole app runs on one port.
app = Flask(__name__, static_folder=str(FRONTEND_DIR), static_url_path="")
CORS(app)

with open(BASE_DIR / "tariffs.json", encoding="utf-8") as f:
    tariffs = json.load(f)


def calculate_bill(units, state, category):
    data = tariffs[state]["categories"][category]
    slabs = data["slabs"]
    fixed_charge = data["fixed_charge"]
    fppas = data["fppas"]
    duty_pct = data["electricity_duty_pct"]

    remaining_units = units
    energy_charge = 0
    slab_breakdown = []

    for slab in slabs:
        if remaining_units <= 0:
            break

        units_in_slab = min(remaining_units, slab["limit"])
        slab_cost = units_in_slab * slab["rate"]
        energy_charge += slab_cost
        slab_breakdown.append(
            {
                "label": slab["label"],
                "units": units_in_slab,
                "rate": slab["rate"],
                "cost": round(slab_cost, 2),
            }
        )
        remaining_units -= units_in_slab

    fppas_charge = round(units * fppas, 2)
    subtotal = round(fixed_charge + energy_charge + fppas_charge, 2)
    electricity_duty = round(subtotal * duty_pct, 2)
    total_bill = round(subtotal + electricity_duty, 2)

    return {
        "fixed_charge": fixed_charge,
        "energy_charge": round(energy_charge, 2),
        "fppas_charge": fppas_charge,
        "electricity_duty": electricity_duty,
        "total_bill": total_bill,
        "effective_rate": round(total_bill / units, 2) if units > 0 else 0,
        "slab_breakdown": slab_breakdown,
    }


def calculate_subsidy(system_kw):
    if system_kw >= 3:
        return 78000
    if system_kw >= 2:
        return 60000
    if system_kw >= 1:
        return 30000
    return 0


def solar_analysis(units, state, category, system_kw=3, system_type="on_grid"):
    solar = tariffs[state]["solar"]
    avg_sun_hours = solar["avg_sun_hours"]
    monthly_generation = system_kw * avg_sun_hours * 30

    cost_per_kw = solar["cost_per_kw"]
    gross_cost = system_kw * cost_per_kw

    # PM Surya Ghar Muft Bijli Yojana subsidy is only available for
    # grid-connected rooftop systems. Hybrid and off-grid systems are
    # not eligible under this scheme. Subsidy is capped at 3 kW.
    if system_type == "on_grid":
        subsidy = calculate_subsidy(system_kw)
        subsidy_message = "Government subsidy applied for on-grid rooftop solar."
    else:
        subsidy = 0
        subsidy_message = f"Subsidy not applicable for {system_type} systems."

    net_cost = round(gross_cost - subsidy, 2)

    self_consumed = min(units, monthly_generation)
    surplus_units = max(0, monthly_generation - units)
    export_income = round(surplus_units * solar["export_rate"], 2)

    bill_without_solar = calculate_bill(units, state, category)["total_bill"]
    bill_with_solar = calculate_bill(
        max(0, units - int(self_consumed)), state, category
    )["total_bill"]

    monthly_savings = round(bill_without_solar - bill_with_solar + export_income, 2)
    annual_savings = round(monthly_savings * 12, 2)
    payback_years = round(net_cost / annual_savings, 1) if annual_savings > 0 else 99
    lifetime_savings = round(
        annual_savings * solar["panel_life_years"] - net_cost, 2
    )

    return {
        "system_kw": system_kw,
        "monthly_generation_units": round(monthly_generation, 1),
        "gross_cost": gross_cost,
        "subsidy": round(subsidy, 2),
        "net_cost": net_cost,
        "monthly_savings": monthly_savings,
        "annual_savings": annual_savings,
        "payback_years": payback_years,
        "lifetime_savings": lifetime_savings,
        "export_income": export_income,
        "export_rate": solar["export_rate"],
        "co2_saved_kg_monthly": round(monthly_generation * 0.82, 2),
        "net_metering": solar["net_metering"],
        "avg_sun_hours": avg_sun_hours,
        "recommendation": "on-grid" if solar["net_metering"] else "hybrid",
        "system_type": system_type,
        "message": subsidy_message,
    }


@app.route("/")
def index():
    return app.send_static_file("index.html")


@app.route("/states", methods=["GET"])
def get_states():
    result = {}
    for state, data in tariffs.items():
        result[state] = {
            "utility": data["utility"],
            "regulator": data["regulator"],
            "effective_date": data["effective_date"],
            "categories": list(data["categories"].keys()),
            "green_power_surcharge": data["green_power_surcharge"],
        }
    return jsonify(result)


@app.route("/calculate", methods=["POST"])
def calculate():
    data = request.get_json(silent=True) or {}
    units = int(data.get("units", 0))
    state = data.get("state", "Gujarat")
    system_kw = float(data.get("system_kw", 3))
    system_type = data.get("system_type", "on_grid")

    if units <= 0:
        return jsonify({"error": "Units must be positive"}), 400
    if state not in tariffs:
        return jsonify({"error": "State not found"}), 404
    if system_type not in {"on_grid", "hybrid", "off_grid"}:
        return jsonify({"error": "Invalid system_type"}), 400

    default_category = next(iter(tariffs[state]["categories"]))
    category = data.get("category", default_category)
    if category not in tariffs[state]["categories"]:
        return jsonify({"error": "Category not found"}), 404

    bill = calculate_bill(units, state, category)
    solar = solar_analysis(units, state, category, system_kw, system_type)
    green_power_surcharge = round(units * tariffs[state]["green_power_surcharge"], 2)
    co2_kg = round(units * 0.82, 2)

    return jsonify(
        {
            "state": state,
            "category": category,
            "units": units,
            "system_type": system_type,
            "bill": bill,
            "solar": solar,
            "green_power": {
                "surcharge": green_power_surcharge,
                "total_with_green": round(
                    bill["total_bill"] + green_power_surcharge, 2
                ),
                "description": (
                    "Pay extra to source electricity from renewable energy."
                ),
            },
            "environment": {
                "co2_kg": co2_kg,
                "trees_equivalent": round(co2_kg / 21.7, 1),
            },
            "utility_info": {
                "name": tariffs[state]["utility"],
                "regulator": tariffs[state]["regulator"],
                "effective_date": tariffs[state]["effective_date"],
            },
        }
    )


@app.route("/compare", methods=["POST"])
def compare():
    data = request.get_json(silent=True) or {}
    units = int(data.get("units", 0))
    states = data.get("states", list(tariffs.keys()))

    if units <= 0:
        return jsonify({"error": "Units must be positive"}), 400

    comparison = []
    for state in states:
        if state not in tariffs:
            continue

        category = next(iter(tariffs[state]["categories"]))
        bill = calculate_bill(units, state, category)
        solar = solar_analysis(units, state, category, 3)
        comparison.append(
            {
                "state": state,
                "utility": tariffs[state]["utility"],
                "category": category,
                "total_bill": bill["total_bill"],
                "effective_rate": bill["effective_rate"],
                "solar_payback_years": solar["payback_years"],
                "solar_net_cost": solar["net_cost"],
                "monthly_solar_savings": solar["monthly_savings"],
            }
        )

    comparison.sort(key=lambda item: item["total_bill"])
    return jsonify({"units": units, "comparison": comparison})


@app.route("/tariff-info/<state>", methods=["GET"])
def tariff_info(state):
    if state not in tariffs:
        return jsonify({"error": "State not found"}), 404
    return jsonify(tariffs[state])


if __name__ == "__main__":
    app.run(debug=True, port=5000)
