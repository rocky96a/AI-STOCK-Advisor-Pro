// =====================================
// Algorithmic Strategy Dashboard
// =====================================

function updateStrategies(data) {

    if (!data) {
        console.warn("No algorithmic strategy data received");
        return;
    }

    console.log("STRATEGY DATA:", data);


    // ---------------------------------
    // Individual Strategies
    // ---------------------------------

    updateStrategy(
        "emaVote",
        data.ema
    );

    updateStrategy(
        "vwapVote",
        data.vwap
    );

    updateStrategy(
        "supertrendVote",
        data.supertrend
    );

    updateStrategy(
        "bollingerVote",
        data.bollinger
    );

    updateStrategy(
        "breakoutVote",
        data.breakout
    );

    updateStrategy(
        "orbVote",
        data.orb
    );

    updateStrategy(
        "swingVote",
        data.swing
    );

    updateStrategy(
        "scalpingVote",
        data.scalping
    );


    // ---------------------------------
    // Consensus
    // ---------------------------------

    const consensus =
        data.consensus ||
        data.final ||
        data.signal ||
        data.recommendation;


    const element =
        document.getElementById(
            "strategyConsensus"
        );


    if (element && consensus) {

        element.innerText =
            formatStrategyVote(consensus);

    }

}


// =====================================
// Update Individual Strategy
// =====================================

function updateStrategy(
    elementId,
    strategy
) {

    if (strategy === undefined ||
        strategy === null) {

        return;
    }


    const element =
        document.getElementById(
            elementId
        );


    if (!element) {
        return;
    }


    let value;


    if (typeof strategy === "object") {

        value =
            strategy.signal ||
            strategy.prediction ||
            strategy.vote ||
            strategy.direction ||
            strategy.recommendation;

    } else {

        value = strategy;

    }


    if (value !== undefined) {

        element.innerText =
            formatStrategyVote(value);

    }

}


// =====================================
// Format Vote
// =====================================

function formatStrategyVote(value) {

    if (!value) {
        return "--";
    }

    return String(value)
        .replaceAll("_", " ")
        .toUpperCase();

}


