document.addEventListener('DOMContentLoaded', () => {
    const scanBtn = document.getElementById('scan-btn');
    const backBtn = document.getElementById('back-btn');
    const retryBtn = document.getElementById('retry-btn');

    // Views
    const initialView = document.getElementById('initial-view');
    const loadingView = document.getElementById('loading-view');
    const resultsView = document.getElementById('results-view');
    const errorView = document.getElementById('error-view');

    // UI Elements
    const riskLevelEl = document.getElementById('risk-level');
    const riskScoreBar = document.querySelector('#risk-score-bar .fill');
    const summaryList = document.getElementById('summary-list');
    const clausesList = document.getElementById('clauses-list');

    scanBtn.addEventListener('click', startScan);
    backBtn.addEventListener('click', showInitial);
    retryBtn.addEventListener('click', startScan);

    function showView(view) {
        [initialView, loadingView, resultsView, errorView].forEach(v => v.classList.add('hidden'));
        view.classList.remove('hidden');
    }

    function startScan() {
        showView(loadingView);

        // querying the active tab
        chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
            const activeTab = tabs[0];

            // Send message to content script
            chrome.tabs.sendMessage(activeTab.id, { action: "getText" }, (response) => {
                if (chrome.runtime.lastError) {
                    console.error(chrome.runtime.lastError);
                    showError("Could not connect to page. Reload the page and try again.");
                    return;
                }

                if (response && response.text) {
                    analyzeText(response.text);
                } else {
                    showError("No text found on this page.");
                }
            });
        });
    }

    async function analyzeText(text) {
        try {
            const res = await fetch('http://localhost:8000/analyze', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ text: text })
            });

            if (!res.ok) throw new Error("Server error");

            const data = await res.json();
            renderResults(data);

        } catch (err) {
            console.error(err);
            showView(errorView);
        }
    }

    function renderResults(data) {
        showView(resultsView);

        // Risk Level Color
        riskLevelEl.innerText = data.risk_level;
        let color = '#28a745'; // Green
        if (data.risk_level === 'MEDIUM') color = '#ffc107'; // Yellow
        if (data.risk_level === 'HIGH') color = '#dc3545'; // Red

        riskLevelEl.style.color = color;
        riskScoreBar.style.backgroundColor = color;
        riskScoreBar.style.width = `${data.total_risk_score}%`;

        // Summary
        summaryList.innerHTML = '';
        data.summary.forEach(item => {
            const li = document.createElement('li');
            li.innerText = item;
            summaryList.appendChild(li);
        });

        // Category Breakdown
        const categoryList = document.getElementById('category-list');
        if (categoryList && data.category_details) {
            categoryList.innerHTML = '';
            for (const [cat, score] of Object.entries(data.category_details)) {
                let catColor = '#22c55e'; // Green
                if (score > 20) catColor = '#ffc107';
                if (score > 50) catColor = '#ef4444';

                const catItem = document.createElement('div');
                catItem.style.marginBottom = '8px';
                catItem.innerHTML = `
                    <div style="display:flex; justify-content:space-between; font-size:0.8rem; margin-bottom:2px;">
                        <span>${cat}</span>
                        <span style="color:${catColor}; font-weight:bold;">${score > 0 ? score : 'Safe'}</span>
                    </div>
                    <div style="width:100%; background:#334155; height:4px; border-radius:2px;">
                        <div style="width:${score}%; background:${catColor}; height:100%; border-radius:2px;"></div>
                    </div>
                `;
                categoryList.appendChild(catItem);
            }
        }

        // Risky Clauses
        clausesList.innerHTML = '';
        if (data.risky_clauses.length === 0) {
            clausesList.innerHTML = '<p>No specific risky clauses identified.</p>';
        } else {
            data.risky_clauses.forEach(clause => {
                const div = document.createElement('div');
                div.className = 'clause-item';
                div.innerHTML = `
                    <div class="clause-header">
                        <span class="clause-score">Risk: ${clause.risk_score}</span>
                        <div class="clause-issues">${clause.issues.join(', ')}</div>
                    </div>
                    <p class="clause-text">"${clause.text.substring(0, 150)}..."</p>
                `;
                clausesList.appendChild(div);
            });
        }
    }

    function showInitial() {
        showView(initialView);
    }

    function showError(msg) {
        showView(errorView);
        document.querySelector('.error-msg').innerText = msg;
    }
});
