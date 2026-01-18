// 1. Text Extraction
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "getText") {
        const fullText = document.body.innerText;
        const cleanText = fullText.replace(/\s+/g, ' ').trim();
        sendResponse({ text: cleanText });
    }

    // 2. Highlighting Logic
    if (request.action === "highlightRisks") {
        const clauses = request.clauses; // Array of {text: "...", risk_score: 20}

        if (!clauses || clauses.length === 0) return;

        highlightTextOnPage(clauses);
        sendResponse({ status: "success" });
    }
    return true;
});

function highlightTextOnPage(clauses) {
    // Simple traversal to find and highlight text nodes
    // Note: robust highlighting on complex DOMs is hard. 
    // This is a simplified "exact match" approach on text nodes.

    function escapeRegExp(string) {
        return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }

    // Performance optimization: Combine phrases into one regex? 
    // Or just iterate. Let's iterate for simplicity and control.

    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
    const textNodes = [];
    let node;
    while (node = walker.nextNode()) {
        textNodes.push(node);
    }

    clauses.forEach(clause => {
        // We look for a significant substring to match, as extraction might strip some whitespace/chars
        const searchPhrase = clause.text.substring(0, 50); // Match first 50 chars
        if (searchPhrase.length < 10) return;

        textNodes.forEach(node => {
            const nodeText = node.nodeValue;
            if (nodeText.includes(searchPhrase)) {
                // Determine highlight color based on score
                let color = "yellow";
                if (clause.risk_score > 40) color = "#fae8e8"; // Light red

                const span = document.createElement('span');
                span.style.backgroundColor = color;
                span.style.borderBottom = "2px solid red";
                span.title = `Risk: ${clause.issues.join(", ")}`;
                span.innerText = nodeText;

                // Replace text node with span
                try {
                    if (node.parentNode) {
                        node.parentNode.replaceChild(span, node);
                    }
                } catch (e) { }
            }
        });
    });
}
