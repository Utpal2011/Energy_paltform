# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

VoltIQ: a small web app for comparing Indian state electricity tariffs, computing slab-wise bills, and estimating rooftop solar ROI. Flask JSON API (`Backend/`) + static vanilla HTML/CSS/JS frontend (`Frontend/`). No build step, no package manifest, no test suite, no linter config.

## Running

```bash
pip install flask flask-cors

# Backend (http://127.0.0.1:5000, debug mode)
cd Backend && python app.py

# Frontend (separate terminal; http://127.0.0.1:8080)
cd Frontend && python -m http.server 8080
```

`start.sh` runs both (bash only; on Windows use Git Bash or run the two commands manually).

Quick API check:

```bash
curl -X POST http://127.0.0.1:5000/calculate -H "Content-Type: application/json" \
  -d '{"units":200,"state":"Gujarat","category":"Residential (RGP)","system_kw":3,"system_type":"on_grid"}'
```

## Architecture

**Data is the source of truth.** `Backend/tariffs.json` is loaded once at import time into the module-level `tariffs` dict (restart the server after editing it). Shape per state: `utility`, `regulator`, `effective_date`, `green_power_surcharge`, `categories` (name → `fixed_charge`, `slabs[{limit, rate, label}]`, `fppas`, `electricity_duty_pct`), and `solar` (`net_metering`, `export_rate`, `avg_sun_hours`, `cost_per_kw`, `panel_life_years`, …). Slab `limit` is the width of that slab (units in it), not a cumulative upper bound; the final slab uses `9999` as "unbounded".

**Calculation pipeline in `Backend/app.py`:**
- `calculate_bill` — walks slabs consuming units, then adds FPPAS (per unit) and fixed charge to get a subtotal; electricity duty is a percentage of that subtotal.
- `solar_analysis` — generation = `kW × sun_hours × 30`; savings = bill difference with self-consumed units removed (calls `calculate_bill` twice) + surplus export income. Subsidy comes from `calculate_subsidy` (hardcoded PM Surya Ghar tiers: ₹30k/60k/78k for ≥1/≥2/≥3 kW) and applies **only** to `system_type == "on_grid"`. Note: `solar.subsidy_pct` / `subsidy_max_kw` in the JSON are not used by the code.
- CO₂ factor `0.82 kg/kWh` and `21.7 kg/tree` are hardcoded constants.

**Endpoints:** `GET /states`, `POST /calculate` (bill + solar + green power + environment in one response), `POST /compare` (uses each state's *first* category and a fixed 3 kW on-grid system, sorted by total bill), `GET /tariff-info/<state>`. A category's "default" is dict insertion order from the JSON, so category order in `tariffs.json` matters.

**Frontend (`Frontend/script.js`):**
- API base is hardcoded: `const API = "http://127.0.0.1:5000"` (CORS is enabled on the backend for this).
- Tabs (`calculator`, `compare`, `solar`, `discover`) are `<section id="tab-*">` toggled by `showTab()`; handlers are wired via inline `onclick`/`onchange` attributes in `index.html`.
- Results are rendered by building HTML strings into element IDs (`res-*`, `bill-breakdown`, `solar-snapshot`, `solar-full`, `compare-results`), so renamed response fields must be updated in both `app.py` and `script.js`.
- Visibility is toggled with the `.hidden` CSS class.

**Adding/renaming a state or category requires touching three places:** `Backend/tariffs.json`, the hardcoded `<option>`s in the `#state` select in `Frontend/index.html`, and the offline fallback `statesData` in `loadStates()` in `Frontend/script.js`.
