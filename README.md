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
|   `-- tariffs.json
|-- Frontend/
|   |-- index.html
|   |-- script.js
|   `-- style.css
`-- start.sh
```

## Run Locally

1. Create and activate a Python virtual environment if needed.
2. Install dependencies:

```bash
pip install flask flask-cors
```

3. Start the backend:

```bash
cd Backend
python app.py
```

4. Serve the frontend from another terminal:

```bash
cd Frontend
python -m http.server 8080
```

5. Open:

```text
http://127.0.0.1:8080
```

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
  "system_kw": 3
}
```
