// =====================================
// AI Prediction Compatibility
// =====================================

async function loadAIPrediction() {

    const symbolElement = document.getElementById("symbol");

    if (!symbolElement) {
        return;
    }

    const symbol = normalizeStockSymbol(symbolElement.value || "RELIANCE");

    try {

        const response =
            await apiFetch(`/api/predict/${encodeURIComponent(symbol)}`);

        if (!response.ok) {
            throw new Error("Prediction API failed");
        }

        const data = await response.json();

        console.log("AI DATA:", data);

        if (typeof updateAI === "function") {
            updateAI(data);
        }

        if (typeof updateAIReasoning === "function") {
            updateAIReasoning(data);
        }

    } catch (error) {

        console.error("AI prediction error:", error);

        setText("aiAction", "N/A");
        setText("aiScore", "--");
    }
}
