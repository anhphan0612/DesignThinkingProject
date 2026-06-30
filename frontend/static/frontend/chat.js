(function () {
    let shell;
    let titleEl;
    let statusEl;
    let messagesEl;
    let formEl;
    let inputEl;
    let currentThreadId = null;

    function csrfToken() {
        return document.querySelector("meta[name='csrf-token']").content;
    }

    async function chatRequest(path, method = "GET", body = null) {
        const options = {
            method,
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": csrfToken(),
            },
        };
        if (body !== null) {
            options.body = JSON.stringify(body);
        }
        const response = await fetch(path, options);
        if (!response.ok) {
            const payload = await response.json().catch(() => ({}));
            const error = new Error(`Request failed with status ${response.status}`);
            error.payload = payload;
            throw error;
        }
        return response.json();
    }

    function ensureShell() {
        if (shell) {
            return;
        }

        shell = document.createElement("section");
        shell.className = "chat-box";
        shell.hidden = true;
        shell.setAttribute("aria-live", "polite");
        shell.innerHTML = `
            <header class="chat-box-header">
                <div>
                    <p class="eyebrow">Chat trong app</p>
                    <h2></h2>
                </div>
                <button type="button" class="chat-box-close" aria-label="Đóng chat">×</button>
            </header>
            <div class="chat-box-status" hidden></div>
            <div class="chat-box-messages"></div>
            <form class="chat-box-form">
                <textarea rows="2" placeholder="Nhập tin nhắn..." required></textarea>
                <button type="submit">Gửi</button>
            </form>
        `;
        document.body.append(shell);

        titleEl = shell.querySelector("h2");
        statusEl = shell.querySelector(".chat-box-status");
        messagesEl = shell.querySelector(".chat-box-messages");
        formEl = shell.querySelector(".chat-box-form");
        inputEl = shell.querySelector("textarea");

        shell.querySelector(".chat-box-close").addEventListener("click", () => {
            shell.hidden = true;
        });
        formEl.addEventListener("submit", sendMessage);
    }

    function setStatus(message, isError = false) {
        statusEl.hidden = !message;
        statusEl.textContent = message || "";
        statusEl.classList.toggle("error", isError);
    }

    function messageNode(message, currentUserName) {
        const item = document.createElement("article");
        const isMine = message.sender_name === currentUserName;
        item.className = isMine ? "chat-message mine" : "chat-message";

        const sender = document.createElement("strong");
        sender.textContent = message.sender_name || "Người dùng";

        const body = document.createElement("p");
        body.textContent = message.body;

        const time = document.createElement("time");
        time.dateTime = message.created_at;
        time.textContent = new Intl.DateTimeFormat("vi-VN", {
            hour: "2-digit",
            minute: "2-digit",
            day: "2-digit",
            month: "2-digit",
        }).format(new Date(message.created_at));

        item.append(sender, body, time);
        return item;
    }

    function renderThread(thread) {
        const currentUserName = thread.requester === thread.current_user_id
            ? thread.requester_name
            : thread.recipient_name;
        messagesEl.replaceChildren();
        if (!thread.messages.length) {
            const empty = document.createElement("p");
            empty.className = "chat-empty";
            empty.textContent = "Chưa có tin nhắn nào trong cuộc trò chuyện này.";
            messagesEl.append(empty);
            return;
        }
        thread.messages.forEach((message) => messagesEl.append(messageNode(message, currentUserName)));
        messagesEl.scrollTop = messagesEl.scrollHeight;
    }

    async function loadThread() {
        setStatus("Đang tải cuộc trò chuyện...");
        try {
            const thread = await chatRequest(`/api/chat-threads/${currentThreadId}/`);
            renderThread(thread);
            setStatus("");
        } catch (error) {
            setStatus("Không tải được cuộc trò chuyện. Hãy thử lại.", true);
        }
    }

    async function sendMessage(event) {
        event.preventDefault();
        const body = inputEl.value.trim();
        if (!body || !currentThreadId) {
            return;
        }
        const submit = formEl.querySelector("button[type='submit']");
        submit.disabled = true;
        try {
            await chatRequest(`/api/chat-threads/${currentThreadId}/messages/`, "POST", { body });
            inputEl.value = "";
            await loadThread();
            inputEl.focus();
        } catch (error) {
            setStatus("Không gửi được tin nhắn. Hãy thử lại.", true);
        } finally {
            submit.disabled = false;
        }
    }

    async function open(threadId, title = "Cuộc trò chuyện") {
        ensureShell();
        currentThreadId = threadId;
        titleEl.textContent = title;
        shell.hidden = false;
        await loadThread();
        inputEl.focus();
    }

    window.RentifyChat = { open };
})();
