// =====================================
// Portfolio Dashboard
// File: static/js/portfolio.js
// =====================================

function updatePortfolio(data) {

    if (!data) {
        console.warn("Portfolio data missing");
        return;
    }

    console.log("PORTFOLIO DATA:", data);

    // ==============================
    // Portfolio Summary
    // ==============================

    setPortfolioText(
        "portfolioValue",
        formatMoney(data.total_value)
    );

    setPortfolioText(
        "portfolioInvested",
        formatMoney(data.invested)
    );

    setPortfolioText(
        "portfolioCash",
        formatMoney(
            data.available_cash !== undefined
                ? data.available_cash
                : data.cash
        )
    );

    setPortfolioText(
        "portfolioPnL",
        formatMoney(
            data.total_pnl !== undefined
                ? data.total_pnl
                : data.pnl
        )
    );

    // ==============================
    // Risk
    // ==============================

    setPortfolioText(
        "portfolioRisk",
        data.risk !== undefined
            ? data.risk + "%"
            : "0%"
    );

    setPortfolioText(
        "maxDrawdown",
        data.max_drawdown !== undefined
            ? data.max_drawdown + "%"
            : "0%"
    );

    setPortfolioText(
        "portfolioRiskReward",
        data.risk_reward !== undefined
            ? data.risk_reward
            : "--"
    );

    // ==============================
    // Positions
    // ==============================

    const positions =
        Array.isArray(data.positions)
            ? data.positions
            : [];

    setPortfolioText(
        "openPositions",
        positions.length
    );

    updatePositions(positions);
}

// =====================================
// Positions
// =====================================

function updatePositions(positions) {

    const table =
        document.getElementById(
            "portfolioPositions"
        );

    if (!table) {
        return;
    }

    table.innerHTML = "";

    if (!positions.length) {

        table.innerHTML = `
            <tr>
                <td colspan="5">
                    No positions yet
                </td>
            </tr>
        `;

        return;
    }

    positions.forEach(position => {

        const row =
            document.createElement("tr");

        row.innerHTML = `
            <td>${position.symbol || "--"}</td>
            <td>${position.quantity || 0}</td>
            <td>₹ ${formatMoney(position.entry)}</td>
            <td>₹ ${formatMoney(position.current)}</td>
           <td>₹ ${Number(position.pnl || 0).toLocaleString("en-IN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
})}</td>
        `;

        table.appendChild(row);

    });
}


// =====================================
// Safe text
// =====================================

function setPortfolioText(id, value) {

    const element =
        document.getElementById(id);

    if (!element) {
        return;
    }

    element.innerText = value;
}


// =====================================
// Money
// =====================================

function formatMoney(value) {

    if (
        value === undefined ||
        value === null
    ) {
        return "₹ 0.00";
    }

    return "₹ " +
        Number(value).toLocaleString(
            "en-IN",
            {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            }
        );
}