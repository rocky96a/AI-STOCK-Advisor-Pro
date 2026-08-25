// =====================================
// HEADER: profile username + logout
// =====================================

document.addEventListener("DOMContentLoaded", function () {
    const usernameEl = document.getElementById("profileUsername");
    const dropdownUsernameEl = document.getElementById("profileDropdownUsername");
    const profileBtn = document.getElementById("profileBtn");
    const dropdown = document.getElementById("profileDropdown");
    const logoutBtn = document.getElementById("logoutBtn");

    const username = (window.authGuard && window.authGuard.getUsername()) || "";

    if (usernameEl) usernameEl.textContent = username;
    if (dropdownUsernameEl) dropdownUsernameEl.textContent = username;

    if (profileBtn && dropdown) {
        profileBtn.addEventListener("click", function (e) {
            e.stopPropagation();
            dropdown.classList.toggle("open");
        });

        document.addEventListener("click", function () {
            dropdown.classList.remove("open");
        });
    }

    if (logoutBtn) {
        logoutBtn.addEventListener("click", async function () {
            try {
                if (window.apiFetch) {
                    await window.apiFetch("/api/auth/logout", { method: "POST" });
                }
            } catch (err) {
                // Token may already be invalid/expired - that's fine, we're
                // logging out either way.
            } finally {
                if (window.authGuard) {
                    window.authGuard.goToLogin();
                }
            }
        });
    }
});
