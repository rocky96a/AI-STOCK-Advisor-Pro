// =====================================
// LOGIN PAGE
// Boot sequence -> login card -> authenticate -> redirect to dashboard.
// =====================================

(function () {
    "use strict";

    const TOKEN_KEY = "jm_auth_token";
    const USER_KEY = "jm_auth_user";

    // If a valid-looking token already exists, skip straight to the
    // dashboard instead of making the user watch the boot sequence again.
    if (localStorage.getItem(TOKEN_KEY)) {
        window.location.href = "/";
        return;
    }

    const bootScreen = document.getElementById("bootScreen");
    const loginScreen = document.getElementById("loginScreen");
    const bootPercent = document.getElementById("bootPercent");
    const bootBarFill = document.getElementById("bootBarFill");
    const bootLog = document.getElementById("bootLog");
    const bootFutureLine = document.getElementById("bootFutureLine");

    const LOG_LINES = [
        { text: "INITIALIZING HIVE CORE...", cls: "log-info" },
        { text: "LOADING MARKET GRID INTERFACE...", cls: "log-info" },
        { text: "CONNECTING TECHNICAL / ML / ALGO AGENTS...", cls: "log-info" },
        { text: "SYNCING DECISION ENGINE...", cls: "log-ok" },
        { text: "CALIBRATING CONFIDENCE MATRIX...", cls: "log-ok" },
        { text: "SECURING AUTH CHANNEL...", cls: "log-ok" },
        { text: "HIVE CORE READY.", cls: "log-ok" },
    ];

    const FUTURE_LINE = "The future of the market, written before it happens.";

    function appendLog(line) {
        const div = document.createElement("div");
        div.className = line.cls;
        div.textContent = "> " + line.text;
        bootLog.appendChild(div);
        bootLog.scrollTop = bootLog.scrollHeight;
    }

    function typeFutureLine() {
        return new Promise((resolve) => {
            let i = 0;
            const cursor = '<span class="typed-cursor"></span>';
            const interval = setInterval(() => {
                i++;
                bootFutureLine.innerHTML =
                    FUTURE_LINE.slice(0, i) + cursor;
                if (i >= FUTURE_LINE.length) {
                    clearInterval(interval);
                    resolve();
                }
            }, 22);
        });
    }

    async function runBootSequence() {
        const totalSteps = LOG_LINES.length;

        for (let i = 0; i < totalSteps; i++) {
            await new Promise((r) => setTimeout(r, 260));
            appendLog(LOG_LINES[i]);

            const pct = Math.round(((i + 1) / totalSteps) * 100);
            bootPercent.textContent = pct + "%";
            bootBarFill.style.width = pct + "%";
        }

        await new Promise((r) => setTimeout(r, 200));
        await typeFutureLine();
        await new Promise((r) => setTimeout(r, 500));

        bootScreen.classList.add("hidden");
        loginScreen.classList.add("visible");

        const firstInput = document.getElementById("username");
        if (firstInput) firstInput.focus();
    }

    runBootSequence();

    // ---- Form toggling ----
    const loginForm = document.getElementById("loginForm");
    const registerForm = document.getElementById("registerForm");
    const showRegister = document.getElementById("showRegister");
    const showLogin = document.getElementById("showLogin");

    showRegister.addEventListener("click", (e) => {
        e.preventDefault();
        loginForm.hidden = true;
        registerForm.hidden = false;
    });

    showLogin.addEventListener("click", (e) => {
        e.preventDefault();
        registerForm.hidden = true;
        loginForm.hidden = false;
    });

    // ---- Password visibility toggle ----
    const togglePassword = document.getElementById("togglePassword");
    const passwordInput = document.getElementById("password");

    togglePassword.addEventListener("click", () => {
        const isHidden = passwordInput.type === "password";
        passwordInput.type = isHidden ? "text" : "password";
        togglePassword.innerHTML = isHidden
            ? '<i class="fa-solid fa-eye-slash"></i>'
            : '<i class="fa-solid fa-eye"></i>';
    });

    function setButtonLoading(button, loading) {
        const label = button.querySelector(".btn-label");
        const spinner = button.querySelector(".btn-spinner");
        button.disabled = loading;
        if (spinner) spinner.hidden = !loading;
        if (label) label.style.opacity = loading ? "0.6" : "1";
    }

    function showError(el, message) {
        el.textContent = message;
        el.hidden = false;
    }

    function hideError(el) {
        el.hidden = true;
        el.textContent = "";
    }

    // ---- LOGIN submit ----
    loginForm.addEventListener("submit", async function (e) {
        e.preventDefault();

        const errorEl = document.getElementById("loginError");
        const submitBtn = document.getElementById("loginSubmit");
        hideError(errorEl);

        const username = document.getElementById("username").value.trim();
        const password = document.getElementById("password").value;

        if (!username || !password) {
            showError(errorEl, "Enter your username and password.");
            return;
        }

        setButtonLoading(submitBtn, true);

        try {
            const response = await fetch("/api/auth/login", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ username, password }),
            });

            const data = await response.json();

            if (!response.ok || !data.success) {
                throw new Error(data.error || "Invalid username or password.");
            }

            // Token is created here, after successful login - this is the
            // only thing that unlocks any API call from here on.
            localStorage.setItem(TOKEN_KEY, data.token);
            localStorage.setItem(USER_KEY, data.user.username);

            window.location.href = "/";

        } catch (err) {
            showError(errorEl, err.message || "Login failed. Try again.");
            setButtonLoading(submitBtn, false);
        }
    });

    // ---- REGISTER submit ----
    registerForm.addEventListener("submit", async function (e) {
        e.preventDefault();

        const errorEl = document.getElementById("registerError");
        const submitBtn = document.getElementById("registerSubmit");
        hideError(errorEl);

        const username = document.getElementById("regUsername").value.trim();
        const password = document.getElementById("regPassword").value;

        if (!username || password.length < 6) {
            showError(errorEl, "Username required, password min 6 characters.");
            return;
        }

        setButtonLoading(submitBtn, true);

        try {
            const response = await fetch("/api/auth/register", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ username, password }),
            });

            const data = await response.json();

            if (!response.ok || !data.success) {
                throw new Error(data.error || "Registration failed.");
            }

            localStorage.setItem(TOKEN_KEY, data.token);
            localStorage.setItem(USER_KEY, data.user.username);

            window.location.href = "/";

        } catch (err) {
            showError(errorEl, err.message || "Registration failed. Try again.");
            setButtonLoading(submitBtn, false);
        }
    });
})();
