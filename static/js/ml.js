// =====================================
// ML Dashboard
// =====================================

function updateML(ml) {

    if (!ml) {
        console.warn("No ML data received");
        return;
    }

    console.log("ML DATA:", ml);


    // -----------------------------
    // Random Forest
    // -----------------------------

    updateMLModel(
        "rfPrediction",
        "rfConfidence",
        ml.random_forest || ml.randomForest
    );


    // -----------------------------
    // XGBoost
    // -----------------------------

    updateMLModel(
        "xgbPrediction",
        "xgbConfidence",
        ml.xgboost || ml.XGBoost
    );


    // -----------------------------
    // LightGBM
    // -----------------------------

    updateMLModel(
        "lgbPrediction",
        "lgbConfidence",
        ml.lightgbm || ml.LightGBM
    );


    // -----------------------------
    // LSTM
    // -----------------------------

    updateMLModel(
        "lstmPrediction",
        "lstmConfidence",
        ml.lstm || ml.LSTM
    );


    // -----------------------------
    // Consensus
    // -----------------------------

    const consensus =
        ml.consensus ||
        ml.final ||
        ml.prediction ||
        ml.signal;

    const consensusElement =
        document.getElementById("mlConsensus");

    if (consensusElement && consensus) {

        consensusElement.innerText =
            formatPrediction(consensus);

    }
}


// =====================================
// Individual Model
// =====================================

function updateMLModel(
    predictionId,
    confidenceId,
    model
) {

    if (!model) {
        return;
    }

    const prediction =
        model.prediction ||
        model.signal ||
        model.label ||
        model.direction;

    const confidence =
        model.confidence ??
        model.probability ??
        model.score;


    const predictionElement =
        document.getElementById(predictionId);

    const confidenceElement =
        document.getElementById(confidenceId);


    if (predictionElement && prediction) {

        predictionElement.innerText =
            formatPrediction(prediction);

    }


    if (confidenceElement && confidence !== undefined) {

        let value = Number(confidence);

        if (value <= 1) {
            value *= 100;
        }

        confidenceElement.innerText =
            `${value.toFixed(1)}% confidence`;

    }

}


// =====================================
// Format Prediction
// =====================================

function formatPrediction(value) {

    if (!value) {
        return "--";
    }

    return String(value)
        .replaceAll("_", " ")
        .toUpperCase();

}