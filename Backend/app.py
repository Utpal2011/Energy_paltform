from flask import Flask, jsonify, request
from flask_cors import CORS
import json
import math
from pathlib import Path

import config

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR.parent / "Frontend"

# Serve the Frontend folder from the site root, so the whole app runs on one port.
app = Flask(__name__, static_folder=str(FRONTEND_DIR), static_url_path="")
app.config["MAX_CONTENT_LENGTH"] = config.MAX_REQUEST_BYTES
CORS(app)

with open(BASE_DIR / "tariffs.json", encoding="utf-8") as f:
    tariffs = json.load(f)


def parse_number(value, name, integer=False, maximum=None):
    """Return (number, None) for a finite positive number, else (None, error)."""
    if isinstance(value, bool):
        return None, f"{name} must be a number"
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None, f"{name} must be a number"
    if not math.isfinite(number) or number <= 0:
        return None, f"{name} must be a positive number"
    if integer and not number.is_integer():
        return None, f"{name} must be a whole number"
    if maximum is not None and number > maximum:
        return None, f"{name} must be at most {maximum}"
    return (int(number) if integer else number), None


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


def is_subsidy_category(category):
    return config.SUBSIDY_CATEGORY_KEYWORD in category.lower()


def calculate_subsidy(system_kw, category, system_type, solar):
    if system_type not in config.SUBSIDY_ELIGIBLE_TYPES:
        return 0
    if not is_subsidy_category(category):
        return 0

    eligible_kw = min(system_kw, solar["subsidy_max_kw"])
    band_amount = next(
        (amount for min_kw, amount in config.SUBSIDY_BANDS if eligible_kw >= min_kw),
        0,
    )
    # Only the panels are subsidised, never the battery.
    panel_cost = system_kw * solar["cost_per_kw"]
    return min(band_amount, panel_cost)


def monthly_solar_savings(generation, units, state, category, export_rate):
    """Bill reduction plus export income for one month of generation.

    export_rate is 0 when the system cannot export.
    """
    self_consumed = min(units, generation)
    surplus_units = max(0, generation - units)
    bill_without_solar = calculate_bill(units, state, category)["total_bill"]
    bill_with_solar = calculate_bill(
        max(0, units - int(self_consumed)), state, category
    )["total_bill"]
    export_income = surplus_units * export_rate
    return bill_without_solar - bill_with_solar + export_income, export_income


def solar_analysis(units, state, category, system_kw=3, system_type="on_grid"):
    solar = tariffs[state]["solar"]
    avg_sun_hours = solar["avg_sun_hours"]
    monthly_generation = (
        system_kw * avg_sun_hours * config.DAYS_PER_MONTH * config.PERFORMANCE_RATIO
    )

    cost_per_kw = solar["cost_per_kw"]
    cost_multiplier = config.COST_MULTIPLIER[system_type]
    gross_cost = round(system_kw * cost_per_kw * cost_multiplier, 2)
    cost_is_estimate = cost_multiplier != 1.0
    if cost_is_estimate:
        cost_note = (
            f"Estimate: {system_type} cost includes a battery, "
            f"taken as {cost_multiplier}x the on-grid cost."
        )
    else:
        cost_note = "Based on the state's average installed cost per kW."

    subsidy = calculate_subsidy(system_kw, category, system_type, solar)
    if system_type not in config.SUBSIDY_ELIGIBLE_TYPES:
        subsidy_message = f"Subsidy not applicable for {system_type} systems."
    elif not is_subsidy_category(category):
        subsidy_message = "Subsidy applies only to residential connections."
    elif subsidy == 0:
        subsidy_message = "Subsidy requires a system of at least 1 kW."
    else:
        subsidy_message = "PM Surya Ghar subsidy applied (panels only, not battery)."

    net_cost = round(gross_cost - subsidy, 2)

    export_allowed = (
        solar["net_metering"] and system_type in config.EXPORT_ELIGIBLE_TYPES
    )
    export_rate = solar["export_rate"] if export_allowed else 0

    first_month_savings, export_income = monthly_solar_savings(
        monthly_generation, units, state, category, export_rate
    )
    monthly_savings = round(first_month_savings, 2)
    export_income = round(export_income, 2)
    annual_savings = round(monthly_savings * 12, 2)

    # Walk the panel life year by year as output degrades.
    total_savings = 0
    payback_years = None
    for year in range(1, solar["panel_life_years"] + 1):
        generation = monthly_generation * (1 - config.ANNUAL_DEGRADATION) ** (year - 1)
        year_savings = (
            monthly_solar_savings(generation, units, state, category, export_rate)[0]
            * 12
        )
        if payback_years is None and year_savings > 0:
            if total_savings + year_savings >= net_cost:
                fraction = (net_cost - total_savings) / year_savings
                payback_years = round(year - 1 + max(0, fraction), 1)
        total_savings += year_savings

    payback_reached = payback_years is not None
    if not payback_reached:
        payback_years = config.NO_PAYBACK_YEARS
    lifetime_savings = round(total_savings - net_cost, 2)

    return {
        "system_kw": system_kw,
        "monthly_generation_units": round(monthly_generation, 1),
        "gross_cost": gross_cost,
        "cost_is_estimate": cost_is_estimate,
        "cost_note": cost_note,
        "subsidy": round(subsidy, 2),
        "net_cost": net_cost,
        "monthly_savings": monthly_savings,
        "annual_savings": annual_savings,
        "payback_years": payback_years,
        "payback_reached": payback_reached,
        "lifetime_savings": lifetime_savings,
        "export_income": export_income,
        "export_allowed": export_allowed,
        "export_rate": solar["export_rate"],
        "performance_ratio": config.PERFORMANCE_RATIO,
        "annual_degradation": config.ANNUAL_DEGRADATION,
        "co2_saved_kg_monthly": round(monthly_generation * config.CO2_KG_PER_KWH, 2),
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
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Request body must be a JSON object"}), 400

    units, error = parse_number(
        data.get("units"), "units", integer=True, maximum=config.MAX_UNITS
    )
    if error:
        return jsonify({"error": error}), 400

    state = data.get("state", "Gujarat")
    if not isinstance(state, str) or state not in tariffs:
        return jsonify({"error": "State not found"}), 404

    system_type = data.get("system_type", "on_grid")
    if not isinstance(system_type, str) or system_type not in {
        "on_grid",
        "hybrid",
        "off_grid",
    }:
        return jsonify({"error": "Invalid system_type"}), 400

    system_kw, error = parse_number(
        data.get("system_kw", 3),
        "system_kw",
        maximum=tariffs[state]["solar"]["max_capacity_kw"],
    )
    if error:
        return jsonify({"error": error}), 400

    default_category = next(iter(tariffs[state]["categories"]))
    category = data.get("category", default_category)
    if not isinstance(category, str) or category not in tariffs[state]["categories"]:
        return jsonify({"error": "Category not found"}), 404

    bill = calculate_bill(units, state, category)
    solar = solar_analysis(units, state, category, system_kw, system_type)
    green_power_surcharge = round(units * tariffs[state]["green_power_surcharge"], 2)
    co2_kg = round(units * config.CO2_KG_PER_KWH, 2)

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
                "trees_equivalent": round(co2_kg / config.CO2_KG_PER_TREE, 1),
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
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Request body must be a JSON object"}), 400

    units, error = parse_number(
        data.get("units"), "units", integer=True, maximum=config.MAX_UNITS
    )
    if error:
        return jsonify({"error": error}), 400

    states = data.get("states", list(tariffs.keys()))
    if (
        not isinstance(states, list)
        or len(states) > config.MAX_COMPARE_STATES
        or not all(isinstance(state, str) for state in states)
    ):
        return jsonify(
            {
                "error": (
                    "states must be a list of at most "
                    f"{config.MAX_COMPARE_STATES} state names"
                )
            }
        ), 400

    comparison = []
    for state in states:
        if state not in tariffs:
            continue

        category = next(iter(tariffs[state]["categories"]))
        bill = calculate_bill(units, state, category)
        solar = solar_analysis(units, state, category, config.COMPARE_SYSTEM_KW)
        comparison.append(
            {
                "state": state,
                "utility": tariffs[state]["utility"],
                "category": category,
                "total_bill": bill["total_bill"],
                "effective_rate": bill["effective_rate"],
                "solar_payback_years": solar["payback_years"],
                "solar_payback_reached": solar["payback_reached"],
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
