/* Full-screen chat view helpers */
document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("chatComposer");
    const input = document.getElementById("chatInput");
    const messages = document.getElementById("chatMessages");

    if (!form || !input || !messages) return;

    const resize = () => {
        input.style.height = "auto";
        input.style.height = Math.min(input.scrollHeight, 150) + "px";
    };

    input.addEventListener("input", resize);

    form.addEventListener("submit", (event) => {
        event.preventDefault();

        const text = input.value.trim();
        if (!text) return;

        const row = document.createElement("div");
        row.className = "chat-message user";
        row.style.marginLeft = "auto";
        row.style.justifyContent = "flex-end";
        row.style.maxWidth = "820px";

        const bubble = document.createElement("div");
        bubble.className = "chat-bubble";
        bubble.innerHTML = `<p style="margin:0;color:#e2e8f0;"></p>`;
        bubble.querySelector("p").textContent = text;

        row.appendChild(bubble);
        messages.appendChild(row);
        messages.scrollTop = messages.scrollHeight;

        input.value = "";
        resize();
    });

    resize();
});
