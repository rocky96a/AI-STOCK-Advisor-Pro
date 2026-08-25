// =====================================
// REAL STOCK PREDICTION
// File: static/js/app.js
// =====================================

let analysisInProgress = false;

async function analyzeStock() {

    if (analysisInProgress) {
        return;
    }

    analysisInProgress = true;

    const symbolInput = document.getElementById("symbol");

    const symbol = normalizeStockSymbol(
        symbolInput && symbolInput.value
            ? symbolInput.value
            : "RELIANCE.NS"
    );

    // Keep the search box user-friendly: never expose .NS / Yahoo index codes.
    if (symbolInput) {
        symbolInput.value = displayStockSymbol(symbol);
    }

    console.log("=================================");
    console.log("LOADING STOCK:", symbol);
    console.log("=================================");

    try {

        // ---------------------------------
        // Get real prediction
        //
        // Uses the currently selected chart timeframe so the verdict/
        // indicators reflect the same candle interval being viewed
        // (5m, 15m, etc.) instead of always analyzing the daily chart.
        // Cached client-side (ApiCache) so returning to this page
        // within the TTL window renders instantly, no API call.
        // ---------------------------------

        const interval = currentInterval || "1d";

        const predictUrl =
            `/api/predict/${encodeURIComponent(symbol)}?interval=${encodeURIComponent(interval)}`;

        const data = typeof ApiCache !== "undefined"
            ? await ApiCache.fetchJSON(predictUrl)
            : await (await apiFetch(predictUrl)).json();

        // Remember what was searched so returning to this page (or a
        // fresh tab) picks up where you left off instead of always
        // resetting to RELIANCE.NS.
        try {
            localStorage.setItem("jm_last_symbol", symbol);
            localStorage.setItem("jm_last_interval", interval);
        } catch (storageErr) {
            // ignore — non-fatal
        }

        // IMPORTANT: reload the TradingView chart for the newly searched stock.
        // The prediction/dashboard request and chart request are separate APIs;
        // updating the cards alone does not change the existing candle series.
        if (typeof loadChart === "function") {
            try {
                await loadChart(symbol, interval);
                console.log("CHART UPDATED FOR:", symbol);
            } catch (chartError) {
                console.error("Chart update after stock search failed:", chartError);
            }
        } else {
            console.warn("loadChart() is not available yet.");
        }

        // IMPORTANT
        console.log("REAL API DATA:");
        console.log(data);
        console.log(
            "REAL API JSON:",
            JSON.stringify(data, null, 2)
        );

        // ---------------------------------
        // Update company information
        // ---------------------------------

        updateCompany(data);

        // ---------------------------------
        // Update Verdict (single unified decision)
        // ---------------------------------

        updateVerdict(data, symbol);

        // ---------------------------------
        // Update AI
        // ---------------------------------

        updateAI(data);
        updateAIReasoning(data);
        updateTechnical(data.technical);

        // ---------------------------------
        // Update Confidence
        // ---------------------------------

        updateConfidence(data.decision, data.ai);

        // ---------------------------------
        // Update ML
        // ---------------------------------

        updateMLModels(data.ml);

        // ---------------------------------
        // Update Strategies
        // ---------------------------------

        updateStrategyVotes(data.algorithmic);

        // ---------------------------------
        // Update Trade Setup
        // ---------------------------------

        updateTradeSetup(data.decision, data.algorithmic);

        // ---------------------------------
        // Update News
        // ---------------------------------

     updateNews(data.news);

        console.log("=================================");
        console.log("DASHBOARD UPDATED");
        console.log("=================================");

    }

    catch (error) {

        console.error(
            "Prediction API error:",
            error
        );

        setText("aiAction", "ERROR");
        setText("aiScore", "--");
        setText("newsSentiment", "Unavailable");
        setText("newsArticles", "0");

        const verdictCard = document.getElementById("verdictCard");
        if (verdictCard) {
            verdictCard.dataset.state = "idle";
            verdictCard.dataset.signal = "";
            setText("verdictHeadline", "Couldn't fetch a verdict for that symbol. Try again in a moment.");
        }

    } finally {

        analysisInProgress = false;

    }
}


// =====================================
// COMPANY
// File: static/js/app.js
// =====================================

function updateCompany(data) {

    console.log("COMPANY DATA:", data);

    const company =
        document.getElementById("companyName");

    if (company) {

        company.innerText =
            data.company || "--";

    }


    const sector =
        document.getElementById("sector");

    if (sector) {
        sector.innerText = data.sector || "--";
    }

    const industry =
        document.getElementById("industry");

    if (industry) {
        industry.innerText = data.industry || "--";
    }

    const priceChange =
        document.getElementById("priceChange");

    if (priceChange) {
        const change = data.priceChange ?? data.change ?? data.change_percent;
        priceChange.innerText =
            change !== undefined && change !== null
                ? (String(change).includes("%") ? String(change) : `${change}%`)
                : "--";
    }


    const price =
        document.getElementById("price");

    if (price) {

        price.innerText =
            data.price !== undefined
                ? "₹ " + data.price
                : "--";

    }


    const symbol =
        document.getElementById("symbolName");

    if (symbol) {

        symbol.innerText =
            data.symbol || "--";

    }

}


// =====================================
// FINAL AI / DECISION
// =====================================

function updateAI(data) {

    if (!data) {
        console.warn("Decision data missing");
        return;
    }

    const decision = data.decision || {};
    const ai = data.ai || {};

    const action =
        decision.signal ||
        decision.final_signal ||
        decision.action ||
        ai.recommendation ||
        ai.signal ||
        "HOLD";

    setText("aiAction", String(action).toUpperCase());
    setText(
        "aiScore",
        decision.confidence !== undefined
            ? Number(decision.confidence).toFixed(1) + "%"
            : (ai.score !== undefined ? ai.score : "--")
    );

    setText(
        "reasoningSignal",
        String(action).toUpperCase()
    );

    setText(
        "decisionDirection",
        decision.direction || "--"
    );

    setText(
        "decisionStrength",
        decision.strength || "--"
    );

    setText(
        "decisionConfidence",
        decision.confidence !== undefined
            ? Number(decision.confidence).toFixed(1) + "%"
            : "--"
    );

    setText(
        "decisionBlocked",
        decision.blocked ? "BLOCKED" : "ACTIVE"
    );

    setText(
        "decisionStatus",
        decision.blocked
            ? "Safety block is active"
            : "Decision is active"
    );

    updateMTF(decision.multi_timeframe);
}

// =====================================
// CONFIDENCE
// File: static/js/app.js
// =====================================

function updateConfidence(decision, ai) {

    decision = decision || {};
    ai = ai || {};

    const confidence =
        decision.confidence !== undefined
            ? decision.confidence
            : (ai.confidence !== undefined ? ai.confidence : 0);

    const grade =
        ai.grade || "--";


    const confidenceElement =
        document.getElementById("confidenceValue");

    if (confidenceElement) {

        confidenceElement.innerText =
            confidence + "%";

    }


    const gradeElement =
        document.getElementById("confidenceGrade");

    if (gradeElement) {

        gradeElement.innerText =
            grade;

    }

}


// =====================================
// MACHINE LEARNING
// File: static/js/app.js
// =====================================

function updateMLModels(ml) {

    if (!ml) {
        console.warn("ML data missing");
        return;
    }

    console.log("ML DATA:", ml);

    setText(
        "mlDirection",
        ml.direction ?? "--"
    );

    setText(
        "mlConfidence",
        ml.confidence !== undefined
            ? ml.confidence + "%"
            : "--"
    );

    const probabilities = ml.probabilities || {};

    setText(
        "mlUpProbability",
        probabilities.BUY !== undefined
            ? probabilities.BUY + "%"
            : "--"
    );

    setText(
        "mlDownProbability",
        probabilities.SELL !== undefined
            ? probabilities.SELL + "%"
            : "--"
    );

    setText(
        "mlHorizon",
        ml.horizon_candles !== undefined
            ? ml.horizon_candles + " candles"
            : "--"
    );
}

// =====================================
// STRATEGIES
// File: static/js/app.js
// =====================================

function updateStrategyVotes(strategy) {

    if (!strategy) {
        console.warn("Strategy data missing");
        return;
    }

    console.log("STRATEGY DATA:", strategy);


    // ==============================
    // Overall Votes
    // ==============================

    setText(
        "buyVotes",
        strategy.buy_votes ?? 0
    );

    setText(
        "sellVotes",
        strategy.sell_votes ?? 0
    );

    setText(
        "holdVotes",
        strategy.hold_votes ?? 0
    );

    setText(
        "strategyConfidence",
        strategy.confidence !== undefined
            ? strategy.confidence + "%"
            : "--"
    );

    setText(
        "strategyConsensus",
        strategy.signal ?? "HOLD"
    );


    // ==============================
    // Individual Strategies
    // ==============================

    const strategies =
        Array.isArray(strategy.strategies)
            ? strategy.strategies
            : [];


    strategies.forEach(item => {

        const name =
            String(item.strategy || "").toLowerCase();

        const signal =
            item.signal || "--";


        if (name.includes("ema")) {

            setText(
                "emaVote",
                signal
            );

        }

        else if (name.includes("vwap")) {

            setText(
                "vwapVote",
                signal
            );

        }

        else if (name.includes("supertrend")) {

            setText(
                "supertrendVote",
                signal
            );

        }

        else if (name.includes("bollinger")) {

            setText(
                "bollingerVote",
                signal
            );

        }

        else if (name.includes("breakout")) {

            setText(
                "breakoutVote",
                signal
            );

        }

        else if (name.includes("orb")) {

            setText(
                "orbVote",
                signal
            );

        }

        else if (name.includes("swing")) {

            setText(
                "swingVote",
                signal
            );

        }

        else if (name.includes("scalping")) {

            setText(
                "scalpingVote",
                signal
            );

        }

        else if (name.includes("position")) {

            setText(
                "positionVote",
                signal
            );

        }

    });

}


// =====================================
// VERDICT (unified decision card)
// File: static/js/app.js
// =====================================

const GAUGE_CIRCUMFERENCE = 188.4; // matches the arc length in verdict.html

function updateVerdict(data, symbol) {

    const card = document.getElementById("verdictCard");
    if (!card) return;

    const decision = data.decision || {};
    const technical = data.technical || {};
    const ml = data.ml || {};
    const algorithmic = data.algorithmic || {};
    const news = data.news || {};

    const available = decision.available !== false;
    const rawSignal = String(decision.signal || "HOLD").toUpperCase();
    const signalKey = rawSignal.replace(/\s+/g, "_"); // "STRONG BUY" -> "STRONG_BUY"
    const confidence = Number(decision.confidence || 0);

    card.dataset.state = "ready";
    card.dataset.signal = signalKey;

    setText("verdictSymbol", displayStockSymbol(symbol));
    setText("verdictSignal", available ? rawSignal.replace("_", " ") : "NO DATA");
    setText("verdictConfidence", available ? `${confidence.toFixed(0)}%` : "--");

    // Gauge arc: 0-100 confidence mapped to the arc's stroke-dashoffset.
    const gaugeFill = document.getElementById("gaugeFill");
    if (gaugeFill) {
        const pct = Math.max(0, Math.min(100, confidence)) / 100;
        gaugeFill.style.strokeDashoffset = String(GAUGE_CIRCUMFERENCE * (1 - pct));
    }

    // Plain-English headline built from the engine's own reasons.
    const reasons = Array.isArray(decision.reasons) ? decision.reasons : [];
    const headline = available
        ? (reasons.length
            ? reasons.slice(0, 2).join(". ") + "."
            : `${rawSignal.replace("_", " ")} with ${confidence.toFixed(0)}% confidence.`)
        : "Not enough data to form a verdict for this symbol right now.";
    setText("verdictHeadline", headline);

    // Confluence bar: how each source leans (bull/bear/neutral), equal-width segments.
    const leanOf = (signalText) => {
        const s = String(signalText || "").toUpperCase();
        if (s.includes("BUY") || s === "UP" || s === "BULLISH") return "bull";
        if (s.includes("SELL") || s === "DOWN" || s === "BEARISH") return "bear";
        return "neutral";
    };

    const sources = [
        { id: 0, lean: leanOf(ml.direction || ml.signal) },
        { id: 1, lean: leanOf(technical.signal) },
        { id: 2, lean: leanOf(algorithmic.signal) },
        { id: 3, lean: leanOf(news.sentiment) },
    ];

    const segs = document.querySelectorAll("#confluenceBar .confluence-seg");
    segs.forEach((seg, i) => {
        if (sources[i]) {
            seg.dataset.lean = sources[i].lean;
        }
    });

    // Trade levels (now provided directly by DecisionEngine).
    const fmtPrice = (v) => (v === null || v === undefined ? "--" : `₹${v}`);
    setText("v-entry", fmtPrice(decision.entry));
    setText("v-stoploss", fmtPrice(decision.stoploss));
    setText("v-target1", fmtPrice(decision.target1));
    setText("v-target2", fmtPrice(decision.target2));
    setText("v-rr", decision.risk_reward !== null && decision.risk_reward !== undefined
        ? `1 : ${decision.risk_reward}`
        : "--");

    // Reason chips. Warnings (⚠, e.g. a failed sub-calculation) are always
    // surfaced first so they can never get silently cut off by the limit.
    const footer = document.getElementById("verdictReasons");
    if (footer) {
        footer.innerHTML = "";
        const warnings = reasons.filter((r) => r.startsWith("⚠"));
        const normal = reasons.filter((r) => !r.startsWith("⚠"));
        const toShow = [...warnings, ...normal].slice(0, 4);
        toShow.forEach((reason) => {
            const chip = document.createElement("span");
            chip.className = "reason-chip" + (reason.startsWith("⚠") ? " reason-chip-warn" : "");
            chip.textContent = reason;
            footer.appendChild(chip);
        });
    }

    // Mark entry / stop-loss / target directly on the candlestick chart.
    if (typeof plotTradeLevels === "function") {
        try {
            plotTradeLevels(decision);
        } catch (err) {
            console.warn("plotTradeLevels failed:", err);
        }
    } else if (typeof clearTradeLevels === "function") {
        clearTradeLevels();
    }
}

// =====================================
// TRADE SETUP
// File: static/js/app.js
// =====================================

function updateTradeSetup(decision, algorithmic) {

    if (!decision) {
        console.warn("Decision data missing");
        return;
    }

    console.log("DECISION DATA:", decision);

    algorithmic = algorithmic || {};

    const entry = decision.entry ?? algorithmic.entry;
    const stoploss = decision.stoploss ?? algorithmic.stoploss;
    const target1 = decision.target1 ?? algorithmic.target1;
    const target2 = decision.target2 ?? algorithmic.target2;
    const riskReward = decision.risk_reward ?? algorithmic.risk_reward;

    setText(
        "tradeSignal",
        decision.signal ?? decision.final_signal ?? algorithmic.signal ?? "--"
    );

    setText(
        "entryPrice",
        entry !== undefined && entry !== null
            ? "₹ " + entry
            : "--"
    );

    setText(
        "stopLoss",
        stoploss !== null && stoploss !== undefined
            ? "₹ " + stoploss
            : "--"
    );

    setText(
        "targetPrice",
        target1 !== null && target1 !== undefined
            ? "₹ " + target1
            : "--"
    );

    setText(
        "targetPrice2",
        target2 !== null && target2 !== undefined
            ? "₹ " + target2
            : "--"
    );

    setText(
        "riskReward",
        riskReward !== null && riskReward !== undefined
            ? riskReward
            : "--"
    );

}

// =====================================
// TECHNICAL SUMMARY
// =====================================

function updateTechnical(technical) {

    if (!technical) {
        console.warn("Technical data missing");
        return;
    }

    setText("technicalSignal", technical.signal || "--");
    setText("technicalDirection", technical.direction || "--");
    setText("technicalStrength", technical.strength || "--");
    setText(
        "technicalConfidence",
        technical.confidence !== undefined
            ? Number(technical.confidence).toFixed(1) + "%"
            : "--"
    );
    setText(
        "technicalBullish",
        technical.bullish_score !== undefined
            ? Number(technical.bullish_score).toFixed(1)
            : "--"
    );
    setText(
        "technicalBearish",
        technical.bearish_score !== undefined
            ? Number(technical.bearish_score).toFixed(1)
            : "--"
    );
    setText(
        "technicalComponents",
        technical.analyzer_count !== undefined
            ? technical.analyzer_count
            : "--"
    );

    const container = document.getElementById("technicalReasons");
    if (!container) return;

    const reasons = Array.isArray(technical.reasons)
        ? technical.reasons
        : [];

    container.innerHTML = reasons.length
        ? reasons.map(reason => `
            <div class="reason-item">
                <span>•</span>
                <span>${escapeHTML(reason)}</span>
            </div>
        `).join("")
        : '<div class="reason-item">No technical reasons available.</div>';
}


// =====================================
// NEWS
// File: static/js/app.js
// =====================================

function updateNews(news) {

    if (!news) {
        console.warn("News data missing");
        return;
    }

    console.log("NEWS DATA:", news);


    // ==============================
    // Sentiment
    // ==============================

    const sentiment = news.sentiment || {};


    setText(
        "newsSentiment",
        sentiment.label ??
        sentiment.sentiment ??
        "Neutral"
    );


    setText(
        "newsConfidence",
        sentiment.confidence !== undefined
            ? sentiment.confidence + "%"
            : "0%"
    );


    // ==============================
    // Articles
    // ==============================

    const articles =
        Array.isArray(news.news)
            ? news.news
            : [];


    setText(
        "newsArticles",
        articles.length
    );


    const list =
        document.getElementById("newsList");


    if (!list) {
        console.warn(
            "newsList element not found"
        );
        return;
    }


    list.innerHTML = "";


    articles.forEach(item => {

        const div =
            document.createElement("div");


        div.className =
            "news-item";


        const title =
            item.title ||
            item.headline ||
            "Untitled";


        const sentimentValue =
            item.sentiment ||
            "Neutral";


        const url = item.url || "";
        const publisher = item.publisher || "";
        const published = item.published || "";

        div.innerHTML = `
            <h4>
                ${url
                    ? `<a href="${escapeHTML(url)}" target="_blank" rel="noopener noreferrer">${escapeHTML(title)}</a>`
                    : escapeHTML(title)}
            </h4>

            <span>${escapeHTML(sentimentValue)}</span>
            ${publisher ? `<small>${escapeHTML(publisher)}</small>` : ""}
            ${published ? `<small>${escapeHTML(published)}</small>` : ""}
        `;


        list.appendChild(div);

    });

}


// =====================================
// SAFE TEXT UPDATE
// =====================================

function setText(id, value) {

    const element =
        document.getElementById(id);

    if (!element) {

        console.warn(
            "HTML element not found:",
            id
        );

        return;
    }

    element.innerText =
        value;

}


// =====================================
// BUTTON
// =====================================

document.addEventListener(
    "DOMContentLoaded",
    function () {

        const button =
            document.getElementById("analyzeBtn");


        if (button) {

            button.addEventListener(
                "click",
                analyzeStock
            );

        }

        const input = document.getElementById("symbol");

        if (input) {
            input.addEventListener("keydown", function (event) {
                if (event.key === "Enter") {
                    event.preventDefault();
                    analyzeStock();
                }
            });
        }


        // Restore the last-viewed stock and timeframe so navigating away
        // and back doesn't silently reset to RELIANCE.NS / 1 Day and
        // force a fresh API call for a stock you weren't even looking at.
        try {
            const savedSymbol = localStorage.getItem("jm_last_symbol");
            const savedInterval = localStorage.getItem("jm_last_interval");

            if (savedSymbol && input) {
                input.value = displayStockSymbol(savedSymbol);
            }

            if (savedInterval) {
                currentInterval = savedInterval;

                const timeframeSelect = document.getElementById("timeframe");
                if (timeframeSelect) {
                    // Reverse-map the Yahoo interval back to the UI's
                    // dropdown value (map is UI -> Yahoo in chart.js).
                    const reverseMap = {
                        "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m",
                        "60m": "1h", "1d": "1d", "1wk": "1w", "1mo": "1mo",
                    };
                    const uiValue = reverseMap[savedInterval];
                    if (uiValue) timeframeSelect.value = uiValue;
                }
            }
        } catch (storageErr) {
            // ignore — non-fatal, falls back to defaults
        }

        // Load automatically

        loadMarketBar();
        analyzeStock();

    }
);

function updateAIReasoning(data) {

    const decision = data?.decision || {};
    const ai = data?.ai || {};

    const container = document.getElementById("aiReasons");

    if (!container) {
        return;
    }

    const reasons =
        Array.isArray(decision.reasons) && decision.reasons.length
            ? decision.reasons
            : (Array.isArray(ai.reasons) ? ai.reasons : []);

    if (reasons.length === 0) {
        container.innerHTML =
            '<div class="reason-item">No reasoning available.</div>';
        return;
    }

    container.innerHTML = reasons
        .map(reason => `
            <div class="reason-item">
                <span>•</span>
                <span>${escapeHTML(reason)}</span>
            </div>
        `)
        .join("");
}


function updateMTF(mtf) {

    const empty = {
        available: false,
        alignment: "NO_DATA",
        direction: "UNKNOWN",
        signal: "UNAVAILABLE",
        strength: "NONE",
        available_timeframes: 0,
        timeframes: {}
    };

    mtf = mtf || empty;

    setText("mtfAlignment", mtf.alignment || "NO_DATA");
    setText("mtfDirection", mtf.direction || "UNKNOWN");
    setText("mtfSignal", mtf.signal || "UNAVAILABLE");
    setText("mtfStrength", mtf.strength || "NONE");
    setText(
        "mtfAvailable",
        `${mtf.available_timeframes ?? 0}/3`
    );

    const timeframes = mtf.timeframes || {};

    ["1d", "1h", "15m"].forEach(tf => {

        const item = timeframes[tf] || {};

        const prefix = tf === "1d"
            ? "mtf1d"
            : tf === "1h"
                ? "mtf1h"
                : "mtf15m";

        setText(
            prefix + "Signal",
            item.signal || "UNAVAILABLE"
        );

        setText(
            prefix + "Direction",
            item.direction || "UNKNOWN"
        );

        setText(
            prefix + "Strength",
            item.strength || "NONE"
        );
    });
}


function escapeHTML(value) {

    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}


// =====================================
// LIVE MARKET BAR
// =====================================

async function loadMarketBar() {

    try {

        const response = await apiFetch("/api/market");

        if (!response.ok) {
            throw new Error(`Market API failed: ${response.status}`);
        }

        const payload = await response.json();
        const data = payload.data || {};

        const formatPrice = (key, value) => {
            if (key === "usd_inr") {
                return Number(value).toFixed(2);
            }

            if (
                key === "gold" ||
                key === "crude" ||
                key === "btc" ||
                key === "eth" ||
                key === "tesla"
            ) {
                return Number(value).toLocaleString(undefined, {
                    maximumFractionDigits: 2,
                });
            }
            return Number(value).toLocaleString(undefined, {
                maximumFractionDigits: 2,
            });
        };

        Object.entries(data).forEach(([key, item]) => {

            const priceId = {
                nifty: "niftyPrice",
                bank_nifty: "bankPrice",
                sensex: "sensexPrice",

                sp500: "sp500Price",
                nasdaq: "nasdaqPrice",
                dow: "dowPrice",
                tesla: "teslaPrice",

                usd_inr: "usdPrice",
                gold: "goldPrice",
                crude: "crudePrice",

                btc: "btcPrice",
                eth: "ethPrice",
            }[key];

            const changeId = {
                nifty: "niftyChange",
                bank_nifty: "bankChange",
                sensex: "sensexChange",

                sp500: "sp500Change",
                nasdaq: "nasdaqChange",
                dow: "dowChange",
                tesla: "teslaChange",

                usd_inr: "usdChange",
                gold: "goldChange",
                crude: "crudeChange",

                btc: "btcChange",
                eth: "ethChange",
            }[key];

            setText(
                priceId,
                formatPrice(key, item.price)
            );

            setText(
                changeId,
                `${item.change_percent > 0 ? "▲" : item.change_percent < 0 ? "▼" : "•"} ${Number(item.change_percent).toFixed(2)}%`
            );

            const card = document.querySelector(
                `[data-market-key="${key}"]`
            );

            if (card) {
                card.classList.remove("positive", "negative");

                if (item.change_percent > 0) {
                    card.classList.add("positive");
                } else if (item.change_percent < 0) {
                    card.classList.add("negative");
                }
            }
        });

    } catch (error) {

        console.error("Market bar error:", error);

    }
}


// =====================================
// PORTFOLIO + RISK DASHBOARD
// File: static/js/app.js
// =====================================

async function loadPortfolioRisk() {

    try {

        const portfolioResponse =
            await apiFetch("/api/portfolio");

        const riskResponse =
            await apiFetch("/api/risk");

        if (!portfolioResponse.ok) {
            throw new Error("Portfolio API failed");
        }

        if (!riskResponse.ok) {
            throw new Error("Risk API failed");
        }

        const portfolio =
            await portfolioResponse.json();

        const risk =
            await riskResponse.json();

        console.log("PORTFOLIO DATA:", portfolio);
        console.log("RISK DATA:", risk);

        updatePortfolio({
            total_value: portfolio.total_value,
            invested: portfolio.invested,
            cash: portfolio.available_cash,
            pnl: portfolio.total_pnl,
            risk: risk.portfolio_risk,
            max_drawdown: risk.max_drawdown,
            risk_reward: risk.risk_reward,
            positions: portfolio.positions || []
        });

    }
    catch (error) {

        console.error(
            "Portfolio/Risk error:",
            error
        );

    }

}

// =====================================
// AUTO LOAD PORTFOLIO + RISK
// =====================================

document.addEventListener("DOMContentLoaded", function () {
    loadPortfolioRisk();
});


