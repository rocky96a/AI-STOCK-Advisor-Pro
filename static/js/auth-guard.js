// =====================================
// AUTH GUARD
// Runs before any other script or API call.
//
// - No token in localStorage -> instant redirect to /login.
//   Nothing else on this page executes an API call before that check
//   passes, because every other script that fetches data waits for
//   DOMContentLoaded, which fires after this guard has already run.
// - Provides window.apiFetch(), a drop-in replacement for fetch() that
//   attaches the auth token to every request and auto-redirects to
//   /login the moment the server says the token is invalid/expired.
// =====================================

(function () {
    "use strict";

    const TOKEN_KEY = "jm_auth_token";
    const USER_KEY = "jm_auth_user";

    function getToken() {
        return localStorage.getItem(TOKEN_KEY);
    }

    function setSession(token, username) {
        localStorage.setItem(TOKEN_KEY, token);
        if (username) {
            localStorage.setItem(USER_KEY, username);
        }
    }

    function clearSession() {
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(USER_KEY);
    }

    function getUsername() {
        return localStorage.getItem(USER_KEY) || "";
    }

    function goToLogin() {
        clearSession();
        if (!window.location.pathname.startsWith("/login")) {
            window.location.href = "/login";
        }
    }

    // ---- Hard gate: no token, no dashboard. ----
    if (!getToken() && !window.location.pathname.startsWith("/login")) {
        goToLogin();
    }

    // ---- Global fetch wrapper used by every dashboard script instead of fetch(). ----
    async function apiFetch(url, options) {
        options = options || {};

        const token = getToken();

        if (!token) {
            goToLogin();
            // Return a never-resolving-ish rejected promise so callers'
            // .then chains don't try to parse a body that will never come.
            return Promise.reject(new Error("Not authenticated"));
        }

        const headers = Object.assign(
            {},
            options.headers || {},
            { Authorization: `Bearer ${token}` }
        );

        const response = await fetch(url, Object.assign({}, options, { headers }));

        if (response.status === 401) {
            goToLogin();
            throw new Error("Session expired. Please log in again.");
        }

        return response;
    }

    window.apiFetch = apiFetch;
    window.authGuard = {
        getToken,
        setSession,
        clearSession,
        getUsername,
        goToLogin,
    };
})();
