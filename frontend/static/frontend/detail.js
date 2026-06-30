function csrfToken() {
    return document.querySelector("meta[name='csrf-token']").content;
}

function isAuthenticated() {
    return document.querySelector("meta[name='is-authenticated']").content === "true";
}

async function requestJson(path, method = "POST", body = {}) {
    const response = await fetch(path, {
        method,
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrfToken(),
        },
        body: JSON.stringify(body),
    });
    if (!response.ok) {
        throw new Error(`Request failed with status ${response.status}`);
    }
    return response.json();
}

function showContactMessage(message) {
    if (!contactResult) {
        return;
    }
    contactResult.hidden = false;
    contactResult.textContent = message;
}

const favoriteButton = document.querySelector("#favoriteButton");
const contactButton = document.querySelector("#contactButton");
const contactResult = document.querySelector("#contactResult");
const reportRoomForm = document.querySelector("#reportRoomForm");

if (favoriteButton) {
    favoriteButton.addEventListener("click", async () => {
        const roomId = favoriteButton.dataset.roomId;
        if (!isAuthenticated()) {
            window.location.href = `/auth/login/?next=/rooms/${roomId}/`;
            return;
        }
        const isFavorited = favoriteButton.dataset.favorited === "true";
        favoriteButton.disabled = true;
        try {
            if (isFavorited) {
                await requestJson(`/api/rooms/${roomId}/unfavorite/`, "DELETE");
                favoriteButton.dataset.favorited = "false";
                favoriteButton.classList.remove("active");
                favoriteButton.textContent = "Lưu phòng yêu thích";
            } else {
                await requestJson(`/api/rooms/${roomId}/favorite/`, "POST");
                favoriteButton.dataset.favorited = "true";
                favoriteButton.classList.add("active");
                favoriteButton.textContent = "Đã lưu phòng";
            }
        } catch (error) {
            showContactMessage("Không cập nhật được phòng yêu thích. Hãy thử lại.");
        } finally {
            favoriteButton.disabled = false;
        }
    });
}

if (contactButton) {
    contactButton.addEventListener("click", async () => {
        const roomId = contactButton.dataset.roomId;
        if (!isAuthenticated()) {
            window.location.href = `/auth/login/?next=/rooms/${roomId}/`;
            return;
        }
        contactButton.disabled = true;
        const originalText = contactButton.textContent;
        contactButton.textContent = "Đang mở chat...";
        try {
            const data = await requestJson(`/api/rooms/${roomId}/contact/`, "POST");
            showContactMessage(data.message || "Đã mở cuộc trò chuyện trong app.");
            if (data.thread_id && window.RentifyChat) {
                await window.RentifyChat.open(data.thread_id, `Chat với ${data.landlord_name}`);
            }
        } catch (error) {
            showContactMessage("Không mở được chat. Hãy thử lại.");
        } finally {
            contactButton.disabled = false;
            contactButton.textContent = originalText;
        }
    });
}

if (reportRoomForm) {
    reportRoomForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        const roomId = reportRoomForm.dataset.roomId;
        const submit = reportRoomForm.querySelector("button[type='submit']");
        submit.disabled = true;
        try {
            await requestJson("/api/reports/", "POST", {
                target_type: "room",
                room: roomId,
                reason: reportRoomForm.elements.reason.value,
                details: reportRoomForm.elements.details.value,
            });
            reportRoomForm.reset();
            showContactMessage("Đã gửi báo cáo. Admin sẽ kiểm tra nội dung này.");
        } catch (error) {
            showContactMessage("Không gửi được báo cáo. Hãy thử lại.");
        } finally {
            submit.disabled = false;
        }
    });
}
