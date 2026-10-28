# VoltIQ - Open Energy Discovery Platform

VoltIQ is a web app for comparing electricity tariffs, estimating slab-wise bills, and exploring solar economics across Indian states.

## Features

- Slab-wise electricity bill calculation with fixed charges, FPPAS, and duty
- State comparison for the same monthly consumption
- Solar ROI analysis with subsidy, payback, and lifetime savings
- REST APIs for states, bill calculation, comparison, and tariff info

## Project Structure

```text
Energy-platform/
|-- Backend/
|   |-- app.py
|   |-- config.py
|   |-- tariffs.json
|   `-- tests/
|-- Frontend/
|   |-- index.html
|   |-- script.js
|   `-- style.css
`-- start.sh
```

## Run Locally

1. Create and activate a Python virtual environment if needed.
2. Install dependencies (from the repo root):

```bash
pip install -r requirements.txt
```

3. Start the server (it serves both the API and the frontend):

```bash
python Backend/app.py
```

4. Open:

```text
http://127.0.0.1:5000
```

## Tests

```bash
python -m pytest Backend/tests -q
```

## Model Assumptions

Tunable assumptions live in `Backend/config.py`: CO2 factors, the 0.80
performance ratio, 0.5%/year panel degradation, PM Surya Ghar subsidy bands
(residential on-grid/hybrid only, panels only), hybrid/off-grid cost
multipliers (estimates), and request limits.

## API Endpoints

- `GET /states`
- `POST /calculate`
- `POST /compare`
- `GET /tariff-info/<state>`

## Sample Request

```json
POST /calculate
{
  "units": 200,
  "state": "Gujarat",
  "category": "Residential (RGP)",
  "system_kw": 3,
  "system_type": "on_grid"
}
```
