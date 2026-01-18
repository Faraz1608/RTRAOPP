document.addEventListener('DOMContentLoaded', () => {
    const scanBtn = document.getElementById('scan-btn');
    const backBtn = document.getElementById('back-btn');
    const retryBtn = document.getElementById('retry-btn');
    const manualScanBtn = document.getElementById('manual-scan-btn');
    const pdfUpload = document.getElementById('pdf-upload');
    const historyList = document.getElementById('history-list');

    // Tab Elements
    const tabs = document.querySelectorAll('.tab-btn');

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
    const categoryList = document.getElementById('category-list');

    // --- Tab Switching ---
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active', 'hidden')); // Reset
            document.querySelectorAll('.tab-content').forEach(c => c.style.display = 'none');

            tab.classList.add('active');
            const contentId = tab.dataset.tab;
            const content = document.getElementById(contentId);
            content.style.display = 'block';
            content.classList.add('active');

            if (contentId === 'history-tab') loadHistory();
        });
    });

    scanBtn.addEventListener('click', startScan);
    backBtn.addEventListener('click', () => location.reload());
    retryBtn.addEventListener('click', startScan);

    if (manualScanBtn) {
        manualScanBtn.addEventListener('click', () => {
            const text = document.getElementById('paste-area').value;
            if (text) analyzeText(text);
        });
    }

    if (pdfUpload) {
        pdfUpload.addEventListener('change', async (e) => {
            const file = e.target.files[0];
            if (!file) return;

            const formData = new FormData();
            formData.append('file', file);

            showView(loadingView);
            try {
                const res = await fetch('http://localhost:8000/upload', { method: 'POST', body: formData });
                if (!res.ok) throw new Error("Upload failed");
                const data = await res.json();
                renderResults(data);
            } catch (err) {
                console.error(err);
                showError("PDF Upload failed.");
            }
        });
    }

    function showView(view) {
        [loadingView, resultsView, errorView].forEach(v => v.classList.add('hidden'));
        if (view !== initialView) initialView.classList.add('hidden');
        view.classList.remove('hidden');
    }

    function startScan() {
        showView(loadingView);

        // querying the active tab
        chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
            const activeTab = tabs[0];
            const url = activeTab.url;

            // Send message to content script
            chrome.tabs.sendMessage(activeTab.id, { action: "getText" }, (response) => {
                if (chrome.runtime.lastError) {
                    console.error(chrome.runtime.lastError);
                    showError("Could not connect to page. Reload.");
                    return;
                }

                if (response && response.text) {
                    analyzeText(response.text, url, activeTab.id);
                } else {
                    showError("No text found on this page.");
                }
            });
        });
    }

    async function analyzeText(text, url = null, tabId = null) {
        try {
            const payload = { text: text };
            if (url) payload.url = url;

            const res = await fetch('http://localhost:8000/analyze', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!res.ok) throw new Error("Server error");

            const data = await res.json();
            renderResults(data);

            // Highlight if we have a tabId (only for page scans)
            if (tabId && data.risky_clauses) {
                chrome.tabs.sendMessage(tabId, {
                    action: "highlightRisks",
                    clauses: data.risky_clauses
                });
            }

        } catch (err) {
            console.error(err);
            showView(errorView);
        }
    }

    async function loadHistory() {
        try {
            const res = await fetch('http://localhost:8000/history');
            const scans = await res.json();
            if (historyList) {
                historyList.innerHTML = '';
                scans.forEach(scan => {
                    const li = document.createElement('li');
                    li.style.borderBottom = "1px solid #334155";
                    li.style.padding = "10px";
                    li.innerHTML = `
                        <div style="display:flex; justify-content:space-between; color:white;">
                            <span>${scan.domain}</span>
                            <span style="color:${scan.risk_level === 'HIGH' ? '#ef4444' : '#22c55e'}">${scan.risk_level}</span>
                        </div>
                        <div style="font-size:0.75rem; color:#94a3b8;">
                            Score: ${scan.risk_score} • ${new Date(scan.timestamp).toLocaleDateString()}
                        </div>
                    `;
                    historyList.appendChild(li);
                });
            }
        } catch (e) {
            if (historyList) historyList.innerHTML = '<li>Failed to load history</li>';
        }
    }

    function renderResults(data) {
        showView(resultsView);

        // Risk Level Color
        riskLevelEl.innerText = data.risk_level;
        let color = '#28a745';
        if (data.risk_level === 'MEDIUM') color = '#ffc107';
        if (data.risk_level === 'HIGH') color = '#dc3545';

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
        if (categoryList && data.category_details) {
            categoryList.innerHTML = '';
            for (const [cat, score] of Object.entries(data.category_details)) {
                let catColor = '#22c55e';
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
        // Reset tabs potentially? Or just go to Scan view
        showView(initialView);
    }

    function showError(msg) {
        showView(errorView);
        document.querySelector('.error-msg').innerText = msg;
    }
});
