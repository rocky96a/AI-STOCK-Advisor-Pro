async function analyzeStock() {

    const symbol =
        normalizeStockSymbol(document.getElementById("symbol").value || "RELIANCE");

    try{

        // Technical data
        const analyzeResponse =
            await apiFetch(`/api/analyze/${symbol}`);

        const analyzeData =
            await analyzeResponse.json();

        // AI prediction
        const predictResponse =
            await apiFetch(`/api/predict/${symbol}`);

        const predictData =
            await predictResponse.json();

        // Existing company card
        updateDashboard(analyzeData);

        // New Phase 5 cards
        updateAI(predictData);

        updateConfidence(predictData.ai);

        updateMLModels(predictData.ml);

        updateStrategyVotes(predictData.algorithmic);

        updateTradeSetup(predictData.decision);

        updateNews(predictData.news);

    }

    catch(error){

        console.error(error);

    }

}

function updateMLModels(ml){

    if(!ml) return;

    document.getElementById("rfPrediction").innerHTML =
        ml.random_forest.prediction;

    document.getElementById("rfConfidence").innerHTML =
        ml.random_forest.confidence + "%";

    document.getElementById("xgbPrediction").innerHTML =
        ml.xgboost.prediction;

    document.getElementById("xgbConfidence").innerHTML =
        ml.xgboost.confidence + "%";

    document.getElementById("lstmPrediction").innerHTML =
        ml.lstm.prediction;

    document.getElementById("lstmConfidence").innerHTML =
        ml.lstm.confidence + "%";

}

function updateAI(data) {

    if (!data) {
        console.warn("No AI decision data received");
        return;
    }

    console.log("AI DATA:", data);

    const action =
        data.action ||
        data.recommendation ||
        data.signal ||
        data.decision ||
        "HOLD";

    const element =
        document.getElementById("aiAction");

    if (element) {
        element.innerText =
            String(action).toUpperCase();
    }

}

function updateConfidence(ai){

    document.getElementById("confidenceValue").innerHTML =
        ai.confidence + "%";

    document.getElementById("confidenceGrade").innerHTML =
        ai.grade;

}

function updateTradeSetup(decision){

    document.getElementById("entryPrice").innerHTML =
        decision.entry;

    document.getElementById("targetPrice").innerHTML =
        decision.target;

    document.getElementById("stopLoss").innerHTML =
        decision.stoploss;

}

function updateStrategyVotes(strategy){

    if(!strategy) return;

    document.getElementById("buyVotes").innerHTML =
        strategy.buy;

    document.getElementById("sellVotes").innerHTML =
        strategy.sell;

    document.getElementById("holdVotes").innerHTML =
        strategy.hold;

    if(strategy.strategies){

        document.getElementById("emaVote").innerHTML =
            strategy.strategies.ema || "--";

        document.getElementById("supertrendVote").innerHTML =
            strategy.strategies.supertrend || "--";

        document.getElementById("vwapVote").innerHTML =
            strategy.strategies.vwap || "--";

        document.getElementById("orbVote").innerHTML =
            strategy.strategies.orb || "--";

        document.getElementById("breakoutVote").innerHTML =
            strategy.strategies.breakout || "--";

        document.getElementById("bollingerVote").innerHTML =
            strategy.strategies.bollinger || "--";

        document.getElementById("scalpingVote").innerHTML =
            strategy.strategies.scalping || "--";

        document.getElementById("swingVote").innerHTML =
            strategy.strategies.swing || "--";

    }

}

function updateNews(news){

    if(!news) return;

    document.getElementById("newsSentiment").innerHTML =
        news.sentiment;

    document.getElementById("newsConfidence").innerHTML =
        news.confidence + "%";

    document.getElementById("newsArticles").innerHTML =
        news.articles;

    const list =
        document.getElementById("newsList");

    list.innerHTML = "";

    if(news.details){

        news.details.forEach(item=>{

            list.innerHTML += `

                <div class="news-item">

                    <h4>${item.title}</h4>

                    <span>${item.sentiment}</span>

                    •

                    <span>${item.confidence}%</span>

                </div>

            `;

        });

    }

}