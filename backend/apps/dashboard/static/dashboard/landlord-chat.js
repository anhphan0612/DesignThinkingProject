(function () {
    const listEl = document.querySelector("#landlordChatThreads");
    const countEl = document.querySelector("#landlordChatCount");
    const statusEl = document.querySelector("#landlordChatStatus");

    if (!listEl || !countEl || !statusEl) {
        return;
    }

    function setStatus(message, isError = false) {
        statusEl.hidden = !message;
        statusEl.textContent = message || "";
        statusEl.classList.toggle("error", isError);
    }

    async function fetchThreads() {
        const response = await fetch("/api/chat-threads/");
        if (!response.ok) {
            throw new Error(`Request failed with status ${response.status}`);
        }
        return response.json();
    }

    function normalizeResults(data) {
        if (Array.isArray(data)) {
            return data;
        }
        return data.results || [];
    }

    function threadCard(thread) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "landlord-chat-thread";

        const main = document.createElement("span");
        main.className = "landlord-chat-main";

        const title = document.createElement("strong");
        title.textContent = thread.requester_name || "Người thuê";

        const room = document.createElement("span");
        room.textContent = thread.target_title || "Cuộc trò chuyện";

        const latest = document.createElement("small");
        latest.textContent = thread.latest_message || "Chưa có tin nhắn. Bấm để phản hồi.";

        main.append(title, room, latest);

        const meta = document.createElement("span");
        meta.className = "landlord-chat-meta";
        meta.textContent = new Intl.DateTimeFormat("vi-VN", {
            day: "2-digit",
            month: "2-digit",
            hour: "2-digit",
            minute: "2-digit",
        }).format(new Date(thread.updated_at));

        button.append(main, meta);
        button.addEventListener("click", async () => {
            if (window.RentifyChat) {
                await window.RentifyChat.open(thread.id, `Chat với ${thread.requester_name || "người thuê"}`);
            }
        });
        return button;
    }

    function renderThreads(threads) {
        countEl.textContent = `${threads.length} cuộc trò chuyện`;
        listEl.replaceChildren();
        if (!threads.length) {
            const empty = document.createElement("p");
            empty.className = "empty-inline landlord-chat-empty";
            empty.textContent = "Chưa có tin nhắn nào từ người thuê.";
            listEl.append(empty);
            return;
        }
        threads.forEach((thread) => listEl.append(threadCard(thread)));
    }

    async function bootstrap() {
        setStatus("Đang tải tin nhắn...");
        try {
            const data = await fetchThreads();
            renderThreads(normalizeResults(data));
            setStatus("");
        } catch (error) {
            countEl.textContent = "Không tải được";
            setStatus("Không tải được danh sách tin nhắn. Hãy thử tải lại trang.", true);
        }
    }

    bootstrap();
})();
