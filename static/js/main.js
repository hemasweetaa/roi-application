document.addEventListener('DOMContentLoaded', () => {
    // --- DOM Element References ---
    const form = document.getElementById('roi-form');
    const monthlySavingsEl = document.getElementById('monthly-savings');
    const paybackMonthsEl = document.getElementById('payback-months');
    const roiPercentageEl = document.getElementById('roi-percentage');
    const downloadReportBtn = document.getElementById('download-report-btn');
    const emailModal = document.getElementById('email-modal');
    const emailForm = document.getElementById('email-form');
    
    const saveScenarioBtn = document.getElementById('save-scenario-btn');
    const loadScenarioBtn = document.getElementById('load-scenario-btn');
    const savedScenariosList = document.getElementById('saved-scenarios-list');

    let latestResults = {};
    let latestInputs = {};

    // --- Core Calculation Function ---
    const calculate = async () => {
        const formData = new FormData(form);
        const data = {};
        formData.forEach((value, key) => {
            data[key] = parseFloat(value) || 0;
        });
        latestInputs = data;

        const response = await fetch('/simulate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });

        if (response.ok) {
            const results = await response.json();
            latestResults = results;
            updateResultsUI(results);
        }
    };

    const updateResultsUI = (results) => {
        monthlySavingsEl.textContent = `$${results.monthly_savings.toLocaleString()}`;
        paybackMonthsEl.textContent = isFinite(results.payback_months) ? `${results.payback_months} months` : 'N/A';
        const roiLabel = `ROI (${latestInputs.time_horizon_months / 12} years)`;
        document.querySelector('#results-container h4:nth-of-type(3)').textContent = roiLabel;
        roiPercentageEl.textContent = isFinite(results.roi_percentage) ? `${results.roi_percentage.toLocaleString()}%` : '∞';
    };

    // --- Scenario Management ---
    const saveScenario = async () => {
        const scenarioName = document.getElementById('scenario_name').value;
        if (!scenarioName) {
            alert('Please enter a name for the scenario.');
            return;
        }
        latestInputs.scenario_name = scenarioName;

        await fetch('/scenarios', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ inputs: latestInputs, results: latestResults }),
        });
        
        document.getElementById('scenario_name').value = ''; // Clear input
        loadScenarios(); // Refresh the list
    };
    
    const loadScenarios = async () => {
        const response = await fetch('/scenarios');
        const scenarios = await response.json();
        savedScenariosList.innerHTML = '<option value="">-- Select a scenario --</option>';
        scenarios.forEach(s => {
            const option = document.createElement('option');
            option.value = s.id;
            option.textContent = s.scenario_name;
            savedScenariosList.appendChild(option);
        });
    };

    const loadScenarioDetails = async () => {
        const scenarioId = savedScenariosList.value;
        if (!scenarioId) return;
        
        const response = await fetch(`/scenarios/${scenarioId}`);
        const data = await response.json();
        
        // Populate the form with loaded data
        for (const key in data) {
            const input = form.querySelector(`[name="${key}"]`);
            if (input) {
                input.value = data[key];
            }
        }
        calculate(); // Recalculate and update UI
    };

    // --- Report Generation ---
    const generateReport = async (event) => {
        event.preventDefault();
        const email = document.getElementById('user-email').value;
        
        const response = await fetch('/report/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ inputs: latestInputs, results: latestResults, email: email }),
        });

        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;
            a.download = 'invoicing_roi_report.pdf';
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            emailModal.close();
        } else {
            alert('Failed to generate report.');
        }
    };

    // --- Modal Toggle ---
    window.toggleModal = (event) => {
        event.preventDefault();
        const modal = document.getElementById(event.currentTarget.dataset.target);
        if (modal) {
            typeof modal.showModal === "function" ? modal.showModal() : modal.setAttribute("open", "");
        }
    };
    downloadReportBtn.addEventListener('click', (e) => emailModal.showModal());
    emailModal.addEventListener('click', (e) => {
        if(e.target === emailModal) emailModal.close();
    });

    // --- Initializers and Event Listeners ---
    form.addEventListener('input', calculate);
    saveScenarioBtn.addEventListener('click', saveScenario);
    loadScenarioBtn.addEventListener('click', loadScenarioDetails);
    emailForm.addEventListener('submit', generateReport);

    // Initial load
    calculate();
    loadScenarios();
});