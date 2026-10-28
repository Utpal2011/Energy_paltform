"""Tunable assumptions used by the VoltIQ calculations.

Tariff data lives in tariffs.json; values here are modelling assumptions
that apply to every state.
"""

# Environment
CO2_KG_PER_KWH = 0.82  # Indian grid emission factor (CEA baseline)
CO2_KG_PER_TREE = 21.7  # CO2 absorbed by one mature tree per year

# Solar generation
DAYS_PER_MONTH = 30

# /compare uses one fixed system size for every state
COMPARE_SYSTEM_KW = 3

# Payback reported when savings never recover the system cost
NO_PAYBACK_YEARS = 99

# Request limits
MAX_UNITS = 100000  # kWh per month
MAX_COMPARE_STATES = 50
MAX_REQUEST_BYTES = 16 * 1024

# PM Surya Ghar Muft Bijli Yojana: fixed amount by system size (kW, rupees),
# largest band first. Battery cost is never subsidised.
SUBSIDY_BANDS = [(3, 78000), (2, 60000), (1, 30000)]
SUBSIDY_ELIGIBLE_TYPES = {"on_grid", "hybrid"}
SUBSIDY_CATEGORY_KEYWORD = "residential"

# Surplus can be sold to the grid only by grid-tied systems, and only
# where the state allows net metering.
EXPORT_ELIGIBLE_TYPES = {"on_grid", "hybrid"}

# Installed cost relative to an on-grid system of the same size. Hybrid and
# off-grid include batteries; these multipliers are estimates, not quotes.
COST_MULTIPLIER = {"on_grid": 1.0, "hybrid": 1.5, "off_grid": 1.8}
