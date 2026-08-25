/* =====================================================
   WATCHLIST
   ===================================================== */

async function loadWatchlist() {

    const body =
        document.getElementById("watchlistBody");

    const status =
        document.getElementById("watchlistStatus");

    if (!body) {
        return;
    }

    try {

        if (status) {
            status.innerText = "Loading watchlist...";
        }

        const response =
            await apiFetch("/api/watchlist");

        if (!response.ok) {
            throw new Error(
                `Watchlist API failed: ${response.status}`
            );
        }

        const data =
            await response.json();

        console.log(
            "WATCHLIST DATA:",
            data
        );

        const stocks =
            Array.isArray(data.stocks)
                ? data.stocks
                : [];

        body.innerHTML = "";

        if (!stocks.length) {

            body.innerHTML = `
                <tr>
                    <td colspan="12">
                        No watchlist signals available.
                    </td>
                </tr>
            `;

            if (status) {
                status.innerText =
                    "No qualifying stocks found.";
            }

            return;
        }

        stocks.forEach((stock, index) => {

            const row =
                document.createElement("tr");

            const signal =
                stock.signal || "--";

            const signalClass =
                signal
                    .toLowerCase()
                    .replace(/\s+/g, "-");

            row.innerHTML = `

                <td>${index + 1}</td>

                <td>
                    <div class="watchlist-symbol">
                        ${stock.symbol || "--"}
                    </div>

                    <div class="watchlist-company">
                        ${stock.company || "--"}
                    </div>
                </td>

                <td>
                    ${formatWatchlistNumber(stock.price)}
                </td>

                <td>
                    <span class="signal ${signalClass}">
                        ${signal}
                    </span>
                </td>

                <td>
                    ${formatWatchlistNumber(stock.confidence)}%
                </td>

                <td>
                    ${formatWatchlistNumber(stock.entry)}
                </td>

                <td>
                    ${formatWatchlistNumber(stock.stoploss)}
                </td>

                <td>
                    ${formatWatchlistNumber(stock.target1)}
                </td>

                <td>
                    ${formatWatchlistNumber(stock.target2)}
                </td>

                <td>
                    ${formatWatchlistNumber(stock.risk_percent)}%
                </td>

                <td>
                    ${formatWatchlistNumber(stock.risk_reward)}
                </td>

                <td>
                    <strong>
                        ${formatWatchlistNumber(stock.safety_score)}
                    </strong>
                </td>

            `;

            body.appendChild(row);

        });

        if (status) {

            status.innerText =
                `${stocks.length} stocks ranked successfully.`;

        }

    } catch (error) {

        console.error(
            "Watchlist error:",
            error
        );

        body.innerHTML = `
            <tr>
                <td colspan="12">
                    Unable to load watchlist.
                </td>
            </tr>
        `;

        if (status) {
            status.innerText =
                "Watchlist API error.";
        }

    }

}


/* =====================================================
   NUMBER FORMAT
   ===================================================== */

function formatWatchlistNumber(value) {

    if (
        value === null ||
        value === undefined ||
        value === ""
    ) {
        return "--";
    }

    const number =
        Number(value);

    if (Number.isNaN(number)) {
        return "--";
    }

    return number.toLocaleString(
        "en-IN",
        {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        }
    );
}


/* =====================================================
   INITIALIZE
   ===================================================== */

document.addEventListener(
    "DOMContentLoaded",
    function () {

        const body =
            document.getElementById(
                "watchlistBody"
            );

        if (!body) {
            return;
        }

        loadWatchlist();


        const refresh =
            document.getElementById(
                "refreshWatchlist"
            );

        if (refresh) {

            refresh.addEventListener(
                "click",
                loadWatchlist
            );

        }

    }
);
