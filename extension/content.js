// 1. Smart Text Extraction
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "getText") {
        const text = extractMainContent();
        sendResponse({ text: text });
    }

    if (request.action === "highlightRisks") {
        const clauses = request.clauses;
        if (!clauses || clauses.length === 0) return;
        highlightTextOnPage(clauses);
        sendResponse({ status: "success" });
    }
    return true;
});

function extractMainContent() {
    // Clone body to avoid messing up the page during extraction
    const clone = document.body.cloneNode(true);

    // Remove noise elements
    const cleanupTags = ['SCRIPT', 'STYLE', 'NOSCRIPT', 'IFRAME', 'NAV', 'FOOTER', 'HEADER', 'ASIDE'];
    const candidates = clone.querySelectorAll(cleanupTags.join(','));
    candidates.forEach(el => el.remove());

    // Also remove elements with "hidden" class or style
    // (This is hard on a clone without computed styles, so we rely on innerText's visibility logic mostly)

    // Get text
    let text = clone.innerText;

    // Normalize whitespace
    text = text.replace(/\s+/g, ' ').trim();
    return text;
}

// 2. Robust Highlighting
function highlightTextOnPage(clauses) {
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
    const textNodes = [];
    let node;
    while (node = walker.nextNode()) {
        if (node.nodeValue.trim().length > 10) { // Ignore tiny nodes
            textNodes.push(node);
        }
    }

    clauses.forEach(clause => {
        const clauseText = clause.text.replace(/\s+/g, ' ').trim();
        if (clauseText.length < 10) return;

        // Strategy: Match the first 50 chars significant enough to be unique
        const searchChunk = clauseText.substring(0, 60);

        for (const node of textNodes) {
            const nodeText = node.nodeValue.replace(/\s+/g, ' ');

            // 1. Exact match (normalized)
            if (nodeText.includes(searchChunk)) {
                highlightNode(node, searchChunk, clause);
                return; // Found it
            }

            // 2. Fuzzy Context Match (First 20 chars + Last 20 chars of chunk)
            // Useful if there are minor typos or distinct words
            if (searchChunk.length > 40) {
                const start = searchChunk.substring(0, 20);
                const end = searchChunk.substring(searchChunk.length - 20);
                if (nodeText.includes(start) && nodeText.includes(end)) {
                    highlightNode(node, start, clause);
                    return;
                }
            }
        }
    });
}

function highlightNode(node, matchText, clause) {
    try {
        // Style based on risk score
        let bgColor = "#fffbeb"; // Warning yellow
        let borderColor = "#f59e0b";

        if (clause.risk_score > 75) {
            bgColor = "#fef2f2"; // Danger red
            borderColor = "#ef4444";
        }

        const nodeText = node.nodeValue;
        const matchIndex = nodeText.indexOf(matchText);

        if (matchIndex === -1 || !node.parentNode) return;

        // Split: [before][matched highlight][after]
        const before = nodeText.substring(0, matchIndex);
        const matched = nodeText.substring(matchIndex, matchIndex + matchText.length);
        const after = nodeText.substring(matchIndex + matchText.length);

        const span = document.createElement('span');
        span.style.backgroundColor = bgColor;
        span.style.borderBottom = `2px solid ${borderColor}`;
        span.style.cursor = "help";
        span.title = `Risk: ${clause.issues.join(", ")}`;
        span.textContent = matched;

        const parent = node.parentNode;
        const afterNode = document.createTextNode(after);
        parent.insertBefore(document.createTextNode(before), node);
        parent.insertBefore(span, node);
        parent.insertBefore(afterNode, node);
        parent.removeChild(node);
    } catch (e) {
        console.error("Highlight Error", e);
    }
}