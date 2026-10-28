# Solar Accuracy Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make VoltIQ's solar ROI numbers defensible: correct subsidy eligibility, export rules, system-type costs, losses/degradation, configurable constants, validated inputs, and a relative API base.

**Architecture:** All calculation stays in `Backend/app.py`; tunable assumptions move to a new `Backend/config.py`; `tariffs.json` is unchanged. Tests use Flask's test client in `Backend/tests/`.

**Tech Stack:** Python 3, Flask, flask-cors, pytest; vanilla JS frontend.

**Spec:** The approved chat plan of 2026-10-28 plus the user's final answers (below). No separate spec file.

## Global Constraints

- Subsidy = real PM Surya Ghar fixed bands: ≥1 kW → ₹30,000; ≥2 kW → ₹60,000; ≥3 kW → ₹78,000.
- Subsidy only for residential categories (0 for commercial/agricultural) and only for system types in `config.SUBSIDY_ELIGIBLE_TYPES = {"on_grid", "hybrid"}`.
- Battery is never subsidised: the subsidy never exceeds the panel-only cost (`kW × cost_per_kw`).
- `subsidy_max_kw` caps the kW used for the band; `max_capacity_kw` caps the accepted `system_kw`.
- `COST_MULTIPLIER = {"on_grid": 1.0, "hybrid": 1.5, "off_grid": 1.8}`, labelled as estimates in the results.
- Export income only for on_grid and hybrid, and only when `net_metering` is true.
- `PERFORMANCE_RATIO = 0.80`, `ANNUAL_DEGRADATION = 0.005`.
- Existing response field names keep their meaning (the frontend reads them).

## Review Focus

- Non-numeric / NaN / infinite `units` or `system_kw` → 400, never 500.
- `system_kw` between 0 and 1 → valid system, subsidy 0.
- Category names: "Residential (BPL)" etc. must count as residential; "Commercial"/"Agricultural" must not.
- Off-grid with surplus generation → no export income, surplus wasted.
- Payback never reached inside panel life → 99.

---

### Task 0: Test harness + baseline
- Create `Backend/tests/conftest.py` (adds Backend to sys.path, `client` fixture) and `Backend/tests/test_app.py` with bill tests for Gujarat 200 units RGP (hand-verified slab math) and solar baseline values.
- Run: `python -m pytest Backend/tests -q` → all pass. Commit.

### Task 1: `Backend/config.py` (no behaviour change)
- Constants: `CO2_KG_PER_KWH = 0.82`, `CO2_KG_PER_TREE = 21.7`, `DAYS_PER_MONTH = 30`, `COMPARE_SYSTEM_KW = 3`, `NO_PAYBACK_YEARS = 99`.
- `app.py` imports them. Test asserts environment numbers derive from config. Baseline still green. Commit.

### Task 2: Input limits
- `config.MAX_UNITS = 100000`, `MAX_COMPARE_STATES = 50`, `MAX_REQUEST_BYTES = 16 * 1024`.
- `parse_positive_number(value, name, integer=False) -> (number | None, error | None)`; `system_kw` must be finite, > 0, ≤ state `max_capacity_kw`.
- Tests: `units="abc"` → 400; `units=-5` → 400; `units=100001` → 400; `system_kw="nan"`/`"inf"` → 400; `system_kw=1500` Gujarat → 400; `states` not a list or > 50 → 400. Commit.

### Task 3: Subsidy rules
- `calculate_subsidy(system_kw, category, system_type, solar) -> int` with the bands, residential check (`"residential" in category.lower()`), eligible types, `subsidy_max_kw` cap, and panel-only cap.
- Tests: on_grid 3 kW residential → 78000; 2.5 kW → 60000; 0.5 kW → 0; hybrid → same as on_grid; off_grid → 0; commercial/agricultural → 0; `subsidy_max_kw=2` → 60000 at 3 kW. Commit.

### Task 4: Export rules
- `export_allowed = net_metering and system_type in config.EXPORT_ELIGIBLE_TYPES` (`{"on_grid", "hybrid"}`); response field `export_allowed`.
- Tests: off_grid surplus → 0; `net_metering=False` → 0; on_grid surplus → > 0. Commit.

### Task 5: System-type cost
- `gross_cost = system_kw × cost_per_kw × COST_MULTIPLIER[type]`; response adds `cost_is_estimate` (true for hybrid/off_grid) and `cost_note`.
- Tests: Gujarat 3 kW hybrid gross 247500, off_grid 297000, on_grid 165000. Commit.

### Task 6: Losses + degradation
- Year-1 monthly generation = `kW × sun_hours × DAYS_PER_MONTH × PERFORMANCE_RATIO`.
- Loop years 1..panel_life: generation × `(1 − ANNUAL_DEGRADATION)^(year−1)`; annual savings per year; lifetime = sum − net cost; payback = first year cumulative ≥ net cost (fractional within that year), else `NO_PAYBACK_YEARS`.
- Response adds `performance_ratio`, `annual_degradation`.
- Tests: Gujarat 3 kW generation 396.0; lifetime savings < 25 × year-1 annual − net cost; payback-never case → 99. Commit.

### Task 7: Relative API + frontend + docs
- `script.js`: `const API = "";`; show export-not-available and cost-estimate notes; subsidy warning shown only for off_grid.
- `index.html`: subsidy warning text updated.
- `README.md`, `start.sh`, `CLAUDE.md`: single server on port 5000.
- Verify: start server, `curl /`, `/states`, `/calculate`. Commit.
