// Same origin: Flask serves both the page and the API.
const API = "";

let statesData = {};
let lastResult = null;

window.addEventListener("DOMContentLoaded", async () => {
    await loadStates();
    updateCategories();
    updateSubsidyWarning();
});

async function loadStates() {
    try {
        const response = await fetch(`${API}/states`);
        if (!response.ok) {
            throw new Error("Unable to load states.");
        }
        statesData = await response.json();
    } catch (error) {
        statesData = {
            Gujarat: { categories: ["Residential (RGP)", "Commercial (Non-RGP)", "Agricultural (AGP)"] },
            Maharashtra: { categories: ["Residential (BPL)", "Residential", "Commercial (LT-II)"] },
            "Uttar Pradesh": { categories: ["Residential (LMV-1)", "Commercial (LMV-2)", "Agricultural (LMV-6)"] },
            Rajasthan: { categories: ["Residential", "Commercial"] },
            Delhi: { categories: ["Residential (LCA-1)", "Commercial (LCA-2)"] }
        };
    }
}

function showTab(name) {
    document.querySelectorAll(".tab").forEach((tab) => tab.classList.remove("active"));
    document.querySelectorAll(".nav-btn").forEach((button) => {
        button.classList.toggle("active", button.dataset.tab === name);
    });

    const activeTab = document.getElementById(`tab-${name}`);
    if (activeTab) {
        activeTab.classList.add("active");
    }
}

function updateCategories() {
    const state = document.getElementById("state").value;
    const categoryElement = document.getElementById("category");
    const categories = statesData[state]?.categories || [];

    categoryElement.innerHTML = "";
    categories.forEach((category) => {
        const option = document.createElement("option");
        option.value = category;
        option.textContent = category;
        categoryElement.appendChild(option);
    });
}

function updateSubsidyWarning() {
    const systemType = document.getElementById("system_type").value;
    const warningElement = document.getElementById("subsidy-warning");
    const showWarning = systemType === "off_grid";
    warningElement.classList.toggle("hidden", !showWarning);
}

async function calculate() {
    const units = parseInt(document.getElementById("units").value, 10);
    const state = document.getElementById("state").value;
    const category = document.getElementById("category").value;
    const systemKw = parseFloat(document.getElementById("system_kw").value) || 3;
    const systemType = document.getElementById("system_type").value;
    const errorElement = document.getElementById("error-msg");
    const button = document.getElementById("calculate-btn");

    errorElement.classList.add("hidden");

    if (!units || units < 1) {
        errorElement.textContent = "Please enter a valid number of units.";
        errorElement.classList.remove("hidden");
        return;
    }

    button.disabled = true;
    button.textContent = "Calculating...";

    try {
        const response = await fetch(`${API}/calculate`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                units,
                state,
                category,
                system_kw: systemKw,
                system_type: systemType
            })
        });

        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || "Calculation failed.");
        }

        lastResult = data;
        renderBillResult(data);
        renderSolarFull(data);
        document.getElementById("results-panel").classList.remove("hidden");
    } catch (error) {
        errorElement.textContent = error.message || "Could not connect to backend.";
        errorElement.classList.remove("hidden");
    } finally {
        button.disabled = false;
        button.textContent = "Calculate Bill";
    }
}

function formatPayback(years, reached) {
    return reached ? `${years} yrs` : "Not within panel life";
}

function renderBillResult(data) {
    const bill = data.bill;
    const solar = data.solar;

    document.getElementById("res-total").textContent = `Rs ${bill.total_bill.toLocaleString("en-IN")}`;
    document.getElementById("res-system-type").textContent = data.system_type.replace("_", "-");
    document.getElementById("res-utility").textContent = `DISCOM: ${data.utility_info.name} | ${data.category}`;
    document.getElementById("res-solar").textContent = `Rs ${solar.net_cost.toLocaleString("en-IN")}`;
    document.getElementById("res-savings").textContent = `Rs ${solar.monthly_savings.toLocaleString("en-IN")}`;
    document.getElementById("res-subsidy").textContent = `Rs ${solar.subsidy.toLocaleString("en-IN")}`;
    document.getElementById("res-co2").textContent = `${data.environment.co2_kg} kg`;
    document.getElementById("res-solar-message").textContent = solar.message;

    document.getElementById("bill-breakdown").innerHTML = `
        <div class="bd-item"><span class="bd-label">Fixed Charge</span><span class="bd-val">Rs ${bill.fixed_charge}</span></div>
        <div class="bd-item"><span class="bd-label">Energy Charge</span><span class="bd-val">Rs ${bill.energy_charge}</span></div>
        <div class="bd-item"><span class="bd-label">FPPAS</span><span class="bd-val">Rs ${bill.fppas_charge}</span></div>
        <div class="bd-item"><span class="bd-label">Electricity Duty</span><span class="bd-val">Rs ${bill.electricity_duty}</span></div>
    `;

    document.getElementById("solar-snapshot").innerHTML = `
        <div class="solar-item">
            <span class="solar-item-label">Payback Period</span>
            <span class="solar-item-val">${formatPayback(solar.payback_years, solar.payback_reached)}</span>
            <span class="solar-item-sub">Based on annual savings</span>
        </div>
        <div class="solar-item">
            <span class="solar-item-label">Monthly Generation</span>
            <span class="solar-item-val">${solar.monthly_generation_units} units</span>
            <span class="solar-item-sub">Estimated rooftop output</span>
        </div>
        <div class="solar-item">
            <span class="solar-item-label">Export Income</span>
            <span class="solar-item-val">${solar.export_allowed ? `Rs ${solar.export_income.toLocaleString("en-IN")}` : "Not available"}</span>
            <span class="solar-item-sub">${solar.export_allowed ? "Monthly export potential" : "Needs net metering and a grid-tied system"}</span>
        </div>
        <div class="solar-item">
            <span class="solar-item-label">Trees Equivalent</span>
            <span class="solar-item-val">${data.environment.trees_equivalent}</span>
            <span class="solar-item-sub">Carbon offset benchmark</span>
        </div>
    `;
}

function renderSolarFull(data) {
    const solar = data.solar;
    const element = document.getElementById("solar-full");

    element.innerHTML = `
        <div class="card">
            <div class="panel-title">Installation Economics</div>
            <div class="bill-breakdown">
                <div class="bd-item"><span class="bd-label">Gross Cost${solar.cost_is_estimate ? " (estimate)" : ""}</span><span class="bd-val">Rs ${solar.gross_cost.toLocaleString("en-IN")}</span></div>
                <div class="bd-item"><span class="bd-label">Subsidy</span><span class="bd-val">Rs ${solar.subsidy.toLocaleString("en-IN")}</span></div>
                <div class="bd-item"><span class="bd-label">Net Cost</span><span class="bd-val">Rs ${solar.net_cost.toLocaleString("en-IN")}</span></div>
                <div class="bd-item"><span class="bd-label">Recommendation</span><span class="bd-val">${solar.recommendation}</span></div>
            </div>
            <p class="solar-item-sub">${solar.cost_note}</p>
        </div>
        <div class="card">
            <div class="panel-title">Long-Term Returns</div>
            <div class="bill-breakdown">
                <div class="bd-item"><span class="bd-label">Monthly Savings</span><span class="bd-val">Rs ${solar.monthly_savings.toLocaleString("en-IN")}</span></div>
                <div class="bd-item"><span class="bd-label">Annual Savings</span><span class="bd-val">Rs ${solar.annual_savings.toLocaleString("en-IN")}</span></div>
                <div class="bd-item"><span class="bd-label">Payback</span><span class="bd-val">${formatPayback(solar.payback_years, solar.payback_reached)}</span></div>
                <div class="bd-item"><span class="bd-label">Lifetime Savings</span><span class="bd-val">Rs ${solar.lifetime_savings.toLocaleString("en-IN")}</span></div>
            </div>
            <p class="solar-item-sub">Includes ${Math.round((1 - solar.performance_ratio) * 100)}% system losses and ${solar.annual_degradation * 100}% panel degradation per year.</p>
        </div>
    `;

    element.classList.remove("hidden");
}

async function compareStates() {
    const units = parseInt(document.getElementById("compare-units").value, 10) || 200;
    const resultsElement = document.getElementById("compare-results");

    resultsElement.innerHTML = "";
    resultsElement.classList.remove("hidden");

    try {
        const response = await fetch(`${API}/compare`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ units, states: Object.keys(statesData) })
        });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || "Comparison failed.");
        }

        resultsElement.innerHTML = data.comparison.map((item, index) => `
            <div class="compare-card ${index === 0 ? "cheapest" : ""}">
                <div class="cc-state">${item.state}</div>
                <div class="cc-bill">Rs ${item.total_bill.toLocaleString("en-IN")}</div>
                <div class="cc-utility">DISCOM: ${item.utility}</div>
                <div class="cc-rate">${item.category} | Rs ${item.effective_rate}/unit effective</div>
                <div class="cc-solar">Solar payback: ${formatPayback(item.solar_payback_years, item.solar_payback_reached)}</div>
                <div class="cc-solar">Monthly solar savings: Rs ${item.monthly_solar_savings.toLocaleString("en-IN")}</div>
            </div>
        `).join("");
    } catch (error) {
        resultsElement.innerHTML = `<div class="compare-card">Could not load comparison right now.</div>`;
    }
}
