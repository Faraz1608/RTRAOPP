// Listen for messages from the popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "getText") {
        // Extract visible text from the body
        const fullText = document.body.innerText;
        
        // Basic cleanup (remove too much whitespace)
        const cleanText = fullText.replace(/\s+/g, ' ').trim();
        
        sendResponse({ text: cleanText });
    }
    return true; // Keep channel open
});
