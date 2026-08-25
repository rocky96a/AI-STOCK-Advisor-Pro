// ======================================================
// AI STOCK ADVISOR
// PROFESSIONAL TRADING CHART
// Complete Safe Chart Module
// ======================================================

let mainChart = null;

let candleSeries = null;
let volumeSeries = null;

let ema20Series = null;
let ema50Series = null;
let sma200Series = null;

let supportSeries = [];
let resistanceSeries = [];

let chartData = [];

let rsiChart = null;
let rsiSeries = null;

let currentSymbol = "RELIANCE.NS";
let currentInterval = "1d";

let refreshTimer = null;
let chartRequestId = 0;


// ======================================================
// CHART OPTIONS
// ======================================================

const chartOptions = {

    width: 0,
    height: 700,

    layout: {
        background: {
            color: "#0B1220"
        },
        textColor: "#D1D5DB",
        fontFamily: "Inter, Arial"
    },

    grid: {
        vertLines: {
            color: "#1E293B",
            style: 1,
            visible: true
        },
        horzLines: {
            color: "#1E293B",
            style: 1,
            visible: true
        }
    },

    crosshair: {
        mode: LightweightCharts.CrosshairMode.Normal
    },

    rightPriceScale: {
        borderColor: "#334155",
        autoScale: true
    },

    timeScale: {
        borderColor: "#334155",
        timeVisible: true,
        secondsVisible: false,
        rightOffset: 10,
        barSpacing: 8,
        fixLeftEdge: true
    }
};


// ======================================================
// INITIALIZE MAIN CHART
// ======================================================

function initChart() {

    const container =
        document.getElementById("tradingChart");

    // Watchlist and other pages may not have a chart.
    if (!container) {

        console.log(
            "Trading chart not present on this page."
        );

        return false;
    }

    // LightweightCharts library check
    if (
        typeof LightweightCharts === "undefined"
    ) {

        console.error(
            "LightweightCharts library is not loaded."
        );

        return false;
    }

    // Prevent duplicate chart creation
    if (mainChart) {
        return true;
    }

    chartOptions.width =
        container.clientWidth || 800;

    mainChart =
        LightweightCharts.createChart(
            container,
            chartOptions
        );

    createSeries();

    createRSIChart();

    window.addEventListener(
        "resize",
        resizeChart
    );

    return true;
}


// ======================================================
// CREATE MAIN SERIES
// ======================================================

function createSeries() {

    if (!mainChart) {
        return;
    }

    // ------------------------------------------
    // SMA 200
    // ------------------------------------------

    sma200Series =
        mainChart.addLineSeries({

            color: "#A855F7",

            lineWidth: 2,

            title: "SMA 200"

        });


    // ------------------------------------------
    // Candlestick
    // ------------------------------------------

    candleSeries =
        mainChart.addCandlestickSeries({

            upColor: "#26A69A",

            downColor: "#EF5350",

            borderUpColor: "#26A69A",

            borderDownColor: "#EF5350",

            wickUpColor: "#26A69A",

            wickDownColor: "#EF5350",

            borderVisible: true,

            priceLineVisible: true,

            lastValueVisible: true,

            priceFormat: {

                type: "price",

                precision: 2,

                minMove: 0.01

            }

        });


    // ------------------------------------------
    // Volume
    // ------------------------------------------

    volumeSeries =
        mainChart.addHistogramSeries({

            priceScaleId: "volume",

            priceFormat: {
                type: "volume"
            },

            lastValueVisible: false,

            priceLineVisible: false

        });


    // ------------------------------------------
    // Volume scale
    // ------------------------------------------

    mainChart
        .priceScale("volume")
        .applyOptions({

            scaleMargins: {

                top: 0.82,

                bottom: 0

            }

        });


    // ------------------------------------------
    // EMA 20
    // ------------------------------------------

    ema20Series =
        mainChart.addLineSeries({

            color: "#3B82F6",

            lineWidth: 2,

            title: "EMA 20"

        });


    // ------------------------------------------
    // EMA 50
    // ------------------------------------------

    ema50Series =
        mainChart.addLineSeries({

            color: "#FBBF24",

            lineWidth: 2,

            title: "EMA 50"

        });

}


// ======================================================
// RSI CHART
// ======================================================

function createRSIChart() {

    const rsiContainer =
        document.getElementById("rsiPane");

    const tradingContainer =
        document.getElementById("tradingChart");


    // RSI is optional
    if (!rsiContainer || !tradingContainer) {

        console.log(
            "RSI chart not present on this page."
        );

        return false;
    }


    if (
        typeof LightweightCharts === "undefined"
    ) {

        return false;
    }


    rsiChart =
        LightweightCharts.createChart(

            rsiContainer,

            {

                width:
                    tradingContainer.clientWidth ||
                    800,

                height: 150,

                layout: {

                    background: {
                        color: "#0B1220"
                    },

                    textColor: "#D1D5DB"

                },

                grid: {

                    vertLines: {
                        color: "#1E293B"
                    },

                    horzLines: {
                        color: "#1E293B"
                    }

                },

                rightPriceScale: {

                    borderColor: "#334155"

                },

                timeScale: {

                    borderColor: "#334155",

                    timeVisible: true,

                    secondsVisible: false

                }

            }

        );


    rsiSeries =
        rsiChart.addLineSeries({

            color: "#A855F7",

            lineWidth: 2,

            title: "RSI"

        });


    return true;
}


// ======================================================
// RESIZE CHART
// ======================================================

function resizeChart() {

    const container =
        document.getElementById(
            "tradingChart"
        );


    if (!container) {
        return;
    }


    if (mainChart) {

        mainChart.applyOptions({

            width:
                container.clientWidth

        });

    }


    const rsiContainer =
        document.getElementById(
            "rsiPane"
        );


    if (
        rsiChart &&
        rsiContainer
    ) {

        rsiChart.applyOptions({

            width:
                container.clientWidth

        });

    }

}


// ======================================================
// LOAD CHART DATA
// ======================================================

async function loadChart(
    symbol = currentSymbol,
    interval = currentInterval
) {

    // Normalize the symbol here too because timeframe changes and auto-refresh
    // can call loadChart() without going through app.js.
    symbol = normalizeStockSymbol(symbol || currentSymbol || "RELIANCE");

    const requestId = ++chartRequestId;

    // Do not attempt chart loading on pages
    // without the chart.
    if (!mainChart) {

        console.log(
            "Chart not initialized. Skipping load."
        );

        return;

    }


    if (
        !candleSeries ||
        !volumeSeries
    ) {

        console.warn(
            "Chart series not initialized."
        );

        return;

    }


    currentSymbol = symbol;
    currentInterval = interval;

    // Clear the previous stock immediately. This prevents a failed/slow request
    // from making the old candles look like the newly selected stock.
    candleSeries.setData([]);
    volumeSeries.setData([]);

    if (ema20Series) ema20Series.setData([]);
    if (ema50Series) ema50Series.setData([]);
    if (sma200Series) sma200Series.setData([]);
    if (rsiSeries) rsiSeries.setData([]);

    // Also clear any entry marker / SL / target lines left over from the
    // previous symbol — they belong to a different stock's verdict and
    // would otherwise sit on the chart pointing at the wrong price.
    if (typeof clearTradeLevels === "function") {
        clearTradeLevels();
    }

    try {

        const chartUrl =
            `/api/chart/${encodeURIComponent(symbol)}?interval=${encodeURIComponent(interval)}`;

        const data = typeof ApiCache !== "undefined"
            ? await ApiCache.fetchJSON(chartUrl)
            : await (await apiFetch(chartUrl)).json();

        // A newer search may have started while this request was in flight.
        if (requestId !== chartRequestId) {
            console.log("Ignoring stale chart response for:", symbol);
            return;
        }

        if (!data) {

            throw new Error(
                "Empty chart response"
            );

        }


        chartData = data;


        // --------------------------------------
        // Candles
        // --------------------------------------

        if (
            Array.isArray(data.candles)
        ) {

            renderCandles(
                data.candles
            );

        }


        // --------------------------------------
        // Volume
        // --------------------------------------

        if (
            Array.isArray(data.volume)
        ) {

            renderVolume(
                data.volume
            );

        }


        // --------------------------------------
        // EMA 20
        // --------------------------------------

        if (
            ema20Series &&
            Array.isArray(data.ema20)
        ) {

            ema20Series.setData(
                data.ema20
            );

        }


        // --------------------------------------
        // EMA 50
        // --------------------------------------

        if (
            ema50Series &&
            Array.isArray(data.ema50)
        ) {

            ema50Series.setData(
                data.ema50
            );

        }


        // --------------------------------------
        // SMA 200
        // --------------------------------------

        if (
            sma200Series &&
            Array.isArray(data.sma200)
        ) {

            sma200Series.setData(
                data.sma200
            );

        }


        // --------------------------------------
        // RSI
        // --------------------------------------

        if (
            rsiSeries &&
            Array.isArray(data.rsi)
        ) {

            rsiSeries.setData(
                data.rsi
            );

        }


        // --------------------------------------
        // Fit main chart
        // --------------------------------------

        if (mainChart) {

            mainChart
                .timeScale()
                .fitContent();

        }


        // --------------------------------------
        // Fit RSI chart
        // --------------------------------------

        if (rsiChart) {

            rsiChart
                .timeScale()
                .fitContent();

        }


    } catch (error) {

        console.error(
            "Chart loading error:",
            error
        );

    }

}


// ======================================================
// RENDER CANDLES
// ======================================================

function renderCandles(candles) {

    if (!candleSeries) {

        console.warn(
            "Candle series not initialized."
        );

        return;

    }


    if (!Array.isArray(candles)) {

        console.warn(
            "Invalid candle data."
        );

        return;

    }


    candleSeries.setData(
        candles
    );

}


// ======================================================
// RENDER VOLUME
// ======================================================

function renderVolume(volume) {

    if (!volumeSeries) {

        console.warn(
            "Volume series not initialized."
        );

        return;

    }


    if (!Array.isArray(volume)) {

        console.warn(
            "Invalid volume data."
        );

        return;

    }


    volumeSeries.setData(
        volume
    );

}


// ======================================================
// TIMEFRAME HANDLER
// ======================================================

function initTimeframeControl() {

    const timeframe =
        document.getElementById(
            "timeframe"
        );


    // No timeframe control on this page
    if (!timeframe) {

        console.log(
            "Timeframe control not present."
        );

        return;

    }


    timeframe.addEventListener(
        "change",
        async function () {

            let interval =
                this.value.toLowerCase();


            // UI → Yahoo interval
            const map = {

                "1m": "1m",

                "5m": "5m",

                "15m": "15m",

                "30m": "30m",

                "1h": "60m",

                "4h": "60m",

                "1d": "1d",

                "1w": "1wk",

                "1mo": "1mo"

            };


            interval =
                map[interval] ||
                "1d";


            console.log(
                "Loading timeframe:",
                interval
            );


            currentInterval = interval;

            // Re-run the FULL analysis (indicators, verdict, strategy
            // votes, trade levels) at the newly selected timeframe, not
            // just the candlestick chart. Previously switching to 5m/15m
            // only changed what candles were drawn — the BUY/SELL
            // verdict underneath stayed locked to whatever interval was
            // last analyzed (usually 1d). analyzeStock() reads
            // currentInterval (set above) and re-fetches both the
            // chart and the verdict together for the same timeframe.
            if (typeof analyzeStock === "function") {
                await analyzeStock();
            } else {
                await loadChart(
                    currentSymbol,
                    interval
                );
            }

        }
    );

}


// ======================================================
// AUTO REFRESH
// ======================================================

function startAutoRefresh() {

    // Clear previous timer
    if (refreshTimer) {

        clearInterval(
            refreshTimer
        );

    }


    refreshTimer =
        setInterval(
            function () {

                if (!mainChart) {
                    return;
                }

                // Skip refreshes while the tab is in the background —
                // no point re-downloading 5 years of candles for a chart
                // nobody is looking at.
                if (document.hidden) {
                    return;
                }

                loadChart(
                    currentSymbol,
                    currentInterval
                );

            },
            120000 // 2 minutes — was 30s, which hammered Yahoo constantly
        );

}

// Re-sync immediately when the person comes back to the tab, instead of
// waiting up to 2 minutes for the next scheduled tick.
document.addEventListener("visibilitychange", function () {
    if (!document.hidden && mainChart) {
        loadChart(currentSymbol, currentInterval);
    }
});


// ======================================================
// FULLSCREEN
// ======================================================

function initFullscreen() {

    const fullscreenBtn =
        document.getElementById(
            "fullscreen"
        );


    const chartCard =
        document.querySelector(
            ".chart-card"
        );


    // Fullscreen controls may not
    // exist on every page.
    if (
        !fullscreenBtn ||
        !chartCard
    ) {

        console.log(
            "Fullscreen control not present."
        );

        return;

    }


    fullscreenBtn.addEventListener(
        "click",
        async function () {

            try {

                if (
                    !document.fullscreenElement
                ) {

                    if (
                        chartCard.requestFullscreen
                    ) {

                        await chartCard
                            .requestFullscreen();

                    }

                } else {

                    if (
                        document.exitFullscreen
                    ) {

                        await document
                            .exitFullscreen();

                    }

                }


                // Give browser time to resize
                setTimeout(
                    function () {

                        if (
                            mainChart &&
                            chartCard
                        ) {

                            const width =
                                chartCard.clientWidth;

                            const height =
                                Math.max(
                                    chartCard.clientHeight - 60,
                                    300
                                );


                            mainChart.applyOptions({

                                width:
                                    width,

                                height:
                                    height

                            });

                        }


                        resizeChart();

                    },
                    300
                );


            } catch (error) {

                console.error(
                    "Fullscreen error:",
                    error
                );

            }

        }
    );

}


// ======================================================
// FULLSCREEN CHANGE
// ======================================================

document.addEventListener(
    "fullscreenchange",
    function () {

        setTimeout(
            resizeChart,
            300
        );

    }
);


// ======================================================
// PAGE INITIALIZATION
// ======================================================

document.addEventListener(
    "DOMContentLoaded",
    async function () {

        console.log(
            "Initializing chart..."
        );


        // --------------------------------------
        // Initialize chart
        // --------------------------------------

        const chartReady =
            initChart();


        // --------------------------------------
        // No chart on this page
        // --------------------------------------

        if (!chartReady) {

            console.log(
                "No chart on this page. Chart JS stopped safely."
            );

            return;

        }


        // --------------------------------------
        // Controls
        // --------------------------------------

        initTimeframeControl();

        initFullscreen();


        // --------------------------------------
        // Initial data
        // --------------------------------------

        await loadChart(
            currentSymbol,
            currentInterval
        );


        // --------------------------------------
        // Auto refresh
        // --------------------------------------

        startAutoRefresh();


        console.log(
            "Chart initialized successfully."
        );

    }
);

// ======================================================
// TRADE LEVELS ON CHART
// Draws the entry marker (on the exact candle the verdict
// fired) plus horizontal stop-loss / target price lines,
// so "where do I get in / out" is visible directly on the
// chart instead of only as numbers in the verdict card.
// ======================================================

let activeTradeLines = [];

function clearTradeLevels() {

    if (!candleSeries) {
        return;
    }

    activeTradeLines.forEach((line) => {
        try {
            candleSeries.removePriceLine(line);
        } catch (err) {
            // line may already be gone (chart reloaded) — safe to ignore
        }
    });

    activeTradeLines = [];

    try {
        candleSeries.setMarkers([]);
    } catch (err) {
        // no-op if series not ready
    }

    if (rsiSeries) {
        try {
            rsiSeries.setMarkers([]);
        } catch (err) {
            // no-op if series not ready
        }
    }
}

function plotTradeLevels(decision) {

    if (!candleSeries || !decision) {
        return;
    }

    clearTradeLevels();

    const signal = String(decision.signal || "").toUpperCase();
    const isBuy = signal.includes("BUY");
    const isSell = signal.includes("SELL");

    if (!isBuy && !isSell) {
        return; // HOLD / no data: nothing to plot
    }

    // ---- Entry marker, placed on the candle the verdict used ----
    if (decision.entry_time) {

        const entryTime = Math.floor(
            new Date(decision.entry_time).getTime() / 1000
        );

        try {
            candleSeries.setMarkers([
                {
                    time: entryTime,
                    position: isBuy ? "belowBar" : "aboveBar",
                    color: isBuy ? "#17c987" : "#ef4a56",
                    shape: isBuy ? "arrowUp" : "arrowDown",
                    text: `ENTRY ${decision.entry ?? ""}`,
                },
            ]);
        } catch (err) {
            console.warn("Could not place entry marker:", err);
        }

        // Mirror the same entry point on the RSI panel so the indicator
        // and the price chart read as one connected story.
        if (rsiSeries) {
            try {
                rsiSeries.setMarkers([
                    {
                        time: entryTime,
                        position: "inBar",
                        color: isBuy ? "#17c987" : "#ef4a56",
                        shape: "circle",
                        text: "",
                    },
                ]);
            } catch (err) {
                console.warn("Could not place RSI entry marker:", err);
            }
        }
    }

    // ---- Stop-loss / target horizontal price lines ----
    const addLine = (price, color, title) => {
        if (price === null || price === undefined) return;
        try {
            const line = candleSeries.createPriceLine({
                price: Number(price),
                color,
                lineWidth: 2,
                lineStyle: 2, // dashed
                axisLabelVisible: true,
                title,
            });
            activeTradeLines.push(line);
        } catch (err) {
            console.warn(`Could not draw ${title} line:`, err);
        }
    };

    addLine(decision.stoploss, "#ef4a56", "SL");
    addLine(decision.target1, "#17c987", "T1");
    addLine(decision.target2, "#0ea968", "T2");
}