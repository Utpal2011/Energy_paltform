# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

VoltIQ: a small web app for comparing Indian state electricity tariffs, computing slab-wise bills, and estimating rooftop solar ROI. Flask JSON API (`Backend/`) + static vanilla HTML/CSS/JS frontend (`Frontend/`), both served by Flask on one port. No build step, no package manifest, no linter config. Tests: pytest in `Backend/tests/`.

## Running

```bash
# From the repo root
pip install -r requirements.txt

# API + frontend: open http://127.0.0.1:5000 (debug mode)
python Backend/app.py

# Tests
python -m pytest Backend/tests -q
```

`start.sh` does the same (bash only). The frontend calls the API with a relative base, so it only works when served by Flask, not by `python -m http.server`.

Quick API check:

```bash
curl -X POST http://127.0.0.1:5000/calculate -H "Content-Type: application/json" \
  -d '{"units":200,"state":"Gujarat","category":"Residential (RGP)","system_kw":3,"system_type":"on_grid"}'
```

## Architecture

**Data is the source of truth.** `Backend/tariffs.json` is loaded once at import time into the module-level `tariffs` dict (restart the server after editing it). Shape per state: `utility`, `regulator`, `effective_date`, `green_power_surcharge`, `categories` (name → `fixed_charge`, `slabs[{limit, rate, label}]`, `fppas`, `electricity_duty_pct`), and `solar` (`net_metering`, `export_rate`, `avg_sun_hours`, `cost_per_kw`, `panel_life_years`, …). Slab `limit` is the width of that slab (units in it), not a cumulative upper bound; the final slab uses `9999` as "unbounded".

**Calculation pipeline in `Backend/app.py`:**
- `calculate_bill` — walks slabs consuming units, then adds FPPAS (per unit) and fixed charge to get a subtotal; electricity duty is a percentage of that subtotal.
- `solar_analysis` — year-1 generation = `kW × sun_hours × DAYS_PER_MONTH × PERFORMANCE_RATIO`; `monthly_solar_savings` = bill difference with self-consumed units removed + surplus export income. Lifetime savings and payback walk each year of `panel_life_years` with `ANNUAL_DEGRADATION`. `monthly_savings`/`annual_savings` in the response are year-1 values.
- Gross cost = `kW × cost_per_kw × COST_MULTIPLIER[system_type]` (hybrid/off-grid multipliers are estimates; response sets `cost_is_estimate`).
- `calculate_subsidy` — PM Surya Ghar bands from `SUBSIDY_BANDS`, only for categories whose name contains "residential" and types in `SUBSIDY_ELIGIBLE_TYPES` (on_grid, hybrid). `subsidy_max_kw` caps the band; the subsidy never exceeds the panel-only cost (battery never subsidised). `solar.subsidy_pct` is unused.
- Export income only when `net_metering` is true and the type is in `EXPORT_ELIGIBLE_TYPES` (response field `export_allowed`).
- All modelling constants and request limits live in `Backend/config.py`. `parse_number` validates inputs; `system_kw` is capped by the state's `max_capacity_kw`, `units` by `MAX_UNITS`.

**Endpoints:** `GET /states`, `POST /calculate` (bill + solar + green power + environment in one response), `POST /compare` (uses each state's *first* category and a fixed 3 kW on-grid system, sorted by total bill), `GET /tariff-info/<state>`. A category's "default" is dict insertion order from the JSON, so category order in `tariffs.json` matters.

**Frontend (`Frontend/script.js`):**
- API base is relative: `const API = ""` (same origin as the page; CORS stays enabled for other clients).
- Tabs (`calculator`, `compare`, `solar`, `discover`) are `<section id="tab-*">` toggled by `showTab()`; handlers are wired via inline `onclick`/`onchange` attributes in `index.html`.
- Results are rendered by building HTML strings into element IDs (`res-*`, `bill-breakdown`, `solar-snapshot`, `solar-full`, `compare-results`), so renamed response fields must be updated in both `app.py` and `script.js`.
- Visibility is toggled with the `.hidden` CSS class.

**Adding/renaming a state or category requires touching three places:** `Backend/tariffs.json`, the hardcoded `<option>`s in the `#state` select in `Frontend/index.html`, and the offline fallback `statesData` in `loadStates()` in `Frontend/script.js`.
