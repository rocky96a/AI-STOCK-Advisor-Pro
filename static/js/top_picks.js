/* =====================================================
   TODAY'S TOP PICKS — BUY / SELL recommendation panel

   Backed by GET /api/recommendations (top BUY + top SELL, ranked by
   safety score). The backend already caches this for ~45s, and this
   file additionally avoids re-rendering / re-fetching on the client
   within REFRESH_MS so switching tabs or briefly leaving the tab
   doesn't trigger extra network calls.
   ===================================================== */

(function () {

    const REFRESH_MS = 60000; // background refresh interval
    let activeTab = "buy";
    let refreshTimer = null;

    function fmtMoney(value) {
        if (value === null || value === undefined || isNaN(value)) return "--";
        return "₹" + Number(value).toLocaleString("en-IN", {
            maximumFractionDigits: 2,
        });
    }

    function pickCard(pick, type) {
        const badgeClass = type === "buy" ? "buy" : "sell";
        const badgeLabel = pick.signal || (type === "buy" ? "BUY" : "SELL");

        return `
            <div class="tp-pick">
                <div class="tp-pick-top">
                    <div>
                        <span class="tp-symbol">${pick.symbol}</span>
                        <span class="tp-company">${pick.company || ""}</span>
                    </div>
                    <span class="tp-badge ${badgeClass}">${badgeLabel}</span>
                </div>

                <div class="tp-price-row">
                    <span class="tp-price">${fmtMoney(pick.price)}</span>
                    <span class="tp-confidence">${pick.confidence != null ? pick.confidence + "% conf" : ""}</span>
                </div>

                <div class="tp-levels">
                    <div>
                        <span>Entry</span>
                        <strong>${fmtMoney(pick.entry)}</strong>
                    </div>
                    <div>
                        <span>Stop</span>
                        <strong>${fmtMoney(pick.stoploss)}</strong>
                    </div>
                    <div>
                        <span>Target</span>
                        <strong>${fmtMoney(pick.target1)}</strong>
                    </div>
                </div>

                <div class="tp-foot">
                    <span>R:R <strong>${pick.risk_reward != null ? pick.risk_reward.toFixed(2) : "--"}</strong></span>
                    <span>Risk <strong>${pick.risk_percent != null ? pick.risk_percent.toFixed(2) + "%" : "--"}</strong></span>
                    <span>Score <strong>${pick.safety_score != null ? pick.safety_score : "--"}</strong></span>
                </div>
            </div>
        `;
    }

    function renderList(el, picks, type) {
        if (!picks || picks.length === 0) {
            el.innerHTML = `<div class="tp-empty">No qualifying ${type.toUpperCase()} setups right now.</div>`;
            return;
        }
        el.innerHTML = picks.map((p) => pickCard(p, type)).join("");
    }

    function switchTab(tab) {
        activeTab = tab;

        document.querySelectorAll(".tp-tab").forEach((btn) => {
            btn.classList.toggle("active", btn.dataset.tab === tab);
        });

        document.getElementById("tpBuyList").classList.toggle("active", tab === "buy");
        document.getElementById("tpSellList").classList.toggle("active", tab === "sell");
    }

    async function loadTopPicks(force) {
        const status = document.getElementById("topPicksStatus");
        const updated = document.getElementById("topPicksUpdated");
        const buyList = document.getElementById("tpBuyList");
        const sellList = document.getElementById("tpSellList");

        if (!buyList || !sellList) return;

        try {
            if (status) status.innerText = "Loading recommendations…";

            const fetcher = typeof ApiCache !== "undefined"
                ? null
                : (typeof apiFetch === "function" ? apiFetch : fetch);

            const data = typeof ApiCache !== "undefined"
                ? await ApiCache.fetchJSON("/api/recommendations")
                : await (await fetcher("/api/recommendations")).json();

            const buys = Array.isArray(data.buy) ? data.buy : [];
            const sells = Array.isArray(data.sell) ? data.sell : [];

            renderList(buyList, buys, "buy");
            renderList(sellList, sells, "sell");

            const buyCountEl = document.getElementById("tpBuyCount");
            const sellCountEl = document.getElementById("tpSellCount");
            if (buyCountEl) buyCountEl.innerText = buys.length;
            if (sellCountEl) sellCountEl.innerText = sells.length;

            if (status) {
                status.innerText = data.success === false
                    ? "Couldn't refresh recommendations — showing last known data."
                    : "Live AI scan of the watchlist";
            }

            if (updated && data.generated_at) {
                const t = new Date(data.generated_at);
                updated.innerText = "Updated " + t.toLocaleTimeString();
            }

        } catch (err) {
            console.error("TOP PICKS ERROR:", err);
            if (status) status.innerText = "Unable to load recommendations right now.";
        }
    }

    function init() {
        const card = document.getElementById("topPicksCard");
        if (!card) return; // component not on this page

        card.querySelectorAll(".tp-tab").forEach((btn) => {
            btn.addEventListener("click", () => switchTab(btn.dataset.tab));
        });

        loadTopPicks();

        // Background refresh — respects the backend cache TTL, so this
        // just keeps the panel current without hammering the API.
        refreshTimer = setInterval(loadTopPicks, REFRESH_MS);
    }

    document.addEventListener("DOMContentLoaded", init);
})();
